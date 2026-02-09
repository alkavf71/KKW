import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- IMPORT MODULES ---
from modules.asset_database import get_asset_list, get_asset_details
# MODULE BARU KITA:
from modules.vibration_diagnostics import VibrationAnalyzer 
# MODULE LAIN (PASTIKAN FILE NYA ADA):
from modules.standards import ISOZone 
from modules.electrical_diagnostics import analyze_electrical_health
from modules.health_logic import assess_overall_health

# --- PAGE CONFIG ---
st.set_page_config(page_title="Reliability Pro - ISO 20816", layout="wide")

# --- SESSION STATE INIT ---
if 'mech_result' not in st.session_state: st.session_state.mech_result = None
if 'elec_result' not in st.session_state: st.session_state.elec_result = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 Reliability Pro")
    st.caption("Standards: ISO 20816, API 610, IEC 60034")
    
    activity_type = st.radio("Jenis Aktivitas:", ["Inspeksi Rutin", "Commissioning"])
    is_comm = "Commissioning" in activity_type
    
    st.divider()
    tag = st.selectbox("Pilih Aset (Tag No):", get_asset_list())
    asset = get_asset_details(tag)
    
    st.info(f"**{asset.name}**\n\nArea: {asset.area}\nPower: {asset.power_kw} kW\nRPM: {asset.rpm}")

# --- MAIN CONTENT ---
st.title(f"Diagnosa Aset: {asset.tag}")
st.write(f"Limit Referensi Vibrasi: **{asset.vib_limit_warning} mm/s**")

tab1, tab2, tab3, tab4 = st.tabs(["⚙️ MEKANIKAL", "⚡ ELEKTRIKAL", "🏥 KESIMPULAN", "🌊 HYDRAULIC"])

# ==============================================================================
# TAB 1: MEKANIKAL (CLEAN CODE VERSION)
# ==============================================================================
with tab1:
    col1, col2 = st.columns([1, 1.5]) 
    
    # --- FORM INPUT ---
    with col1:
        with st.form("mech_form"):
            st.subheader("Input Data Vibrasi (mm/s)")
            
            st.markdown("#### DRIVER (Motor)")
            c1a, c1b = st.columns(2)
            with c1a:
                st.caption("Titik DE")
                m_de_h = st.number_input("M-DE Horiz", value=0.87) 
                m_de_v = st.number_input("M-DE Vert", value=0.22)
                m_de_a = st.number_input("M-DE Axial", value=0.52)
                t_m_de = st.number_input("Temp Motor DE (°C)", value=35.0) 
            with c1b:
                st.caption("Titik NDE")
                m_nde_h = st.number_input("M-NDE Horiz", value=1.55)
                m_nde_v = st.number_input("M-NDE Vert", value=1.04)
                m_nde_a = st.number_input("M-NDE Axial", value=1.38)
                t_m_nde = st.number_input("Temp Motor NDE (°C)", value=33.0)

            st.markdown("#### DRIVEN (Pompa)")
            c2a, c2b = st.columns(2)
            with c2a:
                st.caption("Titik DE")
                p_de_h = st.number_input("P-DE Horiz", value=1.67)
                p_de_v = st.number_input("P-DE Vert", value=1.54)
                p_de_a = st.number_input("P-DE Axial", value=1.22)
                t_p_de = st.number_input("Temp Pompa DE (°C)", value=33.0)
            with c2b:
                st.caption("Titik NDE")
                p_nde_h = st.number_input("P-NDE Horiz", value=0.95)
                p_nde_v = st.number_input("P-NDE Vert", value=0.57)
                p_nde_a = st.number_input("P-NDE Axial", value=0.83)
                t_p_nde = st.number_input("Temp Pompa NDE (°C)", value=30.0)

            st.divider()
            # Input Fisik & Noise
            noise = st.selectbox("Noise:", ["Normal", "Kavitasi", "Bearing Defect", "Recirculation"])
            chk_seal = st.checkbox("MAJOR: Seal Bocor")
            chk_guard = st.checkbox("MAJOR: Guard Hilang")
            chk_baut = st.checkbox("MINOR: Baut Kendor")
            
            submit_mech = st.form_submit_button("🔍 GENERATE TABEL LAPORAN")

    # --- LOGIKA MEMANGGIL MODULE (SANGAT BERSIH!) ---
    if submit_mech:
        # 1. Siapkan Data Input dalam Dictionary
        inputs = {
            'm_de_h': m_de_h, 'm_de_v': m_de_v, 'm_de_a': m_de_a,
            'm_nde_h': m_nde_h, 'm_nde_v': m_nde_v, 'm_nde_a': m_nde_a,
            'p_de_h': p_de_h, 'p_de_v': p_de_v, 'p_de_a': p_de_a,
            'p_nde_h': p_nde_h, 'p_nde_v': p_nde_v, 'p_nde_a': p_nde_a
        }
        
        # 2. Inisialisasi Analyzer dari Module Baru
        limit_val = 4.50 if is_comm else asset.vib_limit_warning
        analyzer = VibrationAnalyzer(limit_warn=limit_val, limit_trip=7.1)
        
        # 3. Minta Module untuk Menganalisa & Membuat Laporan
        vib_result = analyzer.generate_full_report(inputs)

        # 4. Simpan ke Session State (Ditambah data fisik/suhu yg tidak masuk modul vib)
        temps = {"Motor": max(t_m_de, t_m_nde), "Pump": max(t_p_de, t_p_nde)}
        phys_list = []
        if chk_seal: phys_list.append("MAJOR: Seal Bocor")
        if chk_guard: phys_list.append("MAJOR: Guard Hilang")
        if chk_baut: phys_list.append("MINOR: Baut Kendor")
        
        st.session_state.mech_result = {
            "df": vib_result['dataframe'],
            "max_val": vib_result['max_value'],
            "status": vib_result['global_status'],
            "color": vib_result['global_color'],
            "causes": vib_result['causes'],
            "phys": phys_list,
            "temps": temps
        }

    # --- TAMPILAN OUTPUT (TABEL) ---
    with col2:
        if st.session_state.mech_result:
            res = st.session_state.mech_result
            
            st.subheader("📋 Tabel Laporan Vibrasi")
            
