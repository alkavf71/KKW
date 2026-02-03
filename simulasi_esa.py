import streamlit as st
import numpy as np
import pandas as pd

# ==========================================
# 1. KONFIGURASI HALAMAN & JUDUL
# ==========================================
st.set_page_config(
    page_title="Digital Reliability Assistant - Pertamina",
    page_icon="🛡️",
    layout="wide"
)

# Header Utama
st.title("🛡️ Digital Reliability Assistant")
st.markdown("**Infrastructure Management & Project - PT Pertamina Patra Niaga**")
st.markdown("---")

# ==========================================
# 2. SIDEBAR: INPUT PARAMETER & MODE
# ==========================================
st.sidebar.header("⚙️ Konfigurasi Standar")

# --- A. PEMILIHAN STANDAR (CRITICAL FOR MANAGER) ---
# Ini fitur kuncinya: Memilih mode ketat (API) atau mode pantau (ISO)
operation_mode = st.sidebar.radio(
    "Pilih Mode Operasi:",
    ("Routine Monitoring (ISO)", "Commissioning / New Install (API)"),
    index=0,
    help="Commissioning menggunakan toleransi API yang jauh lebih ketat."
)

st.sidebar.markdown("---")
st.sidebar.header("📝 Input Data Lapangan")

# --- B. INPUT SPESIFIKASI MOTOR ---
with st.sidebar.expander("1. Spesifikasi Motor (NEMA/IEC)", expanded=True):
    rpm_input = st.number_input("Kecepatan Putar (RPM)", value=2980, step=10)
    power_kw = st.number_input("Daya Motor (kW)", value=75.0)
    
    # Hitung Frekuensi Fundamental
    freq_1x = rpm_input / 60.0
    st.caption(f"Fundamental Freq (1x): **{freq_1x:.2f} Hz**")

# --- C. INPUT DATA VIBRASI (SPEKTRUM) ---
with st.sidebar.expander("2. Data Vibrasi (Spectrum Analyzer)", expanded=True):
    st.markdown("Satuan: **mm/s (RMS)**")
    
    # Input Radial (Horizontal/Vertical)
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        rad_1x = st.number_input("Radial 1x RPM", value=0.0)
        rad_2x = st.number_input("Radial 2x RPM", value=0.0)
    with col_v2:
        ax_1x = st.number_input("Axial 1x RPM", value=0.0)
        ax_2x = st.number_input("Axial 2x RPM", value=0.0)
    
    # Input Overall (Total Energy)
    overall_rms = st.number_input("Overall Velocity RMS", value=0.0, help="Nilai total dari Vibration Meter")

# --- D. INPUT DATA BEARING & HIGH FREQ ---
with st.sidebar.expander("3. Data Bearing (Envelope)", expanded=False):
    st.markdown("Satuan: **gE (Acceleration Envelope)**")
    env_peak_amp = st.number_input("Puncak Envelope Tertinggi (gE)", value=0.0)
    env_peak_freq = st.number_input("Frekuensi Puncak tsb (Hz)", value=0.0)
    
    st.markdown("**Geometri Bearing (Untuk Rumus BPFO/BPFI):**")
    # Default: Bearing 6309
    n_balls = st.number_input("Jumlah Bola (N)", value=8)
    bd = st.number_input("Diameter Bola (Bd - mm)", value=17.0)
    
    # === PERBAIKAN DI SINI (Ganti 'pd' jadi 'd_pitch') ===
    d_pitch = st.number_input("Pitch Diameter (Pd - mm)", value=72.5) 
    
    angle = st.number_input("Contact Angle (deg)", value=0.0)
# ==========================================
# 3. LOGIC CENTER (OTAK DIAGNOSA)
# ==========================================

