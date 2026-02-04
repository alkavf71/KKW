import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import iso_logic # Import logika yang baru kita buat

# --- DATABASE ASET (Dari Laporan Inspeksi Anda) ---
ASSETS = {
    "P-02 (FT Moutong)": {
        "tag": "0459599", "kw": 18.5, "rpm": 2900, "class": "Class II",
        "loc": "FT Moutong", "img": "rigid"
    },
    "733-P-103 (FT Luwuk)": {
        "tag": "1041535A", "kw": 30.0, "rpm": 2900, "class": "Class II",
        "loc": "FT Luwuk", "img": "rigid"
    },
    "706-P-203 (IT Makassar)": {
        "tag": "049-1611186", "kw": 15.0, "rpm": 2955, "class": "Class II",
        "loc": "IT Makassar", "img": "rigid"
    }
}

st.set_page_config(page_title="Pump Inspector Pro", layout="wide")

# --- HEADER ---
st.title("🛡️ Digital Reliability Assistant")
st.markdown("**Sistem Diagnosa Pompa Berbasis TKI C-04 (2025) & TKI C-017 (2018)**")

# --- SIDEBAR: PILIH ASET ---
with st.sidebar:
    st.header("1. Pilih Aset")
    asset_name = st.selectbox("Tag Number / Nama Pompa:", list(ASSETS.keys()))
    asset = ASSETS[asset_name]
    
    st.info(f"""
    **Info Aset:**
    \n📍 Lokasi: {asset['loc']}
    \n🏷️ Tag: {asset['tag']}
    \n⚡ Power: {asset['kw']} kW
    \n⚙️ RPM Desain: {asset['rpm']}
    """)
    st.divider()
    inspector_name = st.text_input("Nama Inspektor:", value="Inspector Reliability")

# --- FORM INPUT INSPEKSI (GRID LAYOUT) ---
st.subheader(f"📝 Input Data Inspeksi: {asset_name}")

with st.form("inspection_form"):
    # BAGIAN 1: VIBRASI (12 TITIK)
    st.markdown("### A. Pengukuran Vibrasi (Velocity mm/s RMS)")
    st.caption("Masukkan nilai dari Vibration Meter (misal: ADASH 4900). Referensi: TKI C-017 Tabel 1.")
    
    # Layout Grid: Motor di Kiri, Pompa di Kanan
    col_driver, col_driven = st.columns(2)
    
    with col_driver:
        st.markdown("#### ⚡ MOTOR (Driver)")
        c1, c2, c3 = st.columns(3)
        with c1: m_nde_h = st.number_input("NDE Horiz", 0.0, 50.0, step=0.01, key="m_nde_h")
        with c2: m_nde_v = st.number_input("NDE Vert", 0.0, 50.0, step=0.01, key="m_nde_v")
        with c3: m_nde_a = st.number_input("NDE Axial", 0.0, 50.0, step=0.01, key="m_nde_a")
        
        st.markdown("---")
        c4, c5, c6 = st.columns(3)
        with c4: m_de_h = st.number_input("DE Horiz", 0.0, 50.0, step=0.01, key="m_de_h")
        with c5: m_de_v = st.number_input("DE Vert", 0.0, 50.0, step=0.01, key="m_de_v")
        with c6: m_de_a = st.number_input("DE Axial", 0.0, 50.0, step=0.01, key="m_de_a")

    with col_driven:
        st.markdown("#### 💧 POMPA (Driven)")
        c7, c8, c9 = st.columns(3)
        with c7: p_de_h = st.number_input("DE Horiz", 0.0, 50.0, step=0.01, key="p_de_h")
        with c8: p_de_v = st.number_input("DE Vert", 0.0, 50.0, step=0.01, key="p_de_v")
        with c9: p_de_a = st.number_input("DE Axial", 0.0, 50.0, step=0.01, key="p_de_a")
        
        st.markdown("---")
        c10, c11, c12 = st.columns(3)
        with c10: p_nde_h = st.number_input("NDE Horiz", 0.0, 50.0, step=0.01, key="p_nde_h")
        with c11: p_nde_v = st.number_input("NDE Vert", 0.0, 50.0, step=0.01, key="p_nde_v")
        with c12: p_nde_a = st.number_input("NDE Axial", 0.0, 50.0, step=0.01, key="p_nde_a")

    # BAGIAN 2: PARAMETER LAIN
    st.markdown("### B. Parameter Operasi & Visual")
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        rpm_act = st.number_input("RPM Aktual:", value=asset['rpm'])
    with cp2:
        # TKI C-04 2025 limit 85C, TKI C-017 2018 limit 50C. Kita pakai 2025 tapi warning di 50.
        temp_bearing = st.number_input("Suhu Bearing Max (°C):", 0.0, 150.0, step=0.1)
    with cp3:
        noise_level = st.radio("Kebisingan (Noise):", ["Normal", "Abnormal (>85dB)"])

    st.markdown("**Checklist Visual (TKI C-06 & Laporan Lapangan):**")
    cv1, cv2, cv3, cv4 = st.columns(4)
    with cv1: chk_baut = st.checkbox("Baut Kendor")
    with cv2: chk_bocor = st.checkbox("Kebocoran (Seal/Pipa)")
    with cv3: chk_ground = st.checkbox("Grounding Rusak/Lepas")
    with cv4: chk_paint = st.checkbox("Cat/Coating Terkelupas")

    submit = st.form_submit_button("🔍 ANALISA KESEHATAN POMPA")

