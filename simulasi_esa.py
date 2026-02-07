import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- IMPORT MODULES ---
# Pastikan folder 'modules' ada dan berisi file-file yang sudah kita buat
from modules.asset_database import get_asset_list, get_asset_details
from modules.standards import ISOZone
from modules.vibration_diagnostics import analyze_vibration_matrix, VibPoint
from modules.noise_diagnostics import analyze_noise_profile
from modules.temperature_diagnostics import analyze_temperature_profile
from modules.electrical_diagnostics import analyze_electrical_health
from modules.health_logic import assess_overall_health

# --- PAGE CONFIG ---
st.set_page_config(page_title="Reliability Pro - Report Mode", layout="wide")

# --- SESSION STATE INIT ---
if 'mech_result' not in st.session_state: st.session_state.mech_result = None
if 'elec_result' not in st.session_state: st.session_state.elec_result = None
if 'health_result' not in st.session_state: st.session_state.health_result = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 Reliability Pro")
    st.caption("Standard: Average per Axis (DE+NDE)/2")
    
    activity_type = st.radio("Jenis Aktivitas:", ["Inspeksi Rutin", "Commissioning"])
    is_comm = "Commissioning" in activity_type
    
    st.divider()
    tag = st.selectbox("Pilih Aset (Tag No):", get_asset_list())
    asset = get_asset_details(tag)
    
    st.info(f"**{asset.name}**\n\nArea: {asset.area}\nPower: {asset.power_kw} kW\nRPM: {asset.rpm}")

# --- MAIN CONTENT ---
st.title(f"Diagnosa Aset: {asset.tag}")
st.write(f"Limit Referensi: **{asset.vib_limit_warning} mm/s**")

tab1, tab2, tab3 = st.tabs(["⚙️ MEKANIKAL (REPORT)", "⚡ ELEKTRIKAL", "🏥 KESIMPULAN"])

