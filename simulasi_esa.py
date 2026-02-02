import streamlit as st

# ==============================================================================
# KONFIGURASI HALAMAN & CSS INDUSTRI
# ==============================================================================
st.set_page_config(
    page_title="Pertamina Patra Niaga - Reliability Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan profesional
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 5px; border: 1px solid #e0e0e0; }
    .stAlert { padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# HEADER APLIKASI
# ==============================================================================
st.title("🛡️ Digital Reliability Assistant")
st.markdown("**PT Pertamina Patra Niaga - Infrastructure Management & Project**")
st.markdown("---")

# ==============================================================================
# 1. SIDEBAR: PENGATURAN STANDAR (THE BRAIN)
# ==============================================================================
st.sidebar.header("⚙️ Konfigurasi Standar & Aset")

# Pilihan Standar Acuan
standard_selected = st.sidebar.selectbox(
    "Pilih Standar Acuan:",
    (
        "API 610 - 11th Ed. (Critical Centrifugal Pumps)",
        "NEMA MG 1 - Part 7 (Electric Motors)",
        "ISO 10816-3 (General Industrial Machines)"
    ),
    help="Pilih standar sesuai tipe equipment dan kekritisannya."
)

# Konfigurasi Parameter Limit Berdasarkan Standar
limit_vib_warning = 0.0
limit_vib_danger = 0.0
std_ref_doc = ""

if "API 610" in standard_selected:
    # API 610: Centrifugal Pumps for Petroleum, Petrochemical and Natural Gas Industries
    # Limit: Max vibration 3.0 mm/s RMS (Overall) for horizontal pumps
    st.sidebar.info("ℹ️ **Mode: Critical (Migas)**\nToleransi sangat ketat untuk keamanan operasi BBM.")
    limit_vib_warning = 2.5  # Pre-alarm (Best Practice)
    limit_vib_danger = 3.0   # API 610 Limit
    std_ref_doc = "API 610 11th Edition, Table 8"

elif "NEMA MG 1" in standard_selected:
    # NEMA MG 1 Part 7: Mechanical Vibration - Measurement, Evaluation and Limits
    # Limit: 0.15 in/s Peak ~ 3.81 mm/s Peak ~ 2.7 mm/s RMS
    st.sidebar.warning("ℹ️ **Mode: Electric Motor**\nFokus pada kesehatan motor listrik (Driver).")
    limit_vib_warning = 2.0
    limit_vib_danger = 2.7   # Konversi dari 0.15 in/s Peak
    std_ref_doc = "NEMA MG 1-2016, Section 7.8.1"

elif "ISO 10816" in standard_selected:
    # ISO 10816-3: Evaluation of machine vibration
    st.sidebar.success("ℹ️ **Mode: General Utility**\nUntuk pompa air, fan, atau equipment non-kritis.")
    
    iso_group = st.sidebar.radio("Group Mesin:", ("Group 2 (15kW - 300kW)", "Group 1 (>300kW)"))
    foundation = st.sidebar.radio("Tipe Pondasi:", ("Rigid (Beton)", "Flexible (Rangka Baja)"))
    
    # Logic Matriks ISO 10816-3
    if "Group 2" in iso_group: # Medium Machines (Most common in Depot)
        if foundation == "Rigid":
            limit_vib_warning = 2.8 # Batas Zone A/B ke C
            limit_vib_danger = 4.5  # Batas Zone C ke D
        else: # Flexible
            limit_vib_warning = 4.5
            limit_vib_danger = 7.1
    else: # Large Machines
        if foundation == "Rigid":
            limit_vib_warning = 4.5
            limit_vib_danger = 7.1
        else: # Flexible
            limit_vib_warning = 7.1
            limit_vib_danger = 11.0
    
    std_ref_doc = "ISO 10816-3:2009, Annex A"

# Konfigurasi Tambahan (Suhu & Listrik)
st.sidebar.markdown("---")
st.sidebar.subheader("Parameter Lain")
insulation_class = st.sidebar.selectbox("Insulation Class Motor:", ("Class F (Max 155°C)", "Class B (Max 130°C)"))

# Penentuan Limit Suhu (NEMA MG-1)
# Rule of Thumb: Max Bearing Temp = Max Insulation - Safety Margin or standard bearing limit
if "Class F" in insulation_class:
    limit_temp_bearing = 90.0 # Warning
    limit_temp_danger = 100.0 # Critical
else:
    limit_temp_bearing = 80.0
    limit_temp_danger = 90.0

# ==============================================================================
# 2. INPUT DATA (FORM INSPEKTOR)
# ==============================================================================
col_in1, col_in2, col_in3 = st.columns(3)

with col_in1:
    st.markdown("### 📡 Parameter Fisik")
    vib_val = st.number_input("Vibrasi Overall (mm/s RMS)", value=0.0, step=0.1, format="%.2f")
    noise_val = st.number_input("Noise Level (dB)", value=0.0, step=1.0)

with col_in2:
    st.markdown("### 🌡️ Parameter Suhu")
    temp_val = st.number_input("Suhu Bearing (°C)", value=0.0, step=0.1)
    ambient_val = st.number_input("Suhu Ruangan/Ambient (°C)", value=30.0, step=1.0)

with col_in3:
    st.markdown("### ⚡ Parameter Operasi")
    amp_unbalance = st.number_input("Current Unbalance (%)", value=0.0, step=0.1, help="NEMA MG-1 Max 10%")
    suction_press = st.number_input("Suction Pressure (Bar)", value=1.0, step=0.1)

# Tombol Eksekusi
analyze = st.button("ANALISIS DATA (RUN DIAGNOSTICS)", type="primary", use_container_width=True)

# ==============================================================================
# 3. ENGINE DIAGNOSA & OUTPUT
# ==============================================================================
if analyze:
    st.divider()
    
    # --- LOGIC PENILAIAN STATUS ---
    status_vib = "NORMAL"
    if vib_val >= limit_vib_danger: status_vib = "DANGER"
    elif vib_val >= limit_vib_warning: status_vib = "WARNING"
    
    status_temp = "NORMAL"
    if temp_val >= limit_temp_danger: status_temp = "DANGER"
    elif temp_val >= limit_temp_bearing: status_temp = "WARNING"
    
    status_elec = "NORMAL"
    if amp_unbalance >= 10.0: status_elec = "DANGER" # NEMA Recommendation
    elif amp_unbalance >= 5.0: status_elec = "WARNING"

    # --- TAMPILAN METRIC UTAMA ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Standar Dipilih", standard_selected.split(" - ")[0], delta_color="off")
    c2.metric("Limit Vibrasi (Max)", f"{limit_vib_danger} mm/s", f"{vib_val - limit_vib_danger:.2f} gap", 
              delta_color="inverse" if vib_val > limit_vib_danger else "normal")
    c3.metric("Limit Suhu", f"{limit_temp_danger} °C", f"{temp_val - limit_temp_danger:.1f} gap",
              delta_color="inverse" if temp_val > limit_temp_danger else "normal")
    c4.metric("Limit Unbalance", "10.0 %", f"{amp_unbalance - 10.0:.1f} gap",
              delta_color="inverse" if amp_unbalance > 10 else "normal")

    # --- ALGORITMA DIAGNOSA KERUSAKAN (PRESCRIPTIVE ANALYTICS) ---
    findings = []
    actions = []
    
    # 1. Analisis Misalignment (Vibrasi + Suhu)
    if (status_vib != "NORMAL") and (status_temp != "NORMAL"):
        findings.append("🔍 **Indikasi Misalignment:** Terdeteksi Vibrasi Tinggi disertai Panas Berlebih.")
        actions.append("✅ Lakukan pengecekan **Laser Alignment** pada coupling pompa-motor.")
        actions.append("✅ Periksa kondisi **Shim Plate** pada kaki motor (kemungkinan soft-foot).")

    # 2. Analisis Kavitasi (Noise + Suction Pressure)
    if (noise_val > 90) and (suction_press < 0.5):
        findings.append("🔍 **Indikasi Kavitasi:** Suara bising (>90dB) dengan tekanan hisap rendah.")
        actions.append("✅ Cek **Strainer/Saringan** pada jalur suction (kemungkinan buntu).")
        actions.append("✅ Cek level tangki supply (Low Level). Pastikan NPSHa > NPSHr.")

    # 3. Analisis Bearing (Vibrasi + Noise + Suhu Normal)
    if (status_vib != "NORMAL") and (noise_val > 85) and (status_temp == "NORMAL"):
        findings.append("🔍 **Indikasi Kerusakan Bearing (Awal):** Vibrasi mekanis dengan noise tinggi.")
        actions.append("✅ Lakukan **Greasing/Pelumasan** ulang.")
        actions.append("✅ Jika bunyi menetap, jadwalkan penggantian bearing saat shutdown.")

    # 4. Analisis Elektrikal (Unbalance)
    if status_elec != "NORMAL":
        findings.append(f"🔍 **Masalah Kelistrikan:** Ketidakseimbangan arus sebesar {amp_unbalance}%.")
        actions.append("✅ Cek kekencangan koneksi kabel di **Terminal Box** (Loose Connection).")
        actions.append("✅ Lakukan pengukuran tahanan isolasi (**Megger Test**) pada winding stator.")

    # 5. Analisis Umum (Jika hanya Vibrasi Tinggi tanpa gejala lain)
    if (status_vib != "NORMAL") and not findings:
        findings.append("🔍 **Vibrasi Tinggi (Unspecified):** Parameter melebihi batas standar.")
        actions.append("✅ Cek kekencangan **Baut Pondasi** (Foundation Bolts).")
        actions.append("✅ Lakukan analisis spektrum vibrasi lanjutan.")

    # --- TAMPILAN KESIMPULAN & REKOMENDASI ---
    st.subheader("📑 Laporan Hasil & Rekomendasi")
    
    # Warna Card Berdasarkan Severity Tertinggi
    severity = "GREEN"
    if "DANGER" in [status_vib, status_temp, status_elec]: severity = "RED"
    elif "WARNING" in [status_vib, status_temp, status_elec]: severity = "ORANGE"

    if severity == "GREEN":
        st.success("✅ **KONDISI PERALATAN: NORMAL (ACCEPTABLE)**\n\nPeralatan beroperasi dalam batas toleransi standar yang dipilih. Lanjutkan monitoring rutin.")
    else:
        if severity == "RED":
            container = st.error
            header_text = "⛔ KONDISI PERALATAN: DANGER / ACTION REQUIRED"
        else:
            container = st.warning
            header_text = "⚠️ KONDISI PERALATAN: WARNING / ALERT"
            
        with container(icon="🚨"):
            st.markdown(f"**{header_text}**")
            st.markdown("### Diagnosis:")
            for f in findings:
                st.markdown(f"- {f}")
            
            st.markdown("### Rekomendasi Tindakan (Work Order):")
            for a in actions:
                st.markdown(a)

    # --- FOOTER REFERENSI ---
    with st.expander("📚 Lihat Referensi Standar yang Digunakan"):
        st.markdown(f"""
        **Dasar Penilaian:**
        1. **Vibrasi:** Mengacu pada document **{std_ref_doc}**. Limit Warning: {limit_vib_warning} mm/s, Danger: {limit_vib_danger} mm/s.
        2. **Suhu:** Mengacu pada **NEMA MG-1** Insulation Class {insulation_class.split(' ')[1]}.
        3. **Elektrikal:** Mengacu pada **NEMA MG-1** (Max Unbalance 10% untuk mencegah overheating stator).
        4. **Noise:** Mengacu pada standar K3 Umum (>85 dB wajib Earplug).
        """)
