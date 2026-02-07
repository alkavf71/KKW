import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# IMPORT MODUL (Sesuai nama file)
from modules.asset_database import get_asset_list, get_asset_details
from modules.standards import ISOZone
from modules.vibration_diagnostics import analyze_vibration_matrix, VibPoint
from modules.noise_diagnostics import analyze_noise_profile
from modules.temperature_diagnostics import analyze_temperature_profile
from modules.electrical_diagnostics import analyze_electrical_health
from modules.health_logic import assess_overall_health

st.set_page_config(page_title="Reliability Pro", layout="wide")

if 'mech_result' not in st.session_state: st.session_state.mech_result = None
if 'elec_result' not in st.session_state: st.session_state.elec_result = None
if 'health_result' not in st.session_state: st.session_state.health_result = None

# SIDEBAR
with st.sidebar:
    st.title("🏭 Reliability Pro")
    activity_type = st.radio("Aktivitas:", ["Inspeksi Rutin", "Commissioning"])
    is_comm = "Commissioning" in activity_type
    
    tag = st.selectbox("Pilih Aset:", get_asset_list())
    asset = get_asset_details(tag)
    st.info(f"**{asset.name}**\n\n{asset.power_kw}kW | {asset.rpm}RPM\n{asset.volt_rated}V | {asset.fla_rated}A")

st.title(f"Diagnosa: {asset.tag}")
tab1, tab2, tab3 = st.tabs(["⚙️ MEKANIKAL", "⚡ ELEKTRIKAL", "🏥 KESIMPULAN"])

# TAB 1
with tab1:
    col1, col2 = st.columns([1.2, 1])
    with col1:
        with st.form("mech"):
            st.subheader("1. Vibrasi & Suhu")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**MOTOR**")
                m_de_h = st.number_input("M-DE H", value=0.5)
                m_de_v = st.number_input("M-DE V", value=0.5)
                m_de_a = st.number_input("M-DE A", value=0.5)
                t_m_de = st.number_input("Temp M-DE", value=60.0)
                st.divider()
                m_nde_h = st.number_input("M-NDE H", value=0.5)
                m_nde_v = st.number_input("M-NDE V", value=0.5)
                m_nde_a = st.number_input("M-NDE A", value=0.5)
                t_m_nde = st.number_input("Temp M-NDE", value=55.0)
            with c2:
                st.markdown("**POMPA**")
                p_de_h = st.number_input("P-DE H", value=0.5)
                p_de_v = st.number_input("P-DE V", value=0.5)
                p_de_a = st.number_input("P-DE A", value=0.5)
                t_p_de = st.number_input("Temp P-DE", value=60.0)
                st.divider()
                p_nde_h = st.number_input("P-NDE H", value=0.5)
                p_nde_v = st.number_input("P-NDE V", value=0.5)
                p_nde_a = st.number_input("P-NDE A", value=0.5)
                t_p_nde = st.number_input("Temp P-NDE", value=55.0)

            st.subheader("2. Fisik & Noise")
            with st.expander("Checklist Detail", expanded=True):
                noise = st.selectbox("Noise:", ["Normal (Humming)", "Suara Kerikil/Letupan (Popping)", "Ngorok/Kasar (Growling)", "Mencicit (Squealing)", "Gemuruh (Rumbling)"])
                loc = st.selectbox("Lokasi:", ["-", "Motor DE", "Motor NDE", "Pump DE", "Pump NDE", "Casing"])
                v_test = st.radio("Valve Test:", ["Tidak Dilakukan", "Suara Stabil", "Suara Berubah Drastis (Recirculation)"], horizontal=True)
                
                st.markdown("**Fisik:**")
                chk_seal = st.checkbox("Major: Seal Bocor")
                chk_guard = st.checkbox("Major: Guard Hilang")
                chk_baut = st.checkbox("Minor: Baut Kendor")
                chk_oli = st.checkbox("Minor: Oli Low/Dirty")
                chk_cost = st.checkbox("Critical: Not Cost Effective")

            submit = st.form_submit_button("ANALISA MEKANIKAL")

    if submit:
        readings = [
            VibPoint("Motor DE", "Horizontal", m_de_h), VibPoint("Motor DE", "Vertical", m_de_v), VibPoint("Motor DE", "Axial", m_de_a),
            VibPoint("Motor NDE", "Horizontal", m_nde_h), VibPoint("Motor NDE", "Vertical", m_nde_v), VibPoint("Motor NDE", "Axial", m_nde_a),
            VibPoint("Pump DE", "Horizontal", p_de_h), VibPoint("Pump DE", "Vertical", p_de_v), VibPoint("Pump DE", "Axial", p_de_a),
            VibPoint("Pump NDE", "Horizontal", p_nde_h), VibPoint("Pump NDE", "Vertical", p_nde_v), VibPoint("Pump NDE", "Axial", p_nde_a)
        ]
        temps = {"Motor DE": t_m_de, "Motor NDE": t_m_nde, "Pump DE": t_p_de, "Pump NDE": t_p_nde}
        
        limit = 3.0 if is_comm else asset.vib_limit_warning
        
        vib_c = analyze_vibration_matrix(readings, limit)
        noise_c = analyze_noise_profile(noise, loc, v_test)
        is_axial = any(r.value > limit and r.axis == "Axial" and "DE" in r.location for r in readings)
        temp_c = analyze_temperature_profile(temps, asset.max_temp_bearing, noise, is_axial)
        
        max_v = max(r.value for r in readings)
        if max_v < 2.8: z = ISOZone.A.value
        elif max_v < 7.1: z = ISOZone.B.value
        else: z = ISOZone.D.value

        phys = []
        if chk_seal: phys.append("MAJOR: Seal Bocor")
        if chk_guard: phys.append("MAJOR: Guard Hilang")
        if chk_baut: phys.append("MINOR: Baut Kendor")
        if chk_oli: phys.append("MINOR: Oli Kotor")
        if chk_cost: phys.append("CRITICAL: Not Cost Effective")

        st.session_state.mech_result = {"max": max_v, "zone": z, "causes": vib_c+noise_c+temp_c, "temps": temps, "phys": phys}

    with col2:
        if st.session_state.mech_result:
            res = st.session_state.mech_result
            fig = go.Figure(go.Indicator(mode="gauge+number", value=res['max'], title={'text':"Vib (mm/s)"}, gauge={'axis':{'range':[0,10]}, 'bar':{'color':'black'}, 'steps':[{'range':[0,2.8], 'color':'#2ecc71'}, {'range':[2.8,7.1], 'color':'#f1c40f'}, {'range':[7.1,10], 'color':'#e74c3c'}]}))
            fig.update_layout(height=250, margin=dict(t=30,b=20,l=20,r=20))
            st.plotly_chart(fig, use_container_width=True)
            st.info(res['zone'])
            if res['causes']: 
                for c in res['causes']: st.error(c)
            if res['phys']:
                for p in res['phys']: st.warning(p)