# ==============================================================================
# TAB 1: MEKANIKAL (LOGIC REPORT TABLE)
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
                m_de_h = st.number_input("M-DE Horiz", value=5.46)
                m_de_v = st.number_input("M-DE Vert", value=2.48)
                m_de_a = st.number_input("M-DE Axial", value=9.31)
                # PERBAIKAN: Label dibedakan (Motor)
                t_m_de = st.number_input("Temp Motor DE (°C)", value=40.0) 
            with c1b:
                st.caption("Titik NDE")
                m_nde_h = st.number_input("M-NDE Horiz", value=4.41)
                m_nde_v = st.number_input("M-NDE Vert", value=6.89)
                m_nde_a = st.number_input("M-NDE Axial", value=8.11)
                # PERBAIKAN: Label dibedakan (Motor)
                t_m_nde = st.number_input("Temp Motor NDE (°C)", value=40.0)

            st.markdown("#### DRIVEN (Pompa)")
            c2a, c2b = st.columns(2)
            with c2a:
                st.caption("Titik DE")
                p_de_h = st.number_input("P-DE Horiz", value=1.62)
                p_de_v = st.number_input("P-DE Vert", value=6.70)
                p_de_a = st.number_input("P-DE Axial", value=2.05)
                # PERBAIKAN: Label dibedakan (Pompa)
                t_p_de = st.number_input("Temp Pompa DE (°C)", value=36.0)
            with c2b:
                st.caption("Titik NDE")
                p_nde_h = st.number_input("P-NDE Horiz", value=1.23)
                p_nde_v = st.number_input("P-NDE Vert", value=4.00)
                p_nde_a = st.number_input("P-NDE Axial", value=5.22)
                # PERBAIKAN: Label dibedakan (Pompa)
                t_p_nde = st.number_input("Temp Pompa NDE (°C)", value=40.0)

            st.divider()
            st.markdown("**Inspeksi Fisik & Noise:**")
            noise = st.selectbox("Noise:", ["Normal", "Kavitasi", "Bearing Defect", "Recirculation"])
            loc = st.selectbox("Lokasi:", ["-", "Motor DE", "Motor NDE", "Pump DE", "Pump NDE", "Casing"])
            v_test = st.radio("Valve Test:", ["Tidak Dilakukan", "Stabil", "Berubah Drastis"], horizontal=True)
            
            chk_seal = st.checkbox("MAJOR: Seal Bocor")
            chk_guard = st.checkbox("MAJOR: Guard Hilang")
            chk_baut = st.checkbox("MINOR: Baut Kendor")
            
            # Tombol Submit ada di dalam Form (Indentation benar)
            submit_mech = st.form_submit_button("🔍 GENERATE TABEL LAPORAN")

    # --- LOGIKA PEMBUATAN TABEL LAPORAN ---
    if submit_mech:
        # 1. Tentukan Limit
        limit = 3.0 if is_comm else asset.vib_limit_warning
        limit_trip = 7.1 
        
        # 2. Fungsi Helper Remark
        def get_remark(val, lim_warn, lim_trip):
            if val < lim_warn: return ISOZone.B.value 
            elif val < lim_trip: return ISOZone.C.value 
            else: return ISOZone.D.value 

        # 3. Hitung Rata-rata PER SUMBU (DE + NDE) / 2
        avr_m_h = (m_de_h + m_nde_h) / 2
        avr_m_v = (m_de_v + m_nde_v) / 2
        avr_m_a = (m_de_a + m_nde_a) / 2
        
        avr_p_h = (p_de_h + p_nde_h) / 2
        avr_p_v = (p_de_v + p_nde_v) / 2
        avr_p_a = (p_de_a + p_nde_a) / 2

        # 4. Buat DataFrame
        data = [
            ["Driver", "H", m_de_h, m_nde_h, avr_m_h, limit, get_remark(avr_m_h, limit, limit_trip)],
            ["Driver", "V", m_de_v, m_nde_v, avr_m_v, limit, get_remark(avr_m_v, limit, limit_trip)],
            ["Driver", "A", m_de_a, m_nde_a, avr_m_a, limit, get_remark(avr_m_a, limit, limit_trip)],
            ["Driven", "H", p_de_h, p_nde_h, avr_p_h, limit, get_remark(avr_p_h, limit, limit_trip)],
            ["Driven", "V", p_de_v, p_nde_v, avr_p_v, limit, get_remark(avr_p_v, limit, limit_trip)],
            ["Driven", "A", p_de_a, p_nde_a, avr_p_a, limit, get_remark(avr_p_a, limit, limit_trip)],
        ]
        
        df_report = pd.DataFrame(data, columns=["Unit", "Axis", "DE", "NDE", "Avr", "Limit", "Remark"])
        
        # 5. Diagnosa Teknis
        readings = [
            VibPoint("Motor DE", "Horizontal", m_de_h), VibPoint("Motor DE", "Vertical", m_de_v), VibPoint("Motor DE", "Axial", m_de_a),
            VibPoint("Motor NDE", "Horizontal", m_nde_h), VibPoint("Motor NDE", "Vertical", m_nde_v), VibPoint("Motor NDE", "Axial", m_nde_a),
            VibPoint("Pump DE", "Horizontal", p_de_h), VibPoint("Pump DE", "Vertical", p_de_v), VibPoint("Pump DE", "Axial", p_de_a),
            VibPoint("Pump NDE", "Horizontal", p_nde_h), VibPoint("Pump NDE", "Vertical", p_nde_v), VibPoint("Pump NDE", "Axial", p_nde_a)
        ]
        vib_causes = analyze_vibration_matrix(readings, limit)
        
        # 6. Simpan Hasil
        max_avr = max(avr_m_h, avr_m_v, avr_m_a, avr_p_h, avr_p_v, avr_p_a)
        
        status_global = ISOZone.B.value
        if any("Short-term" in x for x in df_report['Remark']): status_global = ISOZone.C.value
        if any("damage" in x for x in df_report['Remark']): status_global = ISOZone.D.value
        
        color_global = "#2ecc71"
        if "Short-term" in status_global: color_global = "#f1c40f"
        if "damage" in status_global: color_global = "#e74c3c"

        temps = {"Motor": max(t_m_de, t_m_nde), "Pump": max(t_p_de, t_p_nde)}
        phys_list = []
        if chk_seal: phys_list.append("MAJOR: Seal Bocor")
        if chk_guard: phys_list.append("MAJOR: Guard Hilang")
        if chk_baut: phys_list.append("MINOR: Baut Kendor")

        st.session_state.mech_result = {
            "df": df_report,
            "max_val": max_avr,
            "status": status_global,
            "color": color_global,
            "causes": vib_causes,
            "phys": phys_list,
            "temps": temps
        }

    # --- TAMPILAN OUTPUT (TABEL) ---
    with col2:
        if st.session_state.mech_result:
            res = st.session_state.mech_result
            
            st.subheader("📋 Tabel Laporan Vibrasi")
            
            def highlight_row(row):
                if "damage" in row['Remark']: return ['background-color: #ffcccc']*len(row)
                elif "Short-term" in row['Remark']: return ['background-color: #fff3cd']*len(row)
                else: return ['background-color: #d4edda']*len(row)

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
                    st.error("Diagnosa Teknis:")
                    for c in res['causes']: st.write(f"• {c}")
                if res['phys']:
                    st.warning("Temuan Fisik: " + ", ".join(res['phys']))

