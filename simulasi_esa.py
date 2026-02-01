import streamlit as st

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Digital Reliability Assistant", layout="wide", page_icon="🛡️")

# --- HEADER RESMI ---
col_logo, col_title = st.columns([1, 5])
with col_title:
    st.title("🛡️ Digital Reliability Assistant")
    st.markdown("### Berdasarkan TKI No. C-017/F20500/2018-S9")
    st.markdown("**Pelaksanaan Inspeksi Pompa Produk dan Penggerak**")
    st.caption("Engineered by: OJT Student | Ref: ISO 10816-3, NEMA MG-1, & Pump Handbook")

st.markdown("---")

# --- SIDEBAR: INPUT DATA ---
st.sidebar.header("📝 Input Data Inspeksi")

# A. DATA NAMEPLATE
st.sidebar.subheader("A. Spesifikasi Motor")
nameplate_rpm = st.sidebar.number_input("Rated RPM", value=1500)
fla = st.sidebar.number_input("Full Load Ampere (FLA)", value=10.0)
rated_volt = st.sidebar.number_input("Rated Voltage (V)", value=380)

# B. DATA PENGUKURAN (SESSION STATE)
st.sidebar.subheader("B. Hasil Ukur Alat (TKI II.C)")

if 'vib_val' not in st.session_state: st.session_state['vib_val'] = 1.5
if 'noise_val' not in st.session_state: st.session_state['noise_val'] = 75.0
if 'temp_val' not in st.session_state: st.session_state['temp_val'] = 60.0
if 'rpm_act' not in st.session_state: st.session_state['rpm_act'] = 1485
if 'volt_act' not in st.session_state: st.session_state['volt_act'] = 380
if 'amp_act' not in st.session_state: st.session_state['amp_act'] = 8.5
if 'is_unbalance' not in st.session_state: st.session_state['is_unbalance'] = False

vib_val = st.sidebar.number_input("1. Vibration (mm/s)", value=st.session_state['vib_val'], step=0.1)
noise_val = st.sidebar.number_input("2. Noise (dB)", value=st.session_state['noise_val'], step=1.0)
temp_val = st.sidebar.number_input("3. Suhu Bearing (°C)", value=st.session_state['temp_val'], step=1.0)
rpm_act = st.sidebar.number_input("4. RPM Aktual", value=st.session_state['rpm_act'], step=5)
volt_act = st.sidebar.number_input("5a. Voltage (V)", value=st.session_state['volt_act'], step=1)
amp_act = st.sidebar.number_input("5b. Ampere (A)", value=st.session_state['amp_act'], step=0.1)
is_unbalance = st.sidebar.checkbox("Unbalance > 5%?", value=st.session_state['is_unbalance'])

# --- OTAK SISTEM PAKAR (LOGIC FIXED) ---
def diagnose_comprehensive(vib, noise, temp, rpm_act, rpm_ref, volt, amp, fla, unbalance):
    # 1. HITUNG PARAMETER
    load_percent = (amp / fla) * 100
    slip_percent = ((rpm_ref - rpm_act) / rpm_ref) * 100
    
    # 2. STATUS PARAMETER
    if vib < 2.8: vib_s = "Good"
    elif vib < 4.5: vib_s = "Warning"
    else: vib_s = "Critical"
    
    if amp > fla * 1.05: amp_s = "Overload"
    elif amp < fla * 0.5: amp_s = "Underload"
    else: amp_s = "Normal"
    
    if temp < 75: temp_s = "Normal"
    elif temp < 90: temp_s = "High"
    else: temp_s = "Overheat"
    
    if unbalance or abs(volt - rated_volt)/rated_volt > 0.1: elec_s = "Bad"
    else: elec_s = "Good"

    # 3. POHON KEPUTUSAN (URUTAN DIPERBAIKI)
    diag = "Anomali Tidak Terdefinisi"
    rec = "Cek manual."
    severity = "WARNING"
    
    # KASUS 1: SEHAT (Wajib Slip < 3%)
    if vib_s == "Good" and amp_s == "Normal" and temp_s == "Normal" and elec_s == "Good" and slip_percent < 3.0:
        diag = "KONDISI PRIMA (HEALTHY)"
        rec = "Lanjutkan operasi normal."
        severity = "HEALTHY"

    # KASUS 2: KAVITASI / DRY RUN
    elif amp_s == "Underload" and (noise > 85 or vib_s != "Good"):
        diag = "INDIKASI KAVITASI / DRY RUN"
        rec = "⛔ BAHAYA! Stop Pompa. Cek sisi suction/tangki. Beban hilang."
        severity = "CRITICAL"

    # KASUS 3: ELECTRICAL FAULT (DIPINDAH KE ATAS)
    # Kita cek ini DULUAN sebelum Bearing.
    # Kenapa? Karena Unbalance listrik bisa menyebabkan gejala panas & getar (mirip bearing).
    # Jika listrik pincang, itu diagnosa utamanya.
    elif elec_s == "Bad":
        diag = "GANGGUAN KUALITAS DAYA (Power Quality)"
        rec = "Cek tegangan antar fase. Unbalance menyebabkan panas gulungan & vibrasi magnetik."
        severity = "WARNING"
        
    # KASUS 4: BEARING FAILURE
    # Baru cek bearing kalau listrik aman.
    elif vib_s in ["Warning", "Critical"] and (temp_s in ["High", "Overheat"] or noise > 90):
        diag = "INDIKASI KERUSAKAN BEARING"
        rec = "Gesekan tinggi terdeteksi. Cek greasing atau ganti bearing segera."
        severity = "CRITICAL"

    # KASUS 5: MISALIGNMENT / UNBALANCE
    elif vib_s in ["Warning", "Critical"] and amp_s == "Normal" and temp_s == "Normal":
        diag = "INDIKASI MISALIGNMENT / UNBALANCE"
        rec = "Masalah mekanis murni. Cek baut pondasi (soft foot) & Laser Alignment."
        severity = "WARNING"
    
    # KASUS 6: BROKEN ROTOR BAR
    elif slip_percent > 3.0: 
        diag = "INDIKASI ROTOR BAR RETAK (High Slip)"
        rec = "RPM drop tidak wajar (>3%). Motor kehilangan torsi. Cek rotor."
        severity = "WARNING"

    # KASUS 7: OVERLOAD
    elif amp_s == "Overload":
        diag = "OPERASI OVERLOAD"
        rec = "Beban berlebih. Cek bukaan valve atau densitas fluida."
        severity = "WARNING"

    return load_percent, slip_percent, diag, rec, severity, vib_s, temp_s

