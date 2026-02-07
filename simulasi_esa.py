import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- IMPORT MODULES (OTAK SISTEM) ---
from modules.asset_database import get_asset_list, get_asset_details
from modules.vibration_diagnostics import analyze_vibration_matrix, VibPoint
from modules.noise_diagnostics import analyze_noise_profile
from modules.temperature_diagnostics import analyze_temperature_profile
from modules.electrical_diagnostics import analyze_electrical_health
from modules.health_logic import assess_overall_health
from modules.standards import ISOZone, Limits # Pastikan file standards.py ada berisi class ISOZone & Limits

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Under Construction by Alkap Corp.",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INIT SESSION STATE (Agar data tidak hilang saat pindah tab) ---
if 'mech_result' not in st.session_state: st.session_state.mech_result = None
if 'elec_result' not in st.session_state: st.session_state.elec_result = None
if 'health_result' not in st.session_state: st.session_state.health_result = None

# --- FUNGSI BANTUAN ---
def save_to_history(tag, type_chk, max_val, status, diagnosa, details):
    """Simpan data ke CSV (Simulasi Database)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    diag_str = " | ".join(diagnosa)
    # Di real world, ini connect ke SQL Database
    # st.toast(f"Data {type_chk} untuk {tag} berhasil disimpan!", icon="✅")
    return True

# ==============================================================================
# 1. SIDEBAR (NAVIGASI & ASET)
# ==============================================================================
with st.sidebar:
    st.title("🏭 Reliability Pro")
    st.caption("Industrial Elmot & Pump Diagnostic")
    st.divider()

    # A. SELECTOR AKTIVITAS (Menentukan Limit)
    activity_type = st.radio(
        "🛠️ Jenis Aktivitas:",
        ["Inspeksi Rutin (Routine)", "Commissioning (New/Overhaul)"],
        index=0
    )
    
    # Set Limit berdasarkan Aktivitas
    is_commissioning = "Commissioning" in activity_type
    limit_status = "STRICT (API 686)" if is_commissioning else "STANDARD (ISO 10816)"
    st.caption(f"Mode Limit: {limit_status}")

    st.divider()

    # B. SELECTOR ASET (Dari Database)
    asset_list = get_asset_list()
    selected_tag = st.selectbox("📌 Pilih Aset (Tag No):", asset_list)
    asset = get_asset_details(selected_tag)

    # C. INFO KARTU ASET
    st.info(f"""
    **{asset.name}**
    📍 {asset.area}
    
    ⚙️ **Mechanical:**
    • {asset.power_kw} kW | {asset.rpm} RPM
    • Mounting: {asset.mounting}
    
    ⚡ **Electrical:**
    • {asset.volt_rated} V | {asset.fla_rated} A
    """)

    st.divider()
    st.markdown("Developed for **Maintenance Team**")

# ==============================================================================
# 2. MAIN CONTENT
# ==============================================================================
st.title(f"Under Construction by Alkap Corp.: {asset.tag}")
st.markdown(f"**Status Operasi:** {activity_type} | **Acuan Standar:** ISO 10816, ISO 18436, API 610, NEMA MG-1")

# TAB LAYOUT
tab1, tab2, tab3 = st.tabs(["⚙️ MEKANIKAL & FISIK", "⚡ ELEKTRIKAL", "🏥 KESIMPULAN KESEHATAN"])

# ==============================================================================
# TAB 1: MEKANIKAL (VIBRASI, SUHU, NOISE, FISIK)
# ==============================================================================
with tab1:
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("1. Input Data Lapangan")
        
        with st.form("mech_form"):
            # --- A. VIBRASI (4 TITIK x 3 ARAH) ---
            st.markdown("#### 🌊 Vibrasi (mm/s RMS) & Suhu (°C)")
            c1, c2 = st.columns(2)
            
            with c1: # MOTOR
                st.markdown("**MOTOR (Driver)**")
                m_de_h = st.number_input("M-DE Horiz", 0.0, 50.0, 0.5, step=0.1)
                m_de_v = st.number_input("M-DE Vert", 0.0, 50.0, 0.5, step=0.1)
                m_de_a = st.number_input("M-DE Axial", 0.0, 50.0, 0.5, step=0.1)
                t_m_de = st.number_input("Temp M-DE (°C)", 0.0, 150.0, 60.0, step=1.0)
                st.markdown("---")
                m_nde_h = st.number_input("M-NDE Horiz", 0.0, 50.0, 0.5, step=0.1)
                m_nde_v = st.number_input("M-NDE Vert", 0.0, 50.0, 0.5, step=0.1)
                m_nde_a = st.number_input("M-NDE Axial", 0.0, 50.0, 0.5, step=0.1)
                t_m_nde = st.number_input("Temp M-NDE (°C)", 0.0, 150.0, 55.0, step=1.0)

            with c2: # POMPA
                st.markdown("**POMPA (Driven)**")
                p_de_h = st.number_input("P-DE Horiz", 0.0, 50.0, 0.5, step=0.1)
                p_de_v = st.number_input("P-DE Vert", 0.0, 50.0, 0.5, step=0.1)
                p_de_a = st.number_input("P-DE Axial", 0.0, 50.0, 0.5, step=0.1)
                t_p_de = st.number_input("Temp P-DE (°C)", 0.0, 150.0, 60.0, step=1.0)
                st.markdown("---")
                p_nde_h = st.number_input("P-NDE Horiz", 0.0, 50.0, 0.5, step=0.1)
                p_nde_v = st.number_input("P-NDE Vert", 0.0, 50.0, 0.5, step=0.1)
                p_nde_a = st.number_input("P-NDE Axial", 0.0, 50.0, 0.5, step=0.1)
                t_p_nde = st.number_input("Temp P-NDE (°C)", 0.0, 150.0, 55.0, step=1.0)

            # --- B. NOISE INSPECTION ---
            st.markdown("#### 🔊 Inspeksi Kebisingan (Noise)")
            with st.expander("Buka Checklist Noise", expanded=False):
                cn1, cn2 = st.columns(2)
                with cn1:
                    noise_type = st.selectbox("Karakter Suara:", 
                        ["Normal (Humming)", "Suara Kerikil (Kavitasi)", "Ngorok (Bearing)", 
                         "Mencicit (Lube)", "Gesekan Logam (Rubbing)", "Gemuruh (Flow)", 
                         "Desis Keras (High Flow)", "Klotak-klotak (Loose)"])
                with cn2:
                    noise_loc = st.selectbox("Lokasi Suara:", ["-", "Motor DE", "Motor NDE", "Pump DE", "Pump NDE", "Casing", "Piping"])
                
                valve_test = st.radio("Tes Valve Discharge:", ["Tidak Dilakukan", "Suara Stabil", "Suara Berubah Drastis (Recirculation)"], horizontal=True)

            # --- C. PHYSICAL INSPECTION (IMAGE CONDITIONS) ---
            st.markdown("#### 👀 Inspeksi Fisik (Condition Checklist)")
            st.caption("Referensi: Lembar Checklist Conditions (Good/Fair/Bad)")
            
            with st.expander("Buka Checklist Kondisi Fisik", expanded=True):
                # Checkbox logika sesuai gambar screenshot user
                st.markdown("**Temuan Kerusakan:**")
                
                # Baris 1: Minor Issues
                chk_minor_part = st.checkbox("⚠️ Some Minor Parts Missing (Baut kecil hilang, dll)")
                chk_minor_weld = st.checkbox("⚠️ Apparent Weld Repairs Required (Retak halus)")
                
                # Baris 2: Major Issues
                chk_major_part = st.checkbox("⛔ MAJOR Parts Missing (Komponen utama hilang)")
                chk_major_weld = st.checkbox("⛔ MAJOR Weld Repairs Required (Retak struktur)")
                chk_cost = st.checkbox("⛔ Not Cost Effective to Repair (Rusak Total)")
                
                # Logic Fisik
                physical_issues = []
                if chk_minor_part: physical_issues.append("Minor Parts Missing")
                if chk_minor_weld: physical_issues.append("Minor Weld Repairs Required")
                if chk_major_part: physical_issues.append("MAJOR Parts Missing")
                if chk_major_weld: physical_issues.append("MAJOR Weld Repairs Required")
                if chk_cost: physical_issues.append("NOT COST EFFECTIVE TO REPAIR")

            submit_mech = st.form_submit_button("🔍 ANALISA MEKANIKAL")

    # --- LOGIKA ANALISA MEKANIKAL ---
    if submit_mech:
        # 1. Gather Data Object
        readings = [
            VibPoint("Motor DE", "Horizontal", m_de_h), VibPoint("Motor DE", "Vertical", m_de_v), VibPoint("Motor DE", "Axial", m_de_a),
            VibPoint("Motor NDE", "Horizontal", m_nde_h), VibPoint("Motor NDE", "Vertical", m_nde_v), VibPoint("Motor NDE", "Axial", m_nde_a),
            VibPoint("Pump DE", "Horizontal", p_de_h), VibPoint("Pump DE", "Vertical", p_de_v), VibPoint("Pump DE", "Axial", p_de_a),
            VibPoint("Pump NDE", "Horizontal", p_nde_h), VibPoint("Pump NDE", "Vertical", p_nde_v), VibPoint("Pump NDE", "Axial", p_nde_a),
        ]
        temps = {"Motor DE": t_m_de, "Motor NDE": t_m_nde, "Pump DE": t_p_de, "Pump NDE": t_p_nde}
        
        # 2. Tentukan Limit (Commissioning vs Routine)
        limit_vib = 3.0 if is_commissioning else asset.vib_limit_warning # Strict vs Standard
        
        # 3. Panggil Modules
        vib_causes = analyze_vibration_matrix(readings, limit_vib)
        noise_causes = analyze_noise_profile(noise_type, noise_loc, valve_test)
        
        # Cek axial high untuk diagnosa temperatur
        is_axial_high = any(r.val > limit_vib and r.axis == "Axial" and "DE" in r.loc for r in readings)
        temp_causes = analyze_temperature_profile(temps, asset.max_temp_bearing, noise_type, is_axial_high)

        # 4. Hitung Max Vib & ISO Zone
        max_vib_val = max([r.val for r in readings])
        
        # Penentuan Zone (Simplified logic for display)
        if max_vib_val < 2.8: iso_zone_desc = ISOZone.A.value
        elif max_vib_val < 7.1: iso_zone_desc = ISOZone.B.value if not is_commissioning else "ZONE C (Commissioning Fail)"
        else: iso_zone_desc = ISOZone.D.value

        # 5. Simpan ke Session State
        st.session_state.mech_result = {
            "max_vib": max_vib_val,
            "zone": iso_zone_desc,
            "causes": vib_causes + noise_causes + temp_causes,
            "temps": temps,
            "physical": physical_issues
        }

    # --- TAMPILAN HASIL MEKANIKAL ---
    with col_result:
        st.subheader("📊 Hasil Diagnosa")
        if st.session_state.mech_result:
            res = st.session_state.mech_result
            
            # Gauge Chart
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=res['max_vib'],
                title={'text': "Max Vibrasi (mm/s)"},
                gauge={
                    'axis': {'range': [0, 10]},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, 2.8], 'color': "#2ecc71"},
                        {'range': [2.8, 7.1], 'color': "#f1c40f"},
                        {'range': [7.1, 10], 'color': "#e74c3c"}
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': limit_vib}
                }
            ))
            fig.update_layout(height=250, margin=dict(t=30,b=20,l=20,r=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # Status Zone
            st.info(f"**Status ISO:** {res['zone']}")
            
            # List Diagnosa
            if res['causes']:
                st.error("🚨 **Terdeteksi Masalah:**")
                for c in res['causes']:
                    st.write(f"- {c}")
            else:
                st.success("✅ **Analisa Vibrasi & Suhu Normal**")

            # Fisik
            if res['physical']:
                st.warning(f"⚠️ **Temuan Fisik:** {', '.join(res['physical'])}")
            else:
                st.success("✅ **Kondisi Fisik Lengkap (No Missing Parts)**")

# ==============================================================================
# TAB 2: ELEKTRIKAL (ANSI/NEMA)
# ==============================================================================
with tab2:
    st.subheader("⚡ Analisa Kualitas Daya (Power Quality)")
    
    with st.form("elec_form"):
        ec1, ec2 = st.columns(2)
        with ec1:
            st.markdown(f"**Tegangan (Rated: {asset.volt_rated} V)**")
            v1 = st.number_input("Voltage R-S", value=float(asset.volt_rated))
            v2 = st.number_input("Voltage S-T", value=float(asset.volt_rated))
            v3 = st.number_input("Voltage T-R", value=float(asset.volt_rated))
        with ec2:
            st.markdown(f"**Arus (FLA: {asset.fla_rated} A)**")
            # Default load 80% biar gak kaget user
            def_load = float(asset.fla_rated) * 0.8
            i1 = st.number_input("Current R", value=def_load)
            i2 = st.number_input("Current S", value=def_load)
            i3 = st.number_input("Current T", value=def_load)
            ig = st.number_input("Ground Current (A)", 0.0, 10.0, 0.0)
        
        submit_elec = st.form_submit_button("🔍 ANALISA ELEKTRIKAL")

    if submit_elec:
        elec_causes, v_unb, i_unb = analyze_electrical_health(
            [v1, v2, v3], [i1, i2, i3], ig, asset.volt_rated, asset.fla_rated
        )
        st.session_state.elec_result = {
            "causes": elec_causes,
            "v_unb": v_unb,
            "i_unb": i_unb
        }

    if st.session_state.elec_result:
        eres = st.session_state.elec_result
        em1, em2, em3 = st.columns(3)
        em1.metric("Voltage Unbalance", f"{eres['v_unb']:.2f}%", "Max 3% (NEMA)", delta_color="inverse")
        em2.metric("Current Unbalance", f"{eres['i_unb']:.2f}%", "Max 10% (NEMA)", delta_color="inverse")
        em3.metric("Status Diagnosa", f"{len(eres['causes'])} Isu", delta_color="inverse" if eres['causes'] else "normal")
        
        if eres['causes']:
            st.error("🚨 **ANSI Code Violations:**")
            for ec in eres['causes']: st.write(f"- {ec}")
        else:
            st.success("✅ **Sistem Elektrikal Sehat (Healthy)**")

# ==============================================================================
# TAB 3: KESIMPULAN KESEHATAN (GOOD/FAIR/BAD)
# ==============================================================================
with tab3:
    st.subheader("🏥 Asset Health Index (Final Decision)")
    
    if st.button("🔄 GENERATE FINAL REPORT"):
        # Cek apakah data mekanikal & elektrikal sudah ada
        if not st.session_state.mech_result:
            st.warning("⚠️ Mohon lakukan Analisa Mekanikal (Tab 1) terlebih dahulu.")
        else:
            mech = st.session_state.mech_result
            elec = st.session_state.elec_result
            
            # Default values jika elektrikal belum dicek
            elec_status = "Normal"
            if elec and elec['causes']: elec_status = "Alarm" 
            
            # --- PANGGIL HEALTH LOGIC ---
            health_res = assess_overall_health(
                vib_zone=mech['zone'],
                elec_status=elec_status,
                temp_max=max(mech['temps'].values()),
                physical_issues=mech['physical']
            )
            
            st.session_state.health_result = health_res

    # TAMPILAN REPORT
    if st.session_state.health_result:
        hr = st.session_state.health_result
        
        # Warna Background Dinamis
        bg_color = {
            "GOOD": "#d4edda", # Hijau muda
            "FAIR": "#fff3cd", # Kuning muda
            "BAD": "#f8d7da"   # Merah muda
        }.get(hr['status'], "#ffffff")

        # KARTU UTAMA
        st.markdown(f"""
        <div style="background-color:{bg_color}; padding:20px; border-radius:10px; border: 2px solid {hr['color']}; text-align: center;">
            <h1 style="color:{hr['color']}; margin:0;">{hr['status']}</h1>
            <h3>{hr['desc']}</h3>
            <hr>
            <p style="font-size:18px;"><b>REKOMENDASI:</b><br>{hr['action']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        # DETAIL TEMUAN
        c_fail1, c_fail2 = st.columns(2)
        with c_fail1:
            st.markdown("### 📉 Faktor Penurunan Performa")
            if hr['reasons']:
                for r in hr['reasons']:
                    st.error(f"❌ {r}")
            else:
                st.success("Tidak ada faktor penurun performa signifikan.")
                
        with c_fail2:
            st.markdown("### 💾 Tindakan Selanjutnya")
            if hr['status'] == "BAD":
                st.button("🔴 BUAT WORK ORDER (WO) - URGENT")
            elif hr['status'] == "FAIR":
                st.button("🟠 TAMBAH KE WATCHLIST")
            else:
                st.button("🟢 SIMPAN LOG INSPEKSI")