# Styling Tabel (Warna Soft Pastel - Anti Silau)
            def highlight_row(row):
                if "ZONE D" in row['Remark']: 
                    # Merah Muda Pucat (Soft Red) - Untuk Bahaya
                    return ['background-color: #ffebee; color: #b71c1c']*len(row) 
                elif "ZONE C" in row['Remark']: 
                    # Krem/Kuning Mentega (Soft Yellow) - Untuk Warning
                    return ['background-color: #fffde7; color: #f57f17']*len(row) 
                elif "ZONE A" in row['Remark']: 
                    # Hijau Mint Sangat Muda (Soft Green) - Untuk New Machine
                    return ['background-color: #e8f5e9; color: #1b5e20; font-weight: bold']*len(row) 
                else: 
                    # Putih Bersih - Untuk Normal (Zone B)
                    return ['background-color: #ffffff; color: #212529']*len(row)

            st.dataframe(
                res['df'].style.apply(highlight_row, axis=1).format({"DE": "{:.2f}", "NDE": "{:.2f}", "Avr": "{:.2f}", "Limit": "{:.2f}"}), 
                use_container_width=True, 
                hide_index=True
            )
            
            c_g1, c_g2 = st.columns([1, 2])
            with c_g1:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=res['max_val'],
                    title={'text': "Max Avr"},
                    gauge={'axis': {'range': [0, 10]}, 'bar': {'color': "black"}, 'steps': [{'range': [0, 10], 'color': res['color']}]}
                ))
                fig.update_layout(height=180, margin=dict(t=30,b=20,l=20,r=20))
                st.plotly_chart(fig, use_container_width=True)
            
            with c_g2:
                st.info(f"**STATUS UNIT: {res['status']}**")
                
                if res['causes']:
                    st.error("🚨 **DIAGNOSA PENYEBAB (Vibrasi):**")
                    for c in res['causes']: st.write(f"• {c}")
                else:
                    st.success("✅ Pola vibrasi Normal (Tidak ada diagnosa spesifik).")
                    
                if res['phys']:
                    st.warning("⚠️ Temuan Fisik: " + ", ".join(res['phys']))

# ==============================================================================
# TAB 2: ELEKTRIKAL (Copy Paste Kode Lama Anda Di Sini)
# ==============================================================================
with tab2:
    # ... (Gunakan kode Tab 2 dari file sebelumnya yang sudah berjalan normal)
    st.info("Fitur Elektrikal (Gunakan kode sebelumnya)")
    # Agar tidak terlalu panjang di sini, silakan paste kode Tab 2 dari main.py sebelumnya.

# ==============================================================================
# TAB 3: KESIMPULAN (FINAL VERSION)
# ==============================================================================
with tab3:
    if st.button("GENERATE FINAL REPORT"):
        if st.session_state.mech_result:
            mech = st.session_state.mech_result
            # Logic Kesimpulan sama seperti sebelumnya
            # ... (Paste logic Tab 3 Anda di sini)
            st.success("Laporan Siap! (Silakan paste logic Tab 3 dari kode sebelumnya)")
        else:
            st.warning("Jalankan Mekanikal Dulu.")

# ==============================================================================
# TAB 4: HYDRAULIC (Logic API 610)
# ==============================================================================
with tab4:
    # ... (Paste kode Tab 4 Hydraulic dari kode sebelumnya)
    st.info("Fitur Hydraulic (Gunakan kode sebelumnya)")
