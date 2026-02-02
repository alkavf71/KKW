import streamlit as st
import math

# ==============================================================================
# 1. KONFIGURASI HALAMAN & DATABASE FLUIDA (ENGINEERING BACKEND)
# ==============================================================================
st.set_page_config(
    page_title="Reliability Assistant - Pertamina Patra Niaga",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS untuk tampilan Industrial
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    div.stButton > button:first-child { background-color: #00539C; color: white; border-radius: 5px; height: 3em; width: 100%; }
    .stMetric { background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #00539C; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Function: Estimasi Tekanan Uap (ASTM D323 Simplified) ---
def get_vapor_pressure_head(fluid_type, temp_c):
    """
    Mengembalikan estimasi Vapor Pressure Head (Hv) dalam meter.
    Ini adalah pendekatan teknis untuk membantu inspektor lapangan.
    """
    # Specific Gravity rata-rata (SG)
    sg = 0.74 if fluid_type == "Mogas (Pertamax/Pertalite)" else 0.84 # Solar
    
    # Estimasi Tekanan Uap (pendekatan Antoine Equation sederhana untuk BBM)
    # Satuan output fungsi ini dikonversi ke Meter Head
    if fluid_type == "Mogas (Pertamax/Pertalite)":
        # Bensin sangat volatil terhadap suhu
        if temp_c < 30: vp_kpa = 40
        elif temp_c < 40: vp_kpa = 55
        elif temp_c < 50: vp_kpa = 70
        else: vp_kpa = 90
    else:
        # Solar/Diesel relatif stabil
        vp_kpa = 5 if temp_c < 50 else 10

    # Konversi kPa ke Meter Head: H = (P_kpa * 10.197) / (SG * 100) -> approx formula
    # H = P / (rho * g)
    hv = (vp_kpa * 0.10197) / sg
    return hv, vp_kpa

# ==============================================================================
# 2. HEADER & SIDEBAR CONFIGURATION
# ==============================================================================
st.title("🛡️ Digital Reliability Assistant")
st.markdown("**Infrastructure Management & Project - Terminal Facilities Maintenance**")
st.markdown("---")

st.sidebar.header("⚙️ 1. Standar Acuan (Reference)")
standard_selected = st.sidebar.selectbox(
    "Pilih Standar Inspeksi:",
    ("API 610 (Critical Pumps)", "NEMA MG 1 (Electric Motors)", "ISO 10816 (General Utility)")
)

# --- LOGIC LIMIT ALARM (DYNAMIC THRESHOLD) ---
if "API 610" in standard_selected:
    st.sidebar.info("ℹ️ **API 610 11th Ed.**\nLimit: **3.0 mm/s**\nDigunakan untuk Pompa Transfer/Loading BBM Utama.")
    limit_vib = 3.0
    std_ref = "API 610 Table 8"
elif "NEMA" in standard_selected:
    st.sidebar.warning("ℹ️ **NEMA MG 1 Part 7**\nLimit: **~2.7 mm/s** (Converted from Peak)\nFokus pada Motor Listrik.")
    limit_vib = 2.7
    std_ref = "NEMA MG 1 Sec 7.8"
else:
    st.sidebar.success("ℹ️ **ISO 10816-3**\nLimit: **4.5 mm/s** (Zone B)\nUntuk Pompa Air / Utilitas Umum.")
    limit_vib = 4.5
    std_ref = "ISO 10816-3 Zone B"

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. Data Fluida (Untuk NPSH)")
fluid_type = st.sidebar.radio("Jenis Produk:", ("Mogas (Pertamax/Pertalite)", "Gasoyl (Solar/Dex)"))
temp_actual = st.sidebar.number_input("Suhu Operasi Aktual (°C):", value=32.0, step=0.5, help="Diambil dengan Temp Gun di Pipa Suction")

# Hitung Vapor Pressure otomatis di background
hv_actual, vp_kpa_display = get_vapor_pressure_head(fluid_type, temp_actual)
st.sidebar.caption(f"🧪 Estimasi Tekanan Uap ({std_ref}): {vp_kpa_display} kPa")

# ==============================================================================
# 3. INPUT FORM (DATA LAPANGAN)
# ==============================================================================
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🔍 Sensor Vibrasi")
    vib_val = st.number_input("Vibrasi Overall (mm/s RMS)", 0.0, 20.0, 0.0, step=0.01)
    noise_val = st.number_input("Noise Level (dB)", 0.0, 120.0, 0.0, step=1.0)

with col2:
    st.subheader("🌡️ Sensor Suhu")
    temp_bearing = st.number_input("Suhu Bearing (°C)", 0.0, 150.0, 0.0, step=0.1)
    # Suhu fluida diambil dari sidebar agar sinkron dengan perhitungan NPSH

with col3:
    st.subheader("⚙️ Hidrolis & Motor")
    # INI KUNCI: Input Pressure Gauge untuk NPSH
    suction_press_bar = st.number_input("Suction Pressure Gauge (Bar)", -1.0, 10.0, 0.5, step=0.1, help="Bacaan Manometer di Suction")
    amp_unbalance = st.number_input("Ampere Unbalance (%)", 0.0, 50.0, 0.0, step=0.1)
    npsh_r = st.number_input("NPSH Required (Meter)", 0.0, 10.0, 2.5, step=0.1, help="Lihat di Nameplate Pompa")

analyze_btn = st.button("RUN DIAGNOSTICS & COMPLIANCE CHECK")

# ==============================================================================
# 4. ENGINE ANALISIS (THE BRAIN)
# ==============================================================================
if analyze_btn:
    st.markdown("---")
    
    # --- A. PERHITUNGAN NPSH (ENGINEERING CALCULATION - ANSI/HI 1.3) ---
    # Konversi Pressure Gauge (Bar) ke Head (Meter)
    # Asumsi SG fluid rata-rata
    sg_fluid = 0.74 if "Mogas" in fluid_type else 0.84
    h_gauge = (suction_press_bar * 10.197) / sg_fluid
    
    # Tekanan Atmosfer (Hb) asumsi di permukaan laut (10.33 m air)
    h_atm = 10.33 / sg_fluid
    
    # NPSHa = H_atm + H_gauge - H_vapor + VelocityHead(diabaikan utk safety)
    npsh_a = h_atm + h_gauge - hv_actual
    
    # NPSH Margin Check (API 610 recommend 1 meter margin)
    npsh_margin = npsh_a - npsh_r
    
    # --- B. DIAGNOSA LOGIC ---
    issues = []
    actions = []
    status_color = "green"
    status_text = "NORMAL OPERATION"

    # 1. Logic Kavitasi (Gabungan Data Sensor + Rumus Fisika)
    is_cavitation_sensor = (noise_val > 90) and (suction_press_bar < 0.5)
    is_cavitation_physics = (npsh_margin < 1.0) # Margin tipis (< 1 meter)

    if is_cavitation_physics:
        issues.append(f"⚠️ **RISIKO KAVITASI (TEORITIS):** NPSH Available ({npsh_a:.2f}m) terlalu dekat dengan Required ({npsh_r}m).")
        actions.append("🔧 Cek Saringan (Strainer) Suction, kemungkinan kotor menyebabkan pressure drop.")
        actions.append("🔧 Pastikan Level Tangki Supply cukup tinggi.")
        if is_cavitation_sensor:
            status_text = "CRITICAL CAVITATION"
            status_color = "red"
            issues.append("⛔ **KONFIRMASI SENSOR:** Terdeteksi suara bising tinggi & tekanan rendah. Kavitasi sedang terjadi!")
    
    # 2. Logic Vibrasi (Sesuai Standar Pilihan)
    if vib_val > limit_vib:
        status_text = "VIBRATION HIGH"
        status_color = "red" if vib_val > (limit_vib * 1.5) else "orange"
        issues.append(f"⚠️ **VIBRASI TINGGI:** Terukur {vib_val} mm/s (Melebihi limit {standard_selected}: {limit_vib} mm/s).")
        
        # Cek Cross-Diagnostic
        if temp_bearing > 80:
            issues.append("👉 **Indikasi: MISALIGNMENT.** (Vibrasi + Panas).")
            actions.append("🔧 Lakukan Laser Alignment check saat shutdown.")
        else:
            issues.append("👉 **Indikasi: UNBALANCE / LOOSENESS.**")
            actions.append("🔧 Cek kekencangan baut pondasi.")

    # 3. Logic Motor (NEMA)
    if amp_unbalance > 10.0:
        issues.append(f"⚠️ **MASALAH LISTRIK:** Unbalance {amp_unbalance}% (Max NEMA: 10%).")
        actions.append("🔧 Cek terminasi kabel motor (Megger Test).")

    # --- C. TAMPILAN OUTPUT (UI) ---
    
    # Row 1: Status Utama
    if status_color == "green":
        st.success(f"### ✅ STATUS: {status_text}")
    elif status_color == "orange":
        st.warning(f"### ⚠️ STATUS: {status_text}")
    else:
        st.error(f"### ⛔ STATUS: {status_text}")

    # Row 2: Engineering Metrics (Card Style)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vibrasi Aktual", f"{vib_val} mm/s", delta=f"Limit: {limit_vib}", delta_color="inverse")
    m2.metric("Suction Gauge", f"{suction_press_bar} Bar", "Field Data")
    m3.metric("NPSH Available", f"{npsh_a:.2f} m", delta=f"Margin: {npsh_margin:.2f} m", delta_color="normal" if npsh_margin>1 else "inverse")
    m4.metric("Tekanan Uap (Est)", f"{vp_kpa_display} kPa", f"Temp: {temp_actual}°C")

    # Row 3: Detail Analisis
    st.subheader("📑 Laporan Analisis")
    
    with st.expander("Lihat Detail Diagnosa & Rekomendasi", expanded=True):
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.markdown("#### 🔍 Temuan Masalah (Findings)")
            if len(issues) > 0:
                for i in issues: st.write(i)
            else:
                st.write("Tidak ditemukan anomali signifikan.")

        with c_right:
            st.markdown("#### 🛠️ Rekomendasi Tindakan (Action Plan)")
            if len(actions) > 0:
                for a in actions: st.write(a)
            else:
                st.write("Lanjutkan monitoring rutin sesuai jadwal.")
    
    # Footer Referensi
    st.caption(f"Referensi Perhitungan: 1. Vibrasi: {std_ref} | 2. Kavitasi: ANSI/HI 1.3 & API 610 (NPSH Margin) | 3. Fluida: ASTM D323")
