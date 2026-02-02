import streamlit as st
import pandas as pd

# ==============================================================================
# 1. KONFIGURASI HALAMAN & STYLE INDUSTRI
# ==============================================================================
st.set_page_config(
    page_title="Total Reliability Management System",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan Dashboard Profesional
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    div.stButton > button:first-child { background-color: #004d99; color: white; height: 3em; font-weight: bold; }
    .stMetric { background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #004d99; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #003366; }
    .report-card { background-color: white; padding: 20px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. SIDEBAR: KONFIGURASI ASET & STANDAR (MASTER DATA)
# ==============================================================================
st.sidebar.title("🏭 Asset Configuration")
st.sidebar.markdown("---")

# A. Identitas Aset
asset_tag = st.sidebar.text_input("Asset Tag No.", value="P-201-A", help="Contoh: P-101-A")
inspector = st.sidebar.text_input("Inspector Name", value="Engineer OJT")

# B. Pemilihan Standar (The Brain)
st.sidebar.header("1. Standard Reference")
standard_selected = st.sidebar.selectbox(
    "Vibration Standard:",
    ("API 610 (Critical Pumps)", "ISO 10816-3 (General Utility)", "Custom Limit")
)

# Logic Limit Vibrasi
if "API 610" in standard_selected:
    limit_vib_warn = 2.5
    limit_vib_crit = 3.0
    st.sidebar.info(f"Ref: API 610\nLimit: {limit_vib_crit} mm/s")
elif "ISO 10816" in standard_selected:
    iso_class = st.sidebar.radio("Machine Class:", ("Group 1 (>300kW)", "Group 2 (<300kW)"))
    found_type = st.sidebar.radio("Foundation:", ("Rigid", "Flexible"))
    
    if "Group 2" in iso_class:
        limit_vib_crit = 4.5 if found_type == "Rigid" else 7.1
    else:
        limit_vib_crit = 7.1 if found_type == "Rigid" else 11.0
    limit_vib_warn = limit_vib_crit * 0.7
    st.sidebar.success(f"Ref: ISO 10816\nLimit: {limit_vib_crit} mm/s")
else:
    limit_vib_crit = st.sidebar.number_input("Manual Limit (mm/s)", 1.0, 20.0, 5.0)
    limit_vib_warn = limit_vib_crit * 0.8

# C. Logic Limit Electrical (NEMA)
st.sidebar.header("2. Electrical Standard")
nema_ref = "NEMA MG-1"
limit_amp_unbal = 10.0 # NEMA max allowed
st.sidebar.warning(f"Ref: {nema_ref}\nMax Unbalance: 10%")

# ==============================================================================
# 3. INPUT DATA (ORGANIZED BY TABS)
# ==============================================================================
st.title(f"🛠️ Reliability Assessment: {asset_tag}")
st.markdown("**PT Pertamina Patra Niaga - Infrastructure Management & Project**")

tab1, tab2, tab3 = st.tabs(["⚙️ MECHANICAL (Vib/Temp)", "⚡ ELECTRICAL (Motor)", "🌊 PROCESS (Flow/NPSH)"])

with tab1:
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        vib_ode = st.number_input("Vib. Outboard (mm/s)", 0.0, 50.0, 1.2, step=0.1)
        vib_ide = st.number_input("Vib. Inboard (mm/s)", 0.0, 50.0, 1.1, step=0.1)
    with col_m2:
        temp_bearing = st.number_input("Bearing Temp (°C)", 0.0, 150.0, 45.0, step=1.0)
        noise_level = st.number_input("Audible Noise (dB)", 0.0, 130.0, 75.0, step=1.0)
    with col_m3:
        # Fitur Spectrum sederhana (User input dominasi frekuensi)
        dom_freq = st.selectbox("Dominant Frequency (Spectrum):", 
                                ("1x RPM (Unbalance)", "2x RPM (Misalignment)", "High Freq (Bearing)", "None/Normal"))
        loose_bolt = st.checkbox("Check: Baut Pondasi Kendur?", value=False)

with tab2:
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        amp_r = st.number_input("Ampere Phase R", 0.0, 1000.0, 100.0)
        amp_s = st.number_input("Ampere Phase S", 0.0, 1000.0, 100.0)
        amp_t = st.number_input("Ampere Phase T", 0.0, 1000.0, 100.0)
    with col_e2:
        # Kalkulasi Unbalance Otomatis
        avg_amp = (amp_r + amp_s + amp_t) / 3
        if avg_amp > 0:
            max_dev = max(abs(amp_r - avg_amp), abs(amp_s - avg_amp), abs(amp_t - avg_amp))
            current_unbal = (max_dev / avg_amp) * 100
        else:
            current_unbal = 0.0
        
        st.metric("Calculated Unbalance", f"{current_unbal:.2f}%", f"Limit: {limit_amp_unbal}%")
        rotor_bar_check = st.checkbox("Check: Pulsing Sound / Hunting?", help="Indikasi Broken Rotor Bar")

with tab3:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        suction_press = st.number_input("Suction Pressure (BarG)", -1.0, 20.0, 1.0, step=0.1)
        discharge_press = st.number_input("Discharge Pressure (BarG)", 0.0, 50.0, 5.0, step=0.1)
    with col_p2:
        fluid_temp = st.number_input("Fluid Temperature (°C)", 0.0, 100.0, 30.0)
        npsh_r = st.number_input("NPSH Required (m)", 0.0, 10.0, 2.0, help="Lihat Nameplate")
        
    # NPSH Calculator Backend (Simplified for Pertamax/Solar)
    vp_est = 0.6 if fluid_temp > 40 else 0.3 # Estimasi kasar Vapor Pressure Head (m)
    atm_head = 10.33
    suction_head = suction_press * 10.2 # Konversi bar ke meter air
    npsh_a = atm_head + suction_head - vp_est
    npsh_margin = npsh_a - npsh_r

# ==============================================================================
# 4. SUPER ENGINE (DIAGNOSTIC LOGIC)
# ==============================================================================
if st.button("🚀 RUN SUPER DIAGNOSTICS", type="primary", use_container_width=True):
    st.markdown("---")
    st.header("📊 Executive Summary")
    
    findings = []
    
    # --- LOGIC 1: MECHANICAL FAULTS ---
    max_vib = max(vib_ode, vib_ide)
    
    # 1.1 Unbalance (ISO 10816 / API)
    if max_vib > limit_vib_warn:
        severity = "HIGH" if max_vib > limit_vib_crit else "MODERATE"
        if "1x RPM" in dom_freq:
             findings.append({
                "mode": "MECHANICAL", "issue": "ROTOR UNBALANCE", "severity": severity,
                "desc": f"Vibrasi dominan di 1x RPM ({max_vib} mm/s).",
                "rec": "Lakukan Balancing Rotor (Field Balancing atau Workshop)."
            })
        elif "2x RPM" in dom_freq or temp_bearing > 80:
             findings.append({
                "mode": "MECHANICAL", "issue": "MISALIGNMENT", "severity": severity,
                "desc": f"Vibrasi tinggi disertai panas ({temp_bearing}°C) atau 2x RPM.",
                "rec": "Cek Laser Alignment Coupling & Soft Foot Correction."
            })
        else:
             findings.append({
                "mode": "MECHANICAL", "issue": "GENERAL VIBRATION", "severity": severity,
                "desc": "Vibrasi di atas limit standar tanpa pola frekuensi jelas.",
                "rec": "Cek kekencangan baut pondasi & struktur."
            })

    # 1.2 Bearing Fault (High Freq + Noise)
    if "High Freq" in dom_freq or noise_level > 90:
        findings.append({
            "mode": "MECHANICAL", "issue": "BEARING DEFECT", "severity": "HIGH",
            "desc": f"Terdeteksi High Freq spectrum / Noise tinggi ({noise_level} dB).",
            "rec": "Greasing ulang segera. Jika tidak turun, ganti bearing."
        })
        
    # 1.3 Soft Foot (Baut Kendur)
    if loose_bolt:
        findings.append({
            "mode": "MECHANICAL", "issue": "SOFT FOOT / LOOSENESS", "severity": "CRITICAL",
            "desc": "Baut pondasi dilaporkan kendur saat inspeksi.",
            "rec": "Lakukan pengencangan torsi (Torquing) sesuai standar."
        })

    # --- LOGIC 2: ELECTRICAL FAULTS (NEMA) ---
    # 2.1 Broken Rotor Bar
    if rotor_bar_check or (current_unbal < 5.0 and max_vib > limit_vib_warn and "1x RPM" in dom_freq):
        # Logika: Jika teknisi dengar suara pulsing (hunting)
        findings.append({
            "mode": "ELECTRICAL", "issue": "BROKEN ROTOR BAR", "severity": "HIGH",
            "desc": "Indikasi suara pulsing/hunting pada motor.",
            "rec": "Lakukan Motor Current Signature Analysis (MCSA) untuk verifikasi."
        })
    
    # 2.2 Stator/Winding Fault
    if current_unbal > limit_amp_unbal:
        findings.append({
            "mode": "ELECTRICAL", "issue": "ELECTRICAL UNBALANCE / STATOR FAULT", "severity": "CRITICAL",
            "desc": f"Current Unbalance {current_unbal:.1f}% melebihi limit NEMA (10%).",
            "rec": "Stop Motor. Cek tahanan isolasi (Megger) & koneksi terminal."
        })

    # --- LOGIC 3: PROCESS FAULTS (API/HI) ---
    # 3.1 Cavitation
    if (npsh_margin < 1.0) or (noise_level > 85 and suction_press < 0.5):
        findings.append({
            "mode": "PROCESS", "issue": "PUMP CAVITATION", "severity": "CRITICAL",
            "desc": f"NPSH Margin tipis ({npsh_margin:.2f} m) & Noise tinggi.",
            "rec": "Cek Strainer Suction (buntu?), Naikan level tangki, atau cek breather valve."
        })
        
    # 3.2 Dead Head (Katup Tutup)
    if discharge_press > 10.0 and noise_level > 85: # Asumsi 10 bar pressure tinggi
         findings.append({
            "mode": "PROCESS", "issue": "DEAD HEAD OPERATION", "severity": "CRITICAL",
            "desc": "Tekanan discharge sangat tinggi abnormal.",
            "rec": "Cek jalur discharge, pastikan tidak ada valve tertutup saat pompa jalan."
        })

    # ==============================================================================
    # 5. HASIL OUTPUT (DASHBOARD)
    # ==============================================================================
    
    # KPI Metrics
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Max Vibration", f"{max_vib} mm/s", delta="OK" if max_vib < limit_vib_warn else "High", delta_color="inverse")
    kpi2.metric("Current Unbalance", f"{current_unbal:.1f} %", delta="OK" if current_unbal < limit_amp_unbal else "High", delta_color="inverse")
    kpi3.metric("NPSH Margin", f"{npsh_margin:.2f} m", delta="OK" if npsh_margin > 1.0 else "Low", delta_color="normal")
    kpi4.metric("Total Issues", f"{len(findings)} Found", delta_color="off")

    st.subheader("📋 Detailed Diagnostic Report")
    
    if not findings:
        st.success("✅ **HEALTHY ASSET**: Tidak ditemukan indikasi kerusakan signifikan. Lanjutkan monitoring rutin.")
    else:
        for f in findings:
            # Styling Card berdasarkan Severity
            border_color = "#ff4b4b" if f['severity'] == "CRITICAL" else "#ffa500"
            icon = "⛔" if f['severity'] == "CRITICAL" else "⚠️"
            
            with st.container():
                st.markdown(f"""
                <div style="border-left: 5px solid {border_color}; padding: 10px; background-color: white; margin-bottom: 10px; border-radius: 5px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
                    <h4 style="margin:0;">{icon} {f['issue']} ({f['mode']})</h4>
                    <p style="margin:5px 0;"><b>Analisis:</b> {f['desc']}</p>
                    <p style="margin:5px 0; color: #004d99;"><b>🛠️ Action: {f['rec']}</b></p>
                </div>
                """, unsafe_allow_html=True)

    # Disclaimer Standar
    st.caption(f"Diagnosis based on standards: {standard_selected}, NEMA MG-1, & API 610/HI 1.3")