# --- FUNGSI 1: CEK LIMIT (API vs ISO) ---
def check_severity_status(rms_val, mode, kw):
    """
    Menentukan Status Pass/Fail berdasarkan Standar yang dipilih.
    """
    status = ""
    color = ""
    standard_used = ""
    limit_val = 0.0

    if "Commissioning" in mode:
        # --- LOGIKA API 610 (KETAT) ---
        standard_used = "API 610 (Centrifugal Pumps)"
        limit_val = 3.0 # Limit ketat untuk pompa baru (mm/s)
        
        if rms_val <= limit_val:
            status = "PASSED (Commissioning Accepted)"
            color = "success"
        else:
            status = "REJECTED (Commissioning Failed)"
            color = "error"
            
    else:
        # --- LOGIKA ISO 10816-3 (MONITORING) ---
        standard_used = "ISO 10816-3 (Class II - Medium)"
        # Limit Zone A/B/C/D
        limit_a = 1.12
        limit_b = 2.80
        limit_c = 7.10
        
        if rms_val < limit_a:
            status = "ZONE A: Good (New)"
            color = "success"
        elif rms_val < limit_b:
            status = "ZONE B: Satisfactory (Acceptable)"
            color = "success" # Masih hijau tapi perlu pantau
        elif rms_val < limit_c:
            status = "ZONE C: Unsatisfactory (Plan Maintenance)"
            color = "warning"
        else:
            status = "ZONE D: Unacceptable (DANGER)"
            color = "error"
            
    return status, color, standard_used, limit_val

# --- FUNGSI 2: DIAGNOSA MISALIGNMENT & UNBALANCE ---
def analyze_spectrum_faults(rad1, rad2, ax1, ax2, rms):
    faults = []
    
    # Hindari pembagian nol
    ref_rad = rad1 if rad1 > 0.1 else 0.1
    
    # A. CEK MISALIGNMENT (ISO 13373-2 & API 686 Context)
    # Ratio Calculation
    ratio_par = rad2 / ref_rad
    ratio_ang = ax1 / ref_rad
    
    # Logic Parallel
    if ratio_par > 0.5 and rad2 > 1.0:
        severity = "HIGH" if ratio_par > 1.0 else "MODERATE"
        faults.append(f"Parallel Misalignment ({severity}) - Dominan 2x RPM")
        
    # Logic Angular
    if ratio_ang > 0.5 and ax1 > 1.0:
        severity = "HIGH" if ax1 > rad1 else "MODERATE"
        faults.append(f"Angular Misalignment ({severity}) - Dominan 1x Axial")
        
    # B. CEK UNBALANCE (ISO 13373-2)
    # Logic: Dominan 1x Radial, Axial Rendah
    is_dominant_1x = rad1 > (0.8 * rms) # 1x menyumbang 80% energi total
    is_low_axial = rad1 > (3 * ax1)
    
    if is_dominant_1x and is_low_axial and rad1 > 2.0:
        faults.append("Rotor Unbalance - Dominan 1x Radial Murni")
        
    return faults

# --- FUNGSI 3: DIAGNOSA BEARING (Harris Formula) ---
def calculate_bearing_freqs(n, d_ball, d_pitch, contact_angle, rpm_val):
    fr = rpm_val / 60.0
    cos_phi = np.cos(np.radians(contact_angle))
    
    bpfo = (n / 2) * fr * (1 - (d_ball / d_pitch) * cos_phi)
    bpfi = (n / 2) * fr * (1 + (d_ball / d_pitch) * cos_phi)
    
    return bpfo, bpfi

# ==========================================
# 4. TAMPILAN DASHBOARD (UI)
# ==========================================

# --- SECTION A: INDIKATOR STANDAR (VISUAL CUE) ---
# Ini untuk memastikan User sadar standar apa yang dipakai
if "Commissioning" in operation_mode:
    st.error("🚨 MODE: COMMISSIONING / NEW INSTALLATION (API STANDARD ACTIVE)")
    st.caption("Toleransi sangat ketat sesuai API 610 & API 686. Tidak ada toleransi untuk 'Zone C'.")
else:
    st.info("📊 MODE: ROUTINE MONITORING (ISO STANDARD ACTIVE)")
    st.caption("Toleransi berdasarkan Zona Kesehatan Mesin (ISO 10816-3).")

# Eksekusi Logic
status_msg, status_color, std_name, limit_reff = check_severity_status(overall_rms, operation_mode, power_kw)
mech_faults = analyze_spectrum_faults(rad_1x, rad_2x, ax_1x, ax_2x, overall_rms)

# --- SECTION B: STATUS KESEHATAN UTAMA ---
st.subheader("1. Evaluasi Status Mesin (Overall Health)")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Overall Vibrasi", f"{overall_rms} mm/s")

with col2:
    st.metric("Limit Standar", f"{limit_reff} mm/s", delta_color="inverse")
    st.caption(f"Ref: {std_name}")

with col3:
    if status_color == "success":
        st.success(f"### {status_msg}")
    elif status_color == "warning":
        st.warning(f"### {status_msg}")
    else:
        st.error(f"### {status_msg}")