# ==============================================================================
# TAB 2: ELEKTRIKAL (Code Diringkas)
# ==============================================================================
with tab2:
    with st.form("elec_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Voltase ({asset.volt_rated}V)**")
            v1 = st.number_input("R-S", value=asset.volt_rated)
            v2 = st.number_input("S-T", value=asset.volt_rated)
            v3 = st.number_input("T-R", value=asset.volt_rated)
        with c2:
            st.markdown(f"**Ampere ({asset.fla_rated}A)**")
            i1 = st.number_input("R", value=asset.fla_rated*0.8)
            i2 = st.number_input("S", value=asset.fla_rated*0.8)
            i3 = st.number_input("T", value=asset.fla_rated*0.8)
            ig = st.number_input("G", 0.0)
        submit_elec = st.form_submit_button("ANALISA ELEKTRIKAL")

    if submit_elec:
        causes, vu, iu = analyze_electrical_health([v1,v2,v3], [i1,i2,i3], ig, asset.volt_rated, asset.fla_rated)
        st.session_state.elec_result = {"causes": causes, "vu": vu, "iu": iu}

    if st.session_state.elec_result:
        res = st.session_state.elec_result
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Volt Unbalance", f"{res['vu']:.2f}%", "Max 3%")
        col_m2.metric("Curr Unbalance", f"{res['iu']:.2f}%", "Max 10%")
        col_m3.metric("Status", "FAULT" if res['causes'] else "OK")
        if res['causes']:
            for c in res['causes']: st.error(c)

# ==============================================================================
# TAB 3: KESIMPULAN
# ==============================================================================
with tab3:
    if st.button("GENERATE FINAL REPORT"):
        if st.session_state.mech_result:
            res = st.session_state.mech_result
            phys = res.get('phys', [])
            
            health = assess_overall_health(res['status'], "Normal", max(res['temps'].values()), phys)
            
            st.markdown(f"""
            <div style="background-color:{'#d4edda' if health['status']=='GOOD' else '#f8d7da'}; padding:20px; border-radius:10px; border:2px solid {health['color']}; text-align:center;">
                <h1 style="color:{health['color']}; margin:0;">{health['status']}</h1>
                <h3>{health['desc']}</h3>
                <hr>
                <b>REKOMENDASI:</b><br>{health['action']}
            </div>
            """, unsafe_allow_html=True)