# --- LOGIKA DIAGNOSA SETELAH SUBMIT ---
if submit:
    st.divider()
    
    # 1. Kumpulkan Data Vibrasi
    vibs = {
        "Motor NDE H": m_nde_h, "Motor NDE V": m_nde_v, "Motor NDE A": m_nde_a,
        "Motor DE H": m_de_h, "Motor DE V": m_de_v, "Motor DE A": m_de_a,
        "Pump DE H": p_de_h, "Pump DE V": p_de_v, "Pump DE A": p_de_a,
        "Pump NDE H": p_nde_h, "Pump NDE V": p_nde_v, "Pump NDE A": p_nde_a,
    }
    
    # 2. Cari Max Value & Status ISO
    max_val = max(vibs.values())
    max_loc = max(vibs, key=vibs.get)
    iso_status, color_code = iso_logic.get_iso_status(max_val)
    
    # 3. Analisa Akar Masalah (Root Cause) - Logic TKI C-017
    # Cari semua titik yang melebihi batas Warning (2.8 mm/s) untuk didiagnosa
    problem_points = {k: v for k, v in vibs.items() if v > 2.80} 
    root_causes = iso_logic.analyze_root_cause(problem_points) if problem_points else ["Tidak ada indikasi kerusakan mekanis spesifik."]

    # --- TAMPILAN HASIL (DASHBOARD) ---
    col_res_L, col_res_R = st.columns([1, 2])
    
    with col_res_L:
        # Tampilan Gauge Meter
        st.markdown("### Status Aset")
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = max_val,
            title = {'text': f"Max Vib ({max_loc})"},
            gauge = {
                'axis': {'range': [0, 15]},
                'bar': {'color': "black"},
                'steps': [
                    {'range': [0, 1.12], 'color': "#2ecc71"}, # A
                    {'range': [1.12, 2.80], 'color': "#f1c40f"}, # B
                    {'range': [2.80, 7.10], 'color': "#e67e22"}, # C
                    {'range': [7.10, 15], 'color': "#e74c3c"} # D
                ],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': max_val}
            }
        ))
        fig.update_layout(height=250, margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        # Kotak Status
        if color_code == "success": st.success(f"**{iso_status}**")
        elif color_code == "warning": st.warning(f"**{iso_status}**")
        elif color_code == "orange": st.error(f"**{iso_status}** (Jadwalkan Perbaikan)")
        else: st.error(f"**{iso_status}** (STOP OPERASI!)")

    with col_res_R:
        st.markdown("### 🛠️ Diagnosa & Rekomendasi (AI)")
        
        # Tampilkan Diagnosa Mekanis (TKI C-017)
        if problem_points:
            st.error("Terdeteksi Pola Kerusakan (Ref: TKI C-017 Tabel 1):")
            for diagnosis in root_causes:
                st.write(f"- {diagnosis}")
        else:
            st.success("Vibrasi dalam batas normal. Tidak ada pola kerusakan terdeteksi.")

        # Diagnosa Parameter Lain
        issues = []
        if temp_bearing > 85:
            issues.append(f"🔥 **OVERHEAT!** Suhu {temp_bearing}°C melebihi batas TKI C-04 (85°C).")
        elif temp_bearing > 50:
            issues.append(f"⚠️ **Warning Suhu:** {temp_bearing}°C melebihi batas konservatif TKI C-017 (50°C). Pantau pelumasan.")
            
        if noise_level == "Abnormal (>85dB)":
            issues.append("🔊 **Noise Tinggi:** Cek kavitasi atau bearing (Ref: TKI C-017).")
            
        rpm_dev = abs(asset['rpm'] - rpm_act)
        if rpm_dev > (asset['rpm'] * 0.05): # Toleransi 5%
            issues.append(f"⚙️ **RPM Slip:** Deviasi {rpm_dev} RPM dari desain.")

        # Visual Issues
        if chk_baut: issues.append("🔧 **Baut Kendor:** Lakukan pengencangan (Torque).")
        if chk_bocor: issues.append("💧 **Kebocoran:** Cek Seal/Gasket.")
        if chk_paint: issues.append("🎨 **Coating:** Jadwalkan pengecatan ulang (Ref: Laporan Inspeksi).")
        if chk_ground: issues.append("⚡ **Grounding:** Perbaiki kabel grounding.")

        if issues:
            st.markdown("**Temuan Tambahan:**")
            for i in issues:
                st.write(f"- {i}")
        
        # REKOMENDASI FINAL
        st.divider()
        if iso_status in ["UNSATISFACTORY", "UNACCEPTABLE"] or temp_bearing > 85:
            st.error("REKOMENDASI: Buat Work Order (WO) Prioritas Tinggi. Panggil Teknisi.")
        elif iso_status == "SATISFACTORY" or issues:
            st.warning("REKOMENDASI: Monitor ketat & Lakukan maintenance ringan (Cleaning/Greasing).")
        else:
            st.success("REKOMENDASI: Lanjut Operasi Normal.")

    # TABLE RAW DATA
    with st.expander("Lihat Data Mentah Input"):
        st.json(vibs)