st.markdown("---")

# --- SECTION C: DIAGNOSA MENDALAM (TABS) ---
tab1, tab2, tab3 = st.tabs(["🔍 Mechanical Diagnosis", "⚙️ Bearing Health", "🛠️ Action Plan (API 686)"])

with tab1:
    st.subheader("Analisa Spektrum (Misalignment & Unbalance)")
    st.write("Menganalisa rasio amplitudo pada frekuensi 1x dan 2x RPM.")
    
    if len(mech_faults) > 0:
        for fault in mech_faults:
            st.error(f"⚠️ Terdeteksi: **{fault}**")
            
        # Visualisasi Data Sederhana
        chart_data = pd.DataFrame({
            'Frekuensi': ['1x Radial', '2x Radial', '1x Axial', '2x Axial'],
            'Amplitudo (mm/s)': [rad_1x, rad_2x, ax_1x, ax_2x]
        })
        st.bar_chart(chart_data, x='Frekuensi', y='Amplitudo (mm/s)')
    else:
        st.success("✅ Tidak ditemukan indikasi Misalignment atau Unbalance yang signifikan pada spektrum.")
        st.caption("Pastikan data spektrum (1x, 2x) sudah diinput dengan benar di sidebar.")

with tab2:
    st.subheader("Analisa Bearing (High Frequency)")
    
    # Hitung BPFO/BPFI
        calc_bpfo, calc_bpfi = calculate_bearing_freqs(n_balls, bd, d_pitch, angle, rpm_input)
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**BPFO (Outer Race):** {calc_bpfo:.2f} Hz")
        st.info(f"**BPFI (Inner Race):** {calc_bpfi:.2f} Hz")
    with c2:
        st.write(f"**Input Puncak Sensor:** {env_peak_freq:.2f} Hz")
        st.write(f"**Input Amplitudo:** {env_peak_amp:.2f} gE")
    
    # Logic Matching
    match_found = False
    tolerance = 0.05 * calc_bpfo # 5% toleransi
    
    if env_peak_amp > 0.5: # Threshold noise floor
        if abs(env_peak_freq - calc_bpfo) < tolerance:
            st.error("⚠️ **POSITIVE: OUTER RACE DEFECT DETECTED**")
            st.caption("Frekuensi puncak cocok dengan BPFO teoritis.")
            match_found = True
        elif abs(env_peak_freq - calc_bpfi) < tolerance:
            st.error("⚠️ **POSITIVE: INNER RACE DEFECT DETECTED**")
            st.caption("Frekuensi puncak cocok dengan BPFI teoritis.")
            match_found = True
            
        if not match_found and env_peak_amp > 1.0:
            st.warning("⚠️ High Frequency Noise detected (Lubrication Issue / Early Stage)")
    else:
        st.success("✅ Kondisi Bearing Normal (Amplitudo gE rendah)")

with tab3:
    st.subheader("Rekomendasi Perbaikan (API 686)")
    
    if "Misalignment" in str(mech_faults) or "Commissioning" in operation_mode:
        st.markdown("""
        Jika diagnosa menunjukkan Misalignment, atau Anda sedang melakukan Commissioning, 
        gunakan tabel toleransi **API 686 Chapter 7** berikut sebagai target laser alignment:
        """)
        
        # Tabel Toleransi Dinamis sesuai RPM
        tol_offset = "0.04 mm" if rpm_input > 2000 else "0.09 mm"
        tol_angle  = "0.05 mm/100mm" if rpm_input > 2000 else "0.07 mm/100mm"
        
        st.table(pd.DataFrame({
            "Parameter": ["Target Offset (Parallel)", "Target Angular (Sudut)", "Soft Foot Max"],
            f"Limit (Untuk {int(rpm_input)} RPM)": [tol_offset, tol_angle, "0.05 mm"]
        }))
        
        st.info("💡 **Tips:** Lakukan kompensasi Thermal Growth jika suhu operasi > 60°C.")
    else:
        st.write("Tidak ada rekomendasi spesifik misalignment saat ini. Lanjutkan monitoring rutin.")

# Footer
st.markdown("---")
st.caption("© 2026 PT Pertamina Patra Niaga - Infrastructure Management & Project. Built with Streamlit.")
st.caption("References: API 610, API 686, ISO 10816-3, ISO 13373-2.")