# --- EKSEKUSI ---
load, slip, diag, rec, sev, stat_vib, stat_temp = diagnose_comprehensive(
    vib_val, noise_val, temp_val, rpm_act, nameplate_rpm, volt_act, amp_act, fla, is_unbalance
)

# --- TAMPILAN DASHBOARD ---
st.subheader("📊 Hasil Analisa")
col1, col2 = st.columns([3, 2])

with col1:
    if sev == "HEALTHY": st.success(f"### ✅ {diag}")
    elif sev == "WARNING": st.warning(f"### ⚠️ {diag}")
    else: st.error(f"### 🚨 {diag}")
    st.info(f"**Rekomendasi:** {rec}")

with col2:
    c_a, c_b, c_c = st.columns(3)
    c_a.metric("Load", f"{load:.0f}%", f"{amp_act} A")
    c_b.metric("Vibrasi", f"{vib_val}", stat_vib)
    c_c.metric("Slip", f"{slip:.1f}%", f"{rpm_act} RPM")
    
    health_score = 100
    if sev == "WARNING": health_score = 60
    if sev == "CRITICAL": health_score = 20
    st.write("Machine Health Index:")
    st.progress(health_score)

# --- PANEL TOMBOL DEMO ---
st.divider()
st.markdown("### 🎛️ Panel Simulasi Kasus (Demo Manager)")
c1, c2, c3 = st.columns(3)

if c1.button("1. KASUS SEHAT"):
    st.session_state.update({'vib_val': 1.2, 'noise_val': 75.0, 'temp_val': 60.0, 'rpm_act': 1485, 'volt_act': 380, 'amp_act': 8.5, 'is_unbalance': False})
    st.rerun()

if c2.button("2. KASUS KAVITASI"):
    st.session_state.update({'vib_val': 3.5, 'noise_val': 95.0, 'temp_val': 65.0, 'rpm_act': 1495, 'volt_act': 380, 'amp_act': 4.0, 'is_unbalance': False})
    st.rerun()

if c3.button("3. BEARING PECAH"):
    st.session_state.update({'vib_val': 7.5, 'noise_val': 98.0, 'temp_val': 95.0, 'rpm_act': 1470, 'volt_act': 380, 'amp_act': 11.0, 'is_unbalance': False})
    st.rerun()

c4, c5, c6 = st.columns(3)

if c4.button("4. MISALIGNMENT"):
    st.session_state.update({'vib_val': 5.5, 'noise_val': 80.0, 'temp_val': 62.0, 'rpm_act': 1480, 'volt_act': 380, 'amp_act': 8.5, 'is_unbalance': False})
    st.rerun()

if c5.button("5. ELECTRICAL FAULT"):
    st.session_state.update({'vib_val': 3.2, 'noise_val': 78.0, 'temp_val': 85.0, 'rpm_act': 1480, 'volt_act': 370, 'amp_act': 9.0, 'is_unbalance': True})
    st.rerun()

if c6.button("6. BROKEN ROTOR BAR"):
    st.session_state.update({'vib_val': 2.5, 'noise_val': 80.0, 'temp_val': 70.0, 'rpm_act': 1420, 'volt_act': 380, 'amp_act': 9.5, 'is_unbalance': False})
    st.rerun()

st.divider()
with st.expander("📚 DASAR REFERENSI"):
    st.markdown("""
    **Sistem Pakar ini mengacu pada:**
    1.  **ISO 10816-3 (Vibrasi)**: Menetapkan batas Zona C (Warning) di angka 2.8 - 4.5 mm/s.
    2.  **Pump Handbook (Kavitasi)**: Menjelaskan fenomena *Loss of Prime* menyebabkan Ampere Drop & Noise.
    3.  **ISO 15243 (Bearing)**: Kerusakan elemen gelinding menyebabkan vibrasi frekuensi tinggi & panas.
    4.  **NEMA MG-1 (Rotor Bar)**: Slip >3-5% pada beban normal indikasi *broken rotor bars*.
    """)
