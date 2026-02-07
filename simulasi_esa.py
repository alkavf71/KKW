import streamlit as st
import plotly.graph_objects as go
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
st.set_page_config(page_title="Reliability Pro - AVR Logic", layout="wide")

# --- SESSION STATE INIT ---
if 'mech_result' not in st.session_state: st.session_state.mech_result = None
if 'elec_result' not in st.session_state: st.session_state.elec_result = None
if 'health_result' not in st.session_state: st.session_state.health_result = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 Reliability Pro")
    st.caption("Standard: AVR Calculation & ISO 10816")
    
    activity_type = st.radio("Jenis Aktivitas:", ["Inspeksi Rutin", "Commissioning"])
    is_comm = "Commissioning" in activity_type
    
    st.divider()
    tag = st.selectbox("Pilih Aset (Tag No):", get_asset_list())
    asset = get_asset_details(tag)
    
    st.info(f"**{asset.name}**\n\nArea: {asset.area}\nPower: {asset.power_kw} kW\nRPM: {asset.rpm}")

# --- MAIN CONTENT ---
st.title(f"Diagnosa Aset: {asset.tag}")
st.write(f"Limit Referensi: **{asset.vib_limit_warning} mm/s (AVR)**")

tab1, tab2, tab3 = st.tabs(["⚙️ MEKANIKAL (AVR)", "⚡ ELEKTRIKAL", "🏥 KESIMPULAN"])

