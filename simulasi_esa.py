import streamlit as st

# ==========================================
# 1. KONFIGURASI HALAMAN & CSS INDUSTRIAL
# ==========================================
st.set_page_config(
    page_title="Reliability Assistant Pro",
    layout="wide",
    page_icon="🛡️🙏🏻",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan lebih profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1 { color: #0056b3; }
    .status-card { padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. HEADER RESMI (SESUAI TKI)
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_title:
    st.title("🛡️ Digital Reliability Assistant")
    st.markdown("#### Berdasarkan TKI No. C-017/F20500/2018-S9")
    st.caption("Standard Reference: ISO 10816-3 | NEMA MG-1 | API 610 | ISO 15243")

st.markdown("---")

# ==========================================
# 3. INITIALIZE SESSION STATE (UNTUK DEMO)
# ==========================================
defaults = {
    'vib_val': 1.2, 'noise_val': 75.0, 'temp_val': 60.0,
    'rpm_act': 1485, 'amp_act': 8.5,
    # PERBAIKAN: Gunakan 380.0 (Float) bukan 380 (Int)
    'v_rs': 380.0, 'v_st': 380.0, 'v_tr': 380.0 
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# 4. SIDEBAR: INPUT DATA LOGSHEET
# ==========================================
st.sidebar.header("📝 Input Data Inspeksi")

# A. NAMEPLATE (DATA STATIS)
with st.sidebar.expander("A. Spesifikasi Motor (Nameplate)", expanded=True):
    nameplate_rpm = st.number_input("Rated RPM", value=1500)
    fla = st.number_input("Full Load Ampere (FLA)", value=10.0)
    rated_volt = st.number_input("Rated Voltage (V)", value=380)

# B. DATA PENGUKURAN (DATA DINAMIS)
st.sidebar.subheader("B. Hasil Ukur Alat (TKI II.C)")

# 1. Vibrasi & Noise
c1, c2 = st.sidebar.columns(2)
vib_val = c1.number_input("Vibrasi (mm/s)", value=st.session_state['vib_val'], step=0.1, help="ISO 10816 Limit: 4.5")
noise_val = c2.number_input("Noise (dB)", value=st.session_state['noise_val'], step=1.0)

# 2. Suhu & RPM
c3, c4 = st.sidebar.columns(2)
temp_val = c3.number_input("Suhu Brg (°C)", value=st.session_state['temp_val'], step=1.0)
rpm_act = c4.number_input("RPM Aktual", value=st.session_state['rpm_act'], step=5)

# 3. Listrik (3 Phase untuk Auto-Unbalance)
st.sidebar.markdown("**Listrik (Multimeter 3-Phase)**")
amp_act = st.sidebar.number_input("Ampere Rata-rata (A)", value=st.session_state['amp_act'], step=0.1)

c_v1, c_v2, c_v3 = st.sidebar.columns(3)
# PERBAIKAN: Ubah step=1 menjadi step=1.0
v_rs = c_v1.number_input("R-S", value=st.session_state['v_rs'], step=1.0)
v_st = c_v2.number_input("S-T", value=st.session_state['v_st'], step=1.0)
v_tr = c_v3.number_input("T-R", value=st.session_state['v_tr'], step=1.0)

# ==========================================
# 5. OTAK ANALISIS (CALCULATION ENGINE)
# ==========================================

def calculate_metrics(v1, v2, v3, amp, fla, rpm_act, rpm_ref):
    # 1. Hitung Voltage Unbalance (NEMA)
    avg_volt = (v1 + v2 + v3) / 3
    if avg_volt == 0: avg_volt = 1 # Prevent div by zero
    max_dev = max(abs(v1 - avg_volt), abs(v2 - avg_volt), abs(v3 - avg_volt))
    unbalance_pct = (max_dev / avg_volt) * 100
    
    # 2. Hitung Load & Slip
    load_pct = (amp / fla) * 100
    slip_pct = ((rpm_ref - rpm_act) / rpm_ref) * 100
    
    return unbalance_pct, avg_volt, load_pct, slip_pct

def determine_status(vib, noise, temp, unbalance, slip, load, amp, fla):
    # --- THRESHOLDS (BATAS AMAN) ---
    # ISO 10816-3 (Vibrasi)
    stat_vib = "Critical" if vib > 4.5 else "Warning" if vib > 2.8 else "Good"
    # NEMA MG-1 (Unbalance)
    stat_elec = "Bad" if unbalance > 5.0 else "Good"
    # General Bearing (Suhu)
    stat_temp = "Overheat" if temp > 90 else "High" if temp > 75 else "Normal"
    # Load Analysis
    if amp > fla * 1.05: stat_load = "Overload"
    elif amp < fla * 0.5: stat_load = "Underload"
    else: stat_load = "Normal"
    
    # --- DIAGNOSTIC LOGIC TREE (PRIORITY BASED) ---
    
    # 1. PRIORITY: KAVITASI (Safety Hazard)
    if stat_load == "Underload" and (noise > 85 or stat_vib != "Good"):
        return "CRITICAL", "INDIKASI KAVITASI / DRY RUN", "⛔ BAHAYA! Pompa kehilangan fluida (Loss of Prime). Ampere drop drastis. Cek sisi suction/tangki segera."

    # 2. PRIORITY: ELECTRICAL (Root Cause Check)
    # Cek listrik dulu sebelum bearing, karena listrik jelek bikin motor panas & getar
    if stat_elec == "Bad":
        return "WARNING", "GANGGUAN KUALITAS DAYA (Power Quality)", f"Terdeteksi Voltage Unbalance {unbalance:.2f}%. Ini menyebabkan panas berlebih dan vibrasi magnetik. Cek panel/trafo."

    # 3. PRIORITY: BEARING FAILURE
    if stat_vib in ["Warning", "Critical"] and (stat_temp in ["High", "Overheat"] or noise > 90):
        return "CRITICAL", "INDIKASI KERUSAKAN BEARING", "Kombinasi Getaran + Panas/Berisik menandakan gesekan mekanis tinggi. Segera jadwalkan penggantian bearing."

    # 4. PRIORITY: ROTOR BAR (Check Slip)
    # Jika getaran tidak parah, tapi RPM drop
    if slip > 3.0 and stat_load != "Overload":
        return "WARNING", "INDIKASI BROKEN ROTOR BAR", f"Slip motor tinggi ({slip:.2f}%) pada beban normal. Efisiensi rotor menurun. Cek kondisi batang rotor."

    # 5. PRIORITY: MISALIGNMENT / UNBALANCE
    if stat_vib in ["Warning", "Critical"] and stat_load == "Normal" and stat_temp == "Normal":
        return "WARNING", "INDIKASI MISALIGNMENT / UNBALANCE", "Masalah mekanis murni (Tanpa gesekan/panas). Cek baut pondasi (soft foot) dan lakukan Laser Alignment."

    # 6. PRIORITY: OVERLOAD
    if stat_load == "Overload":
        return "WARNING", "OPERASI OVERLOAD", "Motor bekerja di atas kapasitas (Ampere > FLA). Cek bukaan valve atau berat jenis fluida."

    # 7. PRIORITY: HEALTHY
    # Syarat ketat: Vibrasi Good, Listrik Good, Slip < 3%
    if stat_vib == "Good" and stat_elec == "Good" and slip < 3.0:
        return "HEALTHY", "KONDISI PRIMA (HEALTHY)", "Parameter operasi dalam batas normal. Lanjutkan jadwal maintenance rutin."

    return "WARNING", "ANOMALI TIDAK TERDEFINISI", "Parameter campuran. Lakukan inspeksi manual mendalam."

# ==========================================
# 6. EKSEKUSI PROGRAM
# ==========================================

# A. Hitung Metrik
unbalance_pct, avg_volt, load_pct, slip_pct = calculate_metrics(
    v_rs, v_st, v_tr, amp_act, fla, rpm_act, nameplate_rpm
)

# B. Tentukan Diagnosa
severity, diag_title, recommendation = determine_status(
    vib_val, noise_val, temp_val, unbalance_pct, slip_pct, load_pct, amp_act, fla
)

# ==========================================
# 7. DASHBOARD DISPLAY
# ==========================================

# --- SECTION 1: STATUS CARD ---
st.subheader("📊 Status Kesehatan Mesin")

if severity == "HEALTHY":
    bg_color = "#d4edda"
    text_color = "#155724"
    icon = "✅"
elif severity == "WARNING":
    bg_color = "#fff3cd"
    text_color = "#856404"
    icon = "⚠️"
else: # CRITICAL
    bg_color = "#f8d7da"
    text_color = "#721c24"
    icon = "🚨"

st.markdown(f"""
    <div style="background-color: {bg_color}; color: {text_color}; padding: 20px; border-radius: 10px; border-left: 10px solid {text_color};">
        <h2 style="margin:0; color: {text_color};">{icon} {diag_title}</h2>
        <p style="margin-top:10px; font-weight:bold;">REKOMENDASI: {recommendation}</p>
    </div>
""", unsafe_allow_html=True)

# --- SECTION 2: KEY METRICS (3 Columns) ---
st.write("") # Spacer
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Vibrasi (ISO)", f"{vib_val} mm/s", "Batas: 4.5", delta_color="inverse")
with m2:
    st.metric("Motor Load", f"{load_pct:.1f} %", f"{amp_act} A")
with m3:
    # Logic warna Unbalance
    ub_delta_color = "normal" if unbalance_pct < 5 else "inverse"
    st.metric("Unbalance (NEMA)", f"{unbalance_pct:.2f} %", "Batas: 5.0%", delta_color=ub_delta_color)
with m4:
    st.metric("Slip Rotor", f"{slip_pct:.2f} %", f"{rpm_act} RPM")

# --- SECTION 3: DETAILED ANALYSIS & REFERENCE ---
st.divider()
c_left, c_right = st.columns([2, 1])

with c_left:
    st.markdown("### 🔍 Analisis Parameter")
    # Tabel mini untuk detail
    st.markdown(f"""
    - **Suhu Bearing:** {temp_val}°C (Normal < 75°C)
    - **Noise Level:** {noise_val} dB (Normal < 85 dB)
    - **Tegangan Rata-rata:** {avg_volt:.1f} Volt
    """)

with c_right:
    with st.expander("📚 DASAR REFERENSI (SCIENTIFIC BASIS)"):
        st.markdown("""
        **Validasi Standard:**
        1.  **ISO 10816-3**: Vibrasi > 4.5 mm/s (Zona C/D) = Indikasi Kerusakan Mekanis.
        2.  **NEMA MG-1**: Voltage Unbalance > 5% = Derating kapasitas 25% (Electrical Fault).
        3.  **Pump Handbook**: Ampere < 50% FLA + Noise = Loss of Prime (Kavitasi).
        4.  **ISO 15243**: Bearing Fault ditandai dengan Vibrasi + Panas + Noise.
        """)

# ==========================================
# 8. PANEL SIMULASI (DEMO MODE)
# ==========================================
st.divider()
st.markdown("### 🎛️ Demo Simulator (Untuk Presentasi Manager)")
st.caption("Pilih skenario kerusakan untuk menguji sistem diagnosa:")

col_d1, col_d2, col_d3 = st.columns(3)
col_d4, col_d5, col_d6 = st.columns(3)

# Helper function untuk update state (YANG SUDAH DIPERBAIKI)
def set_demo(vib, noise, temp, rpm, amp, v_unbalance=False):
    st.session_state['vib_val'] = vib
    st.session_state['noise_val'] = noise
    st.session_state['temp_val'] = temp
    st.session_state['rpm_act'] = rpm
    st.session_state['amp_act'] = amp
    # Set Voltages
    if v_unbalance:
        st.session_state['v_rs'] = 380.0
        # GANTI 360.0 JADI 350.0 AGAR UNBALANCE > 5%
        st.session_state['v_st'] = 350.0 
        st.session_state['v_tr'] = 380.0
    else:
        st.session_state['v_rs'] = 380.0
        st.session_state['v_st'] = 380.0
        st.session_state['v_tr'] = 380.0

if col_d1.button("1. KASUS SEHAT (HEALTHY)"):
    set_demo(vib=1.2, noise=75.0, temp=60.0, rpm=1485, amp=8.5)
    st.rerun()

if col_d2.button("2. KAVITASI (DRY RUN)"):
    # Ampere Drop + Berisik
    set_demo(vib=3.5, noise=95.0, temp=65.0, rpm=1495, amp=4.0)
    st.rerun()

if col_d3.button("3. BEARING PECAH"):
    # Getar + Panas + Ampere Naik
    set_demo(vib=7.5, noise=98.0, temp=95.0, rpm=1470, amp=11.0)
    st.rerun()

if col_d4.button("4. MISALIGNMENT"):
    # Getar Tinggi + Dingin + Ampere Normal
    set_demo(vib=5.5, noise=80.0, temp=62.0, rpm=1480, amp=8.5)
    st.rerun()

if col_d5.button("5. ELECTRICAL FAULT"):
    # Unbalance Voltages
    set_demo(vib=3.2, noise=78.0, temp=85.0, rpm=1480, amp=9.0, v_unbalance=True)
    st.rerun()

if col_d6.button("6. BROKEN ROTOR BAR"):
    # Slip Tinggi (RPM Drop)
    set_demo(vib=2.5, noise=80.0, temp=70.0, rpm=1420, amp=9.5)
    st.rerun()