# TAB 2
with tab2:
    with st.form("elec"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Volt ({asset.volt_rated}V)**")
            v1 = st.number_input("R-S", value=asset.volt_rated)
            v2 = st.number_input("S-T", value=asset.volt_rated)
            v3 = st.number_input("T-R", value=asset.volt_rated)
        with c2:
            st.markdown(f"**Ampere ({asset.fla_rated}A)**")
            i1 = st.number_input("R", value=asset.fla_rated*0.8)
            i2 = st.number_input("S", value=asset.fla_rated*0.8)
            i3 = st.number_input("T", value=asset.fla_rated*0.8)
            ig = st.number_input("G", 0.0)
        sub_elec = st.form_submit_button("ANALISA ELEKTRIKAL")
    
    if sub_elec:
        ec, vu, iu = analyze_electrical_health([v1,v2,v3], [i1,i2,i3], ig, asset.volt_rated, asset.fla_rated)
        st.session_state.elec_result = {"causes": ec, "vu": vu, "iu": iu}
    
    if st.session_state.elec_result:
        res = st.session_state.elec_result
        c1, c2, c3 = st.columns(3)
        c1.metric("Volt Unb", f"{res['vu']:.1f}%")
        c2.metric("Curr Unb", f"{res['iu']:.1f}%")
        c3.metric("Status", "FAULT" if res['causes'] else "OK")
        if res['causes']: 
            for c in res['causes']: st.error(c)

# TAB 3
with tab3:
    if st.button("GENERATE REPORT"):
        if st.session_state.mech_result:
            mech = st.session_state.mech_result
            elec = st.session_state.elec_result
            e_stat = "TRIP" if (elec and elec['causes']) else "Normal"
            health = assess_overall_health(mech['zone'], e_stat, max(mech['temps'].values()), mech['phys'])
            st.session_state.health_result = health
            
    if st.session_state.health_result:
        hr = st.session_state.health_result
        st.markdown(f"<div style='background:{'#d4edda' if hr['status']=='GOOD' else '#f8d7da'};padding:20px;border-radius:10px;text-align:center;'><h1 style='color:{hr['color']}'>{hr['status']}</h1><h3>{hr['desc']}</h3><hr>{hr['action']}</div>", unsafe_allow_html=True)
        if hr['reasons']:
            st.error("FAKTOR PENYEBAB:")
            for r in hr['reasons']: st.write(f"❌ {r}")