# ==============================================================================
# TAB 1: MEKANIKAL (LOGIC AVR)
# ==============================================================================
with tab1:
    col1, col2 = st.columns([1.2, 1])
    
    # --- FORM INPUT ---
    with col1:
        with st.form("mech_form"):
            st.subheader("1. Input Data Vibrasi (mm/s RMS)")
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("#### MOTOR (Driver)")
                m_de_h = st.number_input("M-DE Horiz", value=0.5)
                m_de_v = st.number_input("M-DE Vert", value=0.5)
                m_de_a = st.number_input("M-DE Axial", value=0.5)
                t_m_de = st.number_input("Suhu M-DE (°C)", value=60.0)
                st.markdown("---")
                m_nde_h = st.number_input("M-NDE Horiz", value=0.5)
                m_nde_v = st.number_input("M-NDE Vert", value=0.5)
                m_nde_a = st.number_input("M-NDE Axial", value=0.5)
                t_m_nde = st.number_input("Suhu M-NDE (°C)", value=55.0)

            with c2:
                st.markdown("#### POMPA (Driven)")
                p_de_h = st.number_input("P-DE Horiz", value=0.5)
                p_de_v = st.number_input("P-DE Vert", value=0.5)
                p_de_a = st.number_input("P-DE Axial", value=0.5)
                t_p_de = st.number_input("Suhu P-DE (°C)", value=60.0)
                st.markdown("---")
                p_nde_h = st.number_input("P-NDE Horiz", value=0.5)
                p_nde_v = st.number_input("P-NDE Vert", value=0.5)
                p_nde_a = st.number_input("P-NDE Axial", value=0.5)
                t_p_nde = st.number_input("Suhu P-NDE (°C)", value=55.0)

            st.subheader("2. Inspeksi Fisik & Noise")
            with st.expander("📝 Checklist Lapangan", expanded=True):
                # Noise
                noise = st.selectbox("Karakter Suara:", ["Normal (Humming)", "Suara Kerikil (Kavitasi)", "Ngorok (Bearing)", "Mencicit (Kurang Grease)", "Gemuruh (Flow)"])
                loc = st.selectbox("Lokasi Suara:", ["-", "Motor DE", "Motor NDE", "Pump DE", "Pump NDE", "Casing"])
                v_test = st.radio("Valve Test:", ["Tidak Dilakukan", "Suara Stabil", "Suara Berubah Drastis (Recirculation)"], horizontal=True)
                
                st.divider()
                # Fisik Detail (Untuk Laporan)
                st.markdown("**Temuan Fisik:**")
                chk_seal = st.checkbox("MAJOR: Seal Bocor / Rembes")
                chk_guard = st.checkbox("MAJOR: Guard Hilang (Unsafe)")
                chk_baut = st.checkbox("MINOR: Baut Kendor/Hilang")
                chk_oli = st.checkbox("MINOR: Level Oli Rendah/Kotor")
                chk_cost = st.checkbox("CRITICAL: Kerusakan Parah (Not Cost Effective)")

            submit_mech = st.form_submit_button("🔍 HITUNG AVR & DIAGNOSA")

    # --- LOGIKA AVR & DIAGNOSA ---
    if submit_mech:
        # 1. Kumpulkan Data Raw
        readings = [
            VibPoint("Motor DE", "Horizontal", m_de_h), VibPoint("Motor DE", "Vertical", m_de_v), VibPoint("Motor DE", "Axial", m_de_a),
            VibPoint("Motor NDE", "Horizontal", m_nde_h), VibPoint("Motor NDE", "Vertical", m_nde_v), VibPoint("Motor NDE", "Axial", m_nde_a),
            VibPoint("Pump DE", "Horizontal", p_de_h), VibPoint("Pump DE", "Vertical", p_de_v), VibPoint("Pump DE", "Axial", p_de_a),
            VibPoint("Pump NDE", "Horizontal", p_nde_h), VibPoint("Pump NDE", "Vertical", p_nde_v), VibPoint("Pump NDE", "Axial", p_nde_a)
        ]
        temps = {"Motor DE": t_m_de, "Motor NDE": t_m_nde, "Pump DE": t_p_de, "Pump NDE": t_p_nde}

        # 2. HITUNG RATA-RATA (AVR) PER TITIK
        def calc_avr(point_name):
            vals = [r.value for r in readings if point_name in r.location]
            return sum(vals) / len(vals) if vals else 0.0

        avr_m_de = calc_avr("Motor DE")
        avr_m_nde = calc_avr("Motor NDE")
        avr_p_de = calc_avr("Pump DE")
        avr_p_nde = calc_avr("Pump NDE")

        # Nilai Final untuk Penentuan Status adalah AVR Tertinggi
        final_avr_val = max(avr_m_de, avr_m_nde, avr_p_de, avr_p_nde)

        # 3. Tentukan STATUS ISO (Berdasarkan AVR vs Limit Aset)
        limit_val = 3.0 if is_comm else asset.vib_limit_warning
        
        # Logic Klasifikasi ISO 10816
        if final_avr_val <= limit_val:
            # Kondisi Bagus (Di bawah limit)
            if final_avr_val < (limit_val * 0.5):
                iso_status = ISOZone.A.value # New condition
                gauge_color = "#2ecc71" # Hijau Tua
            else:
                iso_status = ISOZone.B.value # Unlimited operation
                gauge_color = "#a3e048" # Hijau Muda
        elif final_avr_val <= (limit_val * 1.5):
            # Kondisi Warning
            iso_status = ISOZone.C.value # Short term operation
            gauge_color = "#f1c40f" # Kuning
        else:
            # Kondisi Rusak
            iso_status = ISOZone.D.value # Vibration causes damage
            gauge_color = "#e74c3c" # Merah

        # 4. Diagnosa Penyebab (Tetap pakai raw data H/V/A untuk tahu jenis kerusakannya)
        vib_causes = analyze_vibration_matrix(readings, limit_val)
        noise_causes = analyze_noise_profile(noise, loc, v_test)
        is_axial_high = any(r.value > limit_val and r.axis == "Axial" and "DE" in r.location for r in readings)
        temp_causes = analyze_temperature_profile(temps, asset.max_temp_bearing, noise, is_axial_high)

        # 5. List Temuan Fisik
        phys_list = []
        if chk_seal: phys_list.append("MAJOR: Seal Bocor")
        if chk_guard: phys_list.append("MAJOR: Guard Hilang")
        if chk_baut: phys_list.append("MINOR: Baut Kendor")
        if chk_oli: phys_list.append("MINOR: Oli Kotor")
        if chk_cost: phys_list.append("CRITICAL: Not Cost Effective")

        # 6. Simpan Hasil
        st.session_state.mech_result = {
            "val": final_avr_val, # Nilai AVR
            "zone": iso_status,
            "color": gauge_color,
            "causes": vib_causes + noise_causes + temp_causes,
            "phys": phys_list,
            "temps": temps
        }

    # --- TAMPILAN HASIL (OUTPUT) ---
    with col2:
        if st.session_state.mech_result:
            res = st.session_state.mech_result
            
            # Gauge Meter (Menampilkan AVR)
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=res['val'],
                title={'text': "AVR Vibrasi (mm/s)"},
                gauge={
                    'axis': {'range': [0, 10]},
                    'bar': {'color': "black"},
                    'steps': [{'range': [0, 10], 'color': res['color']}]
                }
            ))
            fig.update_layout(height=250, margin=dict(t=30,b=20,l=20,r=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # Status Text
            st.info(f"**STATUS: {res['zone']}**")
            
            # Penyebab Teknis
            if res['causes']:
                st.error("🚨 **INDIKASI PENYEBAB:**")
                for c in res['causes']: st.write(f"- {c}")
            else:
                st.success("✅ Tidak ada indikasi kerusakan mekanis.")
            
            # Fisik
            if res['phys']:
                st.warning("⚠️ **TEMUAN FISIK:**")
                for p in res['phys']: st.write(f"- {p}")

# ==============================================================================
# TAB 2: ELEKTRIKAL
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
            i1 = st.number_input("Phase R", value=asset.fla_rated*0.8)
            i2 = st.number_input("Phase S", value=asset.fla_rated*0.8)
            i3 = st.number_input("Phase T", value=asset.fla_rated*0.8)
            ig = st.number_input("Ground (A)", value=0.0)
        submit_elec = st.form_submit_button("🔍 ANALISA ELEKTRIKAL")

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
# TAB 3: KESIMPULAN FINAL
# ==============================================================================
with tab3:
    if st.button("🔄 GENERATE FINAL REPORT"):
        if st.session_state.mech_result:
            mech = st.session_state.mech_result
            elec = st.session_state.elec_result
            
            # Logic Final Decision
            elec_status = "TRIP" if (elec and elec['causes']) else "Normal"
            health = assess_overall_health(mech['zone'], elec_status, max(mech['temps'].values()), mech['phys'])
            st.session_state.health_result = health
        else:
            st.warning("⚠️ Harap jalankan Analisa Mekanikal (Tab 1) dulu.")

    if st.session_state.health_result:
        hr = st.session_state.health_result
        st.markdown(f"""
        <div style="background-color:{'#d4edda' if hr['status']=='GOOD' else '#f8d7da'}; padding:20px; border-radius:10px; border:2px solid {hr['color']}; text-align:center;">
            <h1 style="color:{hr['color']}; margin:0;">{hr['status']}</h1>
            <h3>{hr['desc']}</h3>
            <hr>
            <b>REKOMENDASI:</b><br>{hr['action']}
        </div>
        """, unsafe_allow_html=True)
        
        if hr['reasons']:
            st.write("")
            st.error("**FAKTOR PENYEBAB:**")
            for r in hr['reasons']: st.write(f"❌ {r}")
