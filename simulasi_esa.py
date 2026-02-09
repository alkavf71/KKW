import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- IMPORT MODULES ---
from modules.asset_database import get_asset_list, get_asset_details
from modules.standards import ISOZone
from modules.vibration_diagnostics import analyze_vibration_matrix, VibPoint
from modules.noise_diagnostics import analyze_noise_profile
from modules.temperature_diagnostics import analyze_temperature_profile
from modules.electrical_diagnostics import analyze_electrical_health
from modules.health_logic import assess_overall_health

# --- PAGE CONFIG ---
st.set_page_config(page_title="Reliability Pro - Full Suite", layout="wide")

# --- SESSION STATE INIT ---
if 'mech_result' not in st.session_state: st.session_state.mech_result = None
if 'elec_result' not in st.session_state: st.session_state.elec_result = None
if 'health_result' not in st.session_state: st.session_state.health_result = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 Reliability Pro")
    st.caption("Standards: ISO 20816, IEC 60034, API 610")
    
    activity_type = st.radio("Jenis Aktivitas:", ["Inspeksi Rutin", "Commissioning"])
    is_comm = "Commissioning" in activity_type
    
    st.divider()
    tag = st.selectbox("Pilih Aset (Tag No):", get_asset_list())
    asset = get_asset_details(tag)
    
    st.info(f"**{asset.name}**\n\nArea: {asset.area}\nPower: {asset.power_kw} kW\nRPM: {asset.rpm}")

# --- MAIN CONTENT ---
st.title(f"Diagnosa Aset: {asset.tag}")
st.write(f"Limit Referensi Vibrasi: **{asset.vib_limit_warning} mm/s**")

# --- DEFINISI TAB (INI YANG TADI ERROR, SEKARANG SUDAH ADA 4) ---
tab1, tab2, tab3, tab4 = st.tabs(["⚙️ MEKANIKAL", "⚡ ELEKTRIKAL", "🏥 KESIMPULAN", "🌊 HYDRAULIC"])

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
            st.markdown("**Inspeksi Fisik & Noise:**")
            noise = st.selectbox("Noise:", ["Normal", "Kavitasi", "Bearing Defect", "Recirculation"])
            loc = st.selectbox("Lokasi:", ["-", "Motor DE", "Motor NDE", "Pump DE", "Pump NDE", "Casing"])
            v_test = st.radio("Valve Test:", ["Tidak Dilakukan", "Stabil", "Berubah Drastis"], horizontal=True)
            
            chk_seal = st.checkbox("MAJOR: Seal Bocor")
            chk_guard = st.checkbox("MAJOR: Guard Hilang")
            chk_baut = st.checkbox("MINOR: Baut Kendor")
            
            submit_mech = st.form_submit_button("🔍 GENERATE TABEL LAPORAN")

    # --- LOGIKA PEMBUATAN TABEL LAPORAN ---
    if submit_mech:
        # 1. Tentukan Limit
        limit_warn = 4.50 if is_comm else asset.vib_limit_warning
        limit_trip = 7.10
        limit_zone_a = 2.30 if limit_warn >= 4.0 else 1.40
        
        # 2. Fungsi Helper Remark
        def get_remark(val):
            if val < limit_zone_a: return ISOZone.A.value 
            elif val < limit_warn: return ISOZone.B.value 
            elif val < limit_trip: return ISOZone.C.value 
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
            ["Driver", "H", m_de_h, m_nde_h, avr_m_h, limit_warn, get_remark(avr_m_h)],
            ["Driver", "V", m_de_v, m_nde_v, avr_m_v, limit_warn, get_remark(avr_m_v)],
            ["Driver", "A", m_de_a, m_nde_a, avr_m_a, limit_warn, get_remark(avr_m_a)],
            ["Driven", "H", p_de_h, p_nde_h, avr_p_h, limit_warn, get_remark(avr_p_h)],
            ["Driven", "V", p_de_v, p_nde_v, avr_p_v, limit_warn, get_remark(avr_p_v)],
            ["Driven", "A", p_de_a, p_nde_a, avr_p_a, limit_warn, get_remark(avr_p_a)],
        ]
        
        df_report = pd.DataFrame(data, columns=["Unit", "Axis", "DE", "NDE", "Avr", "Limit", "Remark"])
        
        # 5. DIAGNOSA TEKNIS
        readings = [
            VibPoint("Motor DE", "Horizontal", m_de_h), VibPoint("Motor DE", "Vertical", m_de_v), VibPoint("Motor DE", "Axial", m_de_a),
            VibPoint("Motor NDE", "Horizontal", m_nde_h), VibPoint("Motor NDE", "Vertical", m_nde_v), VibPoint("Motor NDE", "Axial", m_nde_a),
            VibPoint("Pump DE", "Horizontal", p_de_h), VibPoint("Pump DE", "Vertical", p_de_v), VibPoint("Pump DE", "Axial", p_de_a),
            VibPoint("Pump NDE", "Horizontal", p_nde_h), VibPoint("Pump NDE", "Vertical", p_nde_v), VibPoint("Pump NDE", "Axial", p_nde_a)
        ]
        
        vib_causes = analyze_vibration_matrix(readings, limit_warn)
        noise_causes = analyze_noise_profile(noise, loc, v_test)
        
        # Diagnosa Suhu
        temp_inputs = {"Motor DE": t_m_de, "Motor NDE": t_m_nde, "Pump DE": t_p_de, "Pump NDE": t_p_nde}
        is_axial_high = (avr_m_a > limit_warn) or (avr_p_a > limit_warn)
        temp_causes = analyze_temperature_profile(temp_inputs, 85.0, noise, is_axial_high)
        
        final_causes = vib_causes + noise_causes + temp_causes
        
        # 6. Simpan Hasil
        max_avr = max(avr_m_h, avr_m_v, avr_m_a, avr_p_h, avr_p_v, avr_p_a)
        
        status_global = ISOZone.B.value
        if any("New machine" in x for x in df_report['Remark']): status_global = ISOZone.A.value 
        if any("Short-term" in x for x in df_report['Remark']): status_global = ISOZone.C.value
        if any("damage" in x for x in df_report['Remark']): status_global = ISOZone.D.value
        
        color_global = "#a3e048"
        if "New machine" in status_global: color_global = "#2ecc71"
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
            "causes": final_causes,
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
                elif "New machine" in row['Remark']: return ['background-color: #d4edda; font-weight: bold']*len(row)
                else: return ['background-color: #e2e3e5']*len(row)

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
                    st.error("🚨 **DIAGNOSA PENYEBAB:**")
                    for c in res['causes']: st.write(f"• {c}")
                else:
                    st.success("✅ Tidak ada indikasi kerusakan teknis.")
                    
                if res['phys']:
                    st.warning("⚠️ Temuan Fisik: " + ", ".join(res['phys']))

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
# TAB 3: KESIMPULAN (FINAL FIXED)
# ==============================================================================
with tab3:
    if st.button("GENERATE FINAL REPORT"):
        if st.session_state.mech_result:
            mech = st.session_state.mech_result
            elec = st.session_state.elec_result
            
            # Ambil Data Mekanikal
            phys = mech.get('phys', [])
            mech_causes = mech.get('causes', [])
            temps_val = max(mech['temps'].values()) if mech.get('temps') else 0.0
            
            # Ambil Data Elektrikal
            elec_causes = elec.get('causes', []) if elec else []
            elec_status_str = "TRIP" if elec_causes else "Normal"
            
            # Gabungkan Diagnosa
            all_tech_diagnoses = mech_causes + elec_causes
            
            # Panggil Logic Otak
            health = assess_overall_health(
                mech['status'],
                elec_status_str,
                temps_val,
                phys,
                all_tech_diagnoses
            )
            
            # Tampilan
            st.markdown(f"""
            <div style="background-color:{'#d4edda' if 'GOOD' in health['status'] else '#f8d7da'}; padding:20px; border-radius:10px; border:3px solid {health['color']}; text-align:center; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);">
                <h2 style="color:{health['color']}; margin:0; font-weight:900;">{health['status']}</h2>
                <h4 style="margin-top:5px;">{health['desc']}</h4>
                <hr style="border-top: 1px solid {health['color']};">
                <h3 style="margin-bottom:5px;">KEPUTUSAN:</h3>
                <p style="font-size:18px; font-weight:bold;">{health['action']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c_rep1, c_rep2 = st.columns(2)
            
            with c_rep1:
                st.write("")
                st.error("### 🔍 AKAR MASALAH (Root Cause)")
                if health['reasons']:
                    for r in health['reasons']:
                        st.write(f"❌ {r}")
                else:
                    st.success("Tidak ditemukan masalah signifikan.")

            with c_rep2:
                st.write("")
                st.warning("### 🛠️ REKOMENDASI PERBAIKAN")
                if health['recommendations']:
                    for rec in health['recommendations']:
                        st.write(f"🔧 {rec}")
                else:
                    st.write("• Lanjutkan maintenance rutin.")

            st.markdown("---")
            st.caption("📚 **STANDAR REFERENSI YANG DIGUNAKAN DALAM ANALISA INI:**")
            
            if health['standards']:
                std_html = ""
                for std in health['standards']:
                    std_html += f"<span style='background-color:#e2e6ea; padding:5px 10px; border-radius:15px; margin-right:5px; font-size:12px; display:inline-block; border:1px solid #ccc;'>📘 {std}</span>"
                st.markdown(std_html, unsafe_allow_html=True)
            else:
                st.caption("ISO 10816-3 (Default)")
                
        else:
            st.warning("⚠️ Harap jalankan Analisa Mekanikal (Tab 1) dulu sebelum Generate Report.")

# ==============================================================================
# TAB 4: HYDRAULIC PERFORMANCE (API 610 / ISO 9906)
# ==============================================================================
with tab4:
    st.header("🌊 Hydraulic Performance Monitoring")
    st.caption("Evaluasi kesehatan internal pompa (Impeller/Wear Ring) berdasarkan tekanan.")

    col_h1, col_h2 = st.columns([1, 1.5])

    with col_h1:
        with st.form("hydro_form"):
            st.subheader("Input Data Operasi")
            
            st.markdown("##### 1. Pressure Gauge Reading")
            p_suction = st.number_input("Suction Pressure (Bar_g)", value=0.5, help="Tekanan sisi hisap (Inlet)")
            p_discharge = st.number_input("Discharge Pressure (Bar_g)", value=4.5, help="Tekanan sisi buang (Outlet)")
            
            st.markdown("##### 2. Properties Fluida")
            sg_fluid = st.number_input("Specific Gravity (SG)", value=0.74, min_value=0.1, max_value=2.0, help="Pertamax ~0.74, Solar ~0.84, Air=1.0")
            
            st.markdown("##### 3. Data Desain")
            design_head = st.number_input("Rated Head (meter)", value=60.0, help="Lihat di Nameplate pompa (H).")
            
            submit_hydro = st.form_submit_button("🔍 ANALISA PERFORMA HYDRAULIC")

    if submit_hydro:
        # Rumus: Head = (P_out - P_in) * 10.197 / SG
        diff_press = p_discharge - p_suction
        actual_head = (diff_press * 10.197) / sg_fluid
        
        # Hitung Deviasi (%)
        deviation = ((actual_head - design_head) / design_head) * 100
        
        # Logic Diagnosa API 610/ISO 9906
        if deviation < -20.0:
            h_status = "CRITICAL / FAILURE"
            h_color = "#e74c3c"
            h_cause = "Kerusakan Internal Parah (Impeller Habis / Wear Ring Longgar)."
            h_action = "❌ STOP & OVERHAUL: Ganti Impeller & Wear Ring. Cek Celah (Clearance)."
            h_std = "API 610 (Performance Drop)"
        elif deviation < -10.0:
            h_status = "DEGRADATION / WARNING"
            h_color = "#e67e22"
            h_cause = "Keausan Internal (Wear Ring Gap Melebar) atau RPM Turun."
            h_action = "⚠️ JADWALKAN MAINTENANCE: Cek efisiensi & clearance wear ring saat stop."
            h_std = "ISO 9906 / ANSI HI 9.6.5"
        elif deviation > 15.0:
            h_status = "RESTRICTION / HIGH HEAD"
            h_color = "#f1c40f"
            h_cause = "Valve Discharge Kurang Buka atau Pipa Discharge Buntu."
            h_action = "🔧 CEK OPERASIONAL: Pastikan valve discharge terbuka sesuai SOP."
            h_std = "System Curve Analysis"
        else:
            h_status = "NORMAL / HEALTHY"
            h_color = "#2ecc71"
            h_cause = "Performa pompa sesuai kurva desain."
            h_action = "✅ LANJUTKAN OPERASI: Monitor parameter rutin."
            h_std = "API 610 (Rated Point)"

        # Tampilan Hasil Tab 4
        with col_h2:
            st.markdown(f"### Hasil Analisa")
            
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Diff. Pressure", f"{diff_press:.2f} Bar")
            c_m2.metric("Actual Head", f"{actual_head:.1f} m", f"{deviation:.1f}%")
            c_m3.metric("Status", h_status)

            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = actual_head,
                title = {'text': "Total Dynamic Head (m)"},
                delta = {'reference': design_head, 'relative': True, "valueformat": ".1%"},
                gauge = {
                    'axis': {'range': [0, design_head * 1.4]},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, design_head * 0.80], 'color': "#ffcccc"},
                        {'range': [design_head * 0.80, design_head * 0.90], 'color': "#ffe5b4"},
                        {'range': [design_head * 0.90, design_head * 1.15], 'color': "#d4edda"}
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': design_head}
                }
            ))
            fig_gauge.update_layout(height=230, margin=dict(t=30,b=20,l=20,r=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

            st.markdown(f"""
            <div style="background-color:{h_color}22; padding:15px; border-left:5px solid {h_color}; border-radius:5px;">
                <h4 style="color:{h_color}; margin:0;">{h_status}</h4>
                <p style="margin-top:10px;"><strong>🔍 Diagnosa Penyebab:</strong><br>{h_cause}</p>
                <p><strong>🛠️ Rekomendasi (Action):</strong><br>{h_action}</p>
                <hr>
                <p style="font-size:12px; color:#666;">📚 Standar Acuan: {h_std}</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Lihat Rumus Perhitungan"):
                st.latex(r"H_{actual} = \frac{(P_{out} - P_{in}) \times 10.197}{SG}")
                st.write("Jika deviasi Head > -10%, itu indikasi 'Internal Recirculation' akibat Wear Ring yang aus (Gap melebar).")
