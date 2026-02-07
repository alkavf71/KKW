import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum

# ==============================================================================
# 1. STANDAR & KONSTANTA (Standards Library)
# ==============================================================================
class ISOZone(Enum):
    """ISO 10816-3 Vibration Severity Zones"""
    A = "ZONE A: New machine condition (Kondisi Prima)"
    B = "ZONE B: Unlimited long-term operation allowable (Operasi Normal)"
    C = "ZONE C: Short-term operation allowable (WARNING: Operasi Terbatas)"
    D = "ZONE D: Vibration causes damage (DANGER: Kerusakan Fisik)"

class Limits:
    """Thresholds Standar (API, NEMA, ISO)"""
    # Electrical
    VOLT_UNBALANCE_LIMIT = 3.0  # NEMA MG-1
    CURR_UNBALANCE_LIMIT = 10.0 # NEMA MG-1
    # Mechanical
    VIB_WARN_DEFAULT = 2.80
    VIB_TRIP_DEFAULT = 7.10
    TEMP_BEARING_STD = 85.0

# ==============================================================================
# 2. STRUKTUR DATA (Data Classes)
# ==============================================================================
@dataclass
class AssetSpecs:
    """Database Spesifikasi Aset"""
    # Wajib diisi (Non-default)
    tag: str
    name: str
    area: str
    volt_rated: float
    fla_rated: float
    power_kw: float
    rpm: int
    
    # Opsional (Default)
    phase: int = 3
    mounting: str = "Rigid"
    max_temp_bearing: float = 85.0
    vib_limit_warning: float = 2.80

@dataclass
class VibPoint:
    """Struktur Data Satu Titik Vibrasi"""
    location: str # Motor DE, Pump NDE, dll
    axis: str     # Horizontal, Vertical, Axial
    value: float  # Nilai RMS (mm/s)

# ==============================================================================
# 3. DATABASE ASET (Asset Register)
# ==============================================================================
ASSET_DB = {
    "P-02": AssetSpecs(
        tag="P-02", name="Pompa Transfer Pertalite", area="FT Moutong",
        volt_rated=380.0, fla_rated=35.5, power_kw=18.5, rpm=2900,
        vib_limit_warning=2.80
    ),
    "733-P-103": AssetSpecs(
        tag="733-P-103", name="Pompa Booster Bio Solar", area="FT Luwuk",
        volt_rated=400.0, fla_rated=54.0, power_kw=30.0, rpm=2900,
        vib_limit_warning=4.50 # Class I Flexible
    ),
    "706-P-203": AssetSpecs(
        tag="706-P-203", name="Pompa Transfer LPG", area="IT Makassar",
        volt_rated=380.0, fla_rated=28.5, power_kw=15.0, rpm=2955,
        max_temp_bearing=90.0
    )
}

def get_asset_list(): return list(ASSET_DB.keys())
def get_asset_details(tag): return ASSET_DB.get(tag)

# ==============================================================================
# 4. LOGIC ENGINE: VIBRASI (Vibration Diagnostics)
# ==============================================================================
def analyze_vibration_matrix(readings: List[VibPoint], limit_warn: float) -> List[str]:
    """Diagnosa Matrix berdasarkan ISO 18436-2 (H/V/A Analysis)"""
    diagnosa = []
    high_vib = [r for r in readings if r.value > limit_warn]
    
    if not high_vib:
        return []

    # Helper function
    def get_val(loc_search, axis_search):
        found = [r.value for r in readings if loc_search in r.location and axis_search in r.axis]
        return max(found) if found else 0.0

    # 1. MISALIGNMENT (Axial Dominan di Kopling)
    m_de_a = get_val("Motor DE", "Axial")
    m_de_h = get_val("Motor DE", "Horizontal")
    p_de_a = get_val("Pump DE", "Axial")
    
    if (m_de_a > limit_warn and m_de_a > 0.5 * m_de_h) or (p_de_a > limit_warn):
        diagnosa.append("🔴 MISALIGNMENT (Angular) [Ref: ISO 18436]: Dominan Axial di Kopling (DE). Cek Alignment & Shims.")

    # 2. UNBALANCE (Horizontal Dominan)
    max_h = max([r.value for r in high_vib if "Horizontal" in r.axis], default=0)
    max_v = max([r.value for r in high_vib if "Vertical" in r.axis], default=0)
    max_a = max([r.value for r in high_vib if "Axial" in r.axis], default=0)

    if max_h > limit_warn and max_h > max_v and max_h > max_a:
         diagnosa.append("🟠 UNBALANCE [Ref: ISO 10816]: Dominan Radial/Horizontal. Cek kotoran Impeller/Fan & Balancing.")

    # 3. LOOSENESS (Vertical Dominan)
    if max_v > limit_warn and max_v > max_h:
        diagnosa.append("🔧 MECHANICAL LOOSENESS [Ref: API 686]: Dominan Vertikal. Cek Baut Pondasi & Soft Foot.")

    # 4. BENT SHAFT (Axial NDE Tinggi)
    m_nde_a = get_val("Motor NDE", "Axial")
    if m_nde_a > limit_warn and m_nde_a > m_de_a:
        diagnosa.append("⚠️ BENT SHAFT [Ref: ISO 18436]: Axial tinggi di Motor NDE. Cek Run-out poros.")

    # 5. HYDRAULIC / PIPE STRAIN (Pump > Motor)
    vib_motor = [r.value for r in readings if "Motor" in r.location]
    vib_pump = [r.value for r in readings if "Pump" in r.location]
    if vib_motor and vib_pump:
        avg_m = sum(vib_motor)/len(vib_motor)
        avg_p = sum(vib_pump)/len(vib_pump)
        if avg_p > limit_warn and avg_p > (avg_m * 1.5):
             diagnosa.append("🌊 PIPE STRAIN / HYDRAULIC [Ref: API 610]: Vibrasi Pompa dominan. Cek support pipa.")

    return list(set(diagnosa))

# ==============================================================================
# 5. LOGIC ENGINE: NOISE (Kebisingan)
# ==============================================================================
def analyze_noise_profile(noise_type: str, noise_loc: str, valve_test: str) -> List[str]:
    """Diagnosa Noise berdasarkan API 610 & TKI"""
    diagnosa = []
    
    # 1. BEARING DEFECT
    if noise_type == "Ngorok/Kasar (Growling)":
        diagnosa.append("🔊 BEARING DEFECT [Ref: ISO 18436]: Suara ngorok (Spalling). REKOMENDASI: Ganti Bearing.")
    elif noise_type == "Mencicit (Squealing)":
        diagnosa.append("🔊 LUBRICATION ISSUE [Ref: ISO 18436]: Kurang pelumas. REKOMENDASI: Regreasing.")

    # 2. RUBBING
    elif noise_type == "Gesekan Logam (Scraping)":
        diagnosa.append("🔊 RUBBING/MISALIGNMENT [Ref: API 686]: Gesekan poros. REKOMENDASI: Cek Alignment.")

    # 3. KAVITASI
    if noise_type == "Suara Kerikil/Letupan (Popping)" or "Casing" in noise_loc:
        diagnosa.append("🔊 KAVITASI [Ref: API 610]: Suara 'kerikil'. REKOMENDASI: Cek Strainer/Level Tangki.")

    # 4. FLOW RECIRCULATION
    if valve_test == "Suara Berubah Drastis (Recirculation)" or noise_type == "Gemuruh (Rumbling)":
        diagnosa.append("🌊 FLOW RECIRCULATION [Ref: API 610]: Operasi di bawah Flow Minimum. REKOMENDASI: Buka valve discharge.")
    
    return diagnosa

# ==============================================================================
# 6. LOGIC ENGINE: TEMPERATUR
# ==============================================================================
def analyze_temperature_profile(temps: Dict[str, float], limit_warn: float, noise_type: str, vib_axial_high: bool) -> List[str]:
    """Diagnosa Temperatur TKI D.1 & D.2"""
    diagnosa = []
    overheat_points = {loc: val for loc, val in temps.items() if val > limit_warn}
    
    if not overheat_points: return []

    for loc, val in overheat_points.items():
        base_msg = f"🔥 OVERHEAT di {loc} ({val}°C)."
        if noise_type == "Mencicit (Squealing)":
            diagnosa.append(f"{base_msg} SEBAB: Kurang Pelumas. ACTION: Regreasing.")
        elif "DE" in loc and vib_axial_high:
            diagnosa.append(f"{base_msg} SEBAB: Misalignment (Gesekan). ACTION: Hot Alignment.")
        elif noise_type == "Ngorok/Kasar (Growling)":
            diagnosa.append(f"{base_msg} SEBAB: Bearing Rusak. ACTION: Ganti Bearing.")
        elif "Pump" in loc and "Seal" in loc:
             diagnosa.append(f"{base_msg} SEBAB: Gland Packing Terlalu Kencang/Seal Flush Buntu.")
        else:
            diagnosa.append(f"{base_msg} ACTION: Cek Fisik Sesuai TKI D.1.")
            
    return list(set(diagnosa))

# ==============================================================================
# 7. LOGIC ENGINE: ELEKTRIKAL
# ==============================================================================
def analyze_electrical_health(v_in: List[float], i_in: List[float], i_g: float, rated_v: float, flc: float) -> Tuple[List[str], float, float]:
    """Diagnosa Elektrikal (ANSI/NEMA)"""
    diagnosa = []
    
    avg_v = np.mean(v_in)
    avg_i = np.mean(i_in)
    max_i = max(i_in)
    
    # NEMA Calculation
    def calc_unb(vals):
        avg = np.mean(vals)
        return (max(abs(v - avg) for v in vals) / avg * 100) if avg > 0 else 0.0

    v_unbal = calc_unb(v_in)
    i_unbal = calc_unb(i_in)

    # ANSI CHECKS
    if avg_v < (rated_v * 0.90): diagnosa.append(f"⚡ ANSI 27 - UNDERVOLTAGE ({avg_v:.0f}V)")
    if avg_v > (rated_v * 1.10): diagnosa.append(f"⚡ ANSI 59 - OVERVOLTAGE ({avg_v:.0f}V)")
    if v_unbal > Limits.VOLT_UNBALANCE_LIMIT: diagnosa.append(f"⚡ ANSI 47 - VOLTAGE UNBALANCE ({v_unbal:.1f}%)")
    
    if avg_i < (flc * 0.40) and avg_i > 1.0: diagnosa.append(f"💧 ANSI 37 - DRY RUN / LOW LOAD ({avg_i:.1f}A)")
    if max_i > (flc * 1.10): diagnosa.append(f"🔥 ANSI 51 - OVERLOAD ({max_i:.1f}A)")
    if i_unbal > Limits.CURR_UNBALANCE_LIMIT: diagnosa.append(f"⚖️ ANSI 46 - CURRENT UNBALANCE ({i_unbal:.1f}%)")
    if i_g > 0.5: diagnosa.append(f"⚠️ ANSI 50G - GROUND FAULT ({i_g}A)")

    return diagnosa, v_unbal, i_unbal

# ==============================================================================
# 8. LOGIC ENGINE: KESEHATAN FINAL (Health Index)
# ==============================================================================
def assess_overall_health(vib_zone: str, elec_status: str, temp_max: float, physical_issues: List[str]) -> Dict:
    """Keputusan Final: GOOD / FAIR / BAD"""
    severity = 0
    reasons = []

    # SENSOR CHECKS
    if "ZONE D" in vib_zone: 
        severity += 3
        reasons.append("Vibrasi Zona BAHAYA (Zone D)")
    elif "ZONE C" in vib_zone: 
        severity += 1
        reasons.append("Vibrasi Tinggi (Zone C)")

    if "TRIP" in elec_status: 
        severity += 3
        reasons.append("Elektrikal Critical Fault")
    
    if temp_max > 85.0: 
        severity += 3
        reasons.append(f"Overheat Ekstrem ({temp_max}°C)")

    # PHYSICAL CHECKS (Gambar User)
    for issue in physical_issues:
        if "MAJOR" in issue.upper() or "NOT COST" in issue.upper():
            severity += 5 # Auto BAD
            reasons.append(f"Fisik: {issue}")
        elif "MINOR" in issue.upper() or "WELD" in issue.upper():
            severity += 1
            reasons.append(f"Fisik: {issue}")

    # DECISION
    if severity >= 3:
        return {"status": "BAD", "color": "#e74c3c", "desc": "KONDISI KRITIS (Rusak Berat)", 
                "action": "❌ STOP OPERASI. Perbaikan tidak ekonomis atau butuh overhaul total.", "reasons": reasons}
    elif severity >= 1:
        return {"status": "FAIR", "color": "#f1c40f", "desc": "KONDISI WARNING (Cukup)", 
                "action": "⚠️ PENGAWASAN KHUSUS. Jadwalkan perbaikan minor.", "reasons": reasons}
    else:
        return {"status": "GOOD", "color": "#2ecc71", "desc": "KONDISI PRIMA (Baik)", 
                "action": "✅ LANJUT OPERASI. Unit sehat.", "reasons": reasons}

# ==============================================================================
# 9. MAIN DASHBOARD UI (Streamlit)
# ==============================================================================
def main():
    st.set_page_config(page_title="Reliability Pro", page_icon="🏭", layout="wide")
    
    # Init Session State
    if 'mech_result' not in st.session_state: st.session_state.mech_result = None
    if 'elec_result' not in st.session_state: st.session_state.elec_result = None
    if 'health_result' not in st.session_state: st.session_state.health_result = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🏭 Reliability Pro")
        st.caption("Industrial Diagnostic System v2.0")
        
        activity_type = st.radio("🛠️ Aktivitas:", ["Inspeksi Rutin", "Commissioning (API 686)"])
        is_commissioning = "Commissioning" in activity_type
        
        st.divider()
        selected_tag = st.selectbox("📌 Pilih Aset:", get_asset_list())
        asset = get_asset_details(selected_tag)
        
        st.info(f"**{asset.name}**\n\nKW: {asset.power_kw} | RPM: {asset.rpm}\nVolt: {asset.volt_rated}V | FLC: {asset.fla_rated}A")

    # --- HEADER ---
    st.title(f"Dashboard Diagnosa: {asset.tag}")
    
    tab1, tab2, tab3 = st.tabs(["⚙️ MEKANIKAL & FISIK", "⚡ ELEKTRIKAL", "🏥 KESIMPULAN KESEHATAN"])

    # === TAB 1: MEKANIKAL ===
    with tab1:
        col_in, col_out = st.columns([1.2, 1])
        with col_in:
            with st.form("mech_form"):
                st.subheader("1. Data Vibrasi (mm/s) & Suhu (°C)")
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
                
                st.subheader("2. Inspeksi Noise & Fisik")
                with st.expander("📝 Checklist Kondisi", expanded=True):
                    # Noise
                    st.markdown("**Noise Profile:**")
                    noise_type = st.selectbox("Suara:", ["Normal (Humming)", "Suara Kerikil/Letupan (Popping)", "Ngorok/Kasar (Growling)", "Mencicit (Squealing)", "Gesekan Logam (Scraping)", "Gemuruh (Rumbling)", "Desis Keras (Hissing)"])
                    noise_loc = st.selectbox("Lokasi:", ["-", "Motor DE", "Motor NDE", "Pump DE", "Pump NDE", "Casing"])
                    valve_test = st.radio("Valve Test:", ["Tidak Dilakukan", "Suara Stabil", "Suara Berubah Drastis (Recirculation)"], horizontal=True)
                    
                    st.divider()
                    # Physical (Sesuai Gambar User)
                    st.markdown("**Temuan Fisik (Visual):**")
                    chk_minor = st.checkbox("⚠️ Minor Parts Missing / Weld Repairs")
                    chk_major = st.checkbox("⛔ MAJOR Parts Missing / Major Weld Repairs")
                    chk_cost = st.checkbox("⛔ Not Cost Effective to Repair")

                submit_mech = st.form_submit_button("🔍 ANALISA MEKANIKAL")

        if submit_mech:
            # Build Data Objects
            readings = [
                VibPoint("Motor DE", "Horizontal", m_de_h), VibPoint("Motor DE", "Vertical", m_de_v), VibPoint("Motor DE", "Axial", m_de_a),
                VibPoint("Motor NDE", "Horizontal", m_nde_h), VibPoint("Motor NDE", "Vertical", m_nde_v), VibPoint("Motor NDE", "Axial", m_nde_a),
                VibPoint("Pump DE", "Horizontal", p_de_h), VibPoint("Pump DE", "Vertical", p_de_v), VibPoint("Pump DE", "Axial", p_de_a),
                VibPoint("Pump NDE", "Horizontal", p_nde_h), VibPoint("Pump NDE", "Vertical", p_nde_v), VibPoint("Pump NDE", "Axial", p_nde_a),
            ]
            temps = {"Motor DE": t_m_de, "Motor NDE": t_m_nde, "Pump DE": t_p_de, "Pump NDE": t_p_nde}
            
            # Logic Processing
            limit_vib = 3.0 if is_commissioning else asset.vib_limit_warning
            
            vib_causes = analyze_vibration_matrix(readings, limit_vib)
            noise_causes = analyze_noise_profile(noise_type, noise_loc, valve_test)
            
            is_axial_high = any(r.value > limit_vib and r.axis == "Axial" and "DE" in r.location for r in readings)
            temp_causes = analyze_temperature_profile(temps, asset.max_temp_bearing, noise_type, is_axial_high)
            
            # ISO Zone Determination
            max_vib = max(r.value for r in readings)
            if max_vib < 2.8: zone = ISOZone.A.value
            elif max_vib < 7.1: zone = ISOZone.B.value if not is_commissioning else "ZONE C (Fail Comm.)"
            else: zone = ISOZone.D.value

            # Physical List
            phys_list = []
            if chk_minor: phys_list.append("Minor Parts/Weld Issue")
            if chk_major: phys_list.append("MAJOR Parts/Weld Issue")
            if chk_cost: phys_list.append("NOT COST EFFECTIVE TO REPAIR")

            st.session_state.mech_result = {
                "max": max_vib, "zone": zone, "causes": vib_causes+noise_causes+temp_causes,
                "temps": temps, "physical": phys_list
            }

        # Result Display
        with col_out:
            st.subheader("📊 Hasil Diagnosa")
            if st.session_state.mech_result:
                res = st.session_state.mech_result
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=res['max'], title={'text': "Max Vib (mm/s)"},
                    gauge={'axis': {'range': [0, 10]}, 'bar': {'color': "black"},
                           'steps': [{'range': [0, 2.8], 'color': "#2ecc71"}, {'range': [2.8, 7.1], 'color': "#f1c40f"}, {'range': [7.1, 10], 'color': "#e74c3c"}]}
                ))
                fig.update_layout(height=250, margin=dict(t=30,b=20,l=20,r=20))
                st.plotly_chart(fig, use_container_width=True)
                
                st.info(f"**{res['zone']}**")
                
                if res['causes']:
                    st.error("🚨 **MASALAH TERDETEKSI:**")
                    for c in res['causes']: st.write(f"- {c}")
                else:
                    st.success("✅ Mekanikal & Suhu Normal")
                
                if res['physical']:
                    st.warning(f"⚠️ **Fisik:** {', '.join(res['physical'])}")

    # === TAB 2: ELEKTRIKAL ===
    with tab2:
        with st.form("elec_form"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Voltase (Rated: {asset.volt_rated}V)**")
                v1 = st.number_input("R-S", value=asset.volt_rated)
                v2 = st.number_input("S-T", value=asset.volt_rated)
                v3 = st.number_input("T-R", value=asset.volt_rated)
            with c2:
                st.markdown(f"**Ampere (FLA: {asset.fla_rated}A)**")
                def_load = asset.fla_rated * 0.8
                i1 = st.number_input("Phase R", value=def_load)
                i2 = st.number_input("Phase S", value=def_load)
                i3 = st.number_input("Phase T", value=def_load)
                ig = st.number_input("Ground", 0.0, 10.0, 0.0)
            submit_elec = st.form_submit_button("🔍 ANALISA ELEKTRIKAL")

        if submit_elec:
            causes, vu, iu = analyze_electrical_health([v1,v2,v3], [i1,i2,i3], ig, asset.volt_rated, asset.fla_rated)
            st.session_state.elec_result = {"causes": causes, "vu": vu, "iu": iu}

        if st.session_state.elec_result:
            res = st.session_state.elec_result
            c1, c2, c3 = st.columns(3)
            c1.metric("Volt Unbalance", f"{res['vu']:.2f}%", "Max 3%")
            c2.metric("Curr Unbalance", f"{res['iu']:.2f}%", "Max 10%")
            c3.metric("Status", "FAULT" if res['causes'] else "OK")
            if res['causes']:
                st.error("🚨 **ANSI CODE VIOLATION:**")
                for c in res['causes']: st.write(f"- {c}")
            else:
                st.success("✅ Elektrikal Sehat")

    # === TAB 3: KESIMPULAN ===
    with tab3:
        if st.button("🔄 GENERATE FINAL REPORT"):
            if not st.session_state.mech_result:
                st.warning("⚠️ Harap jalankan Analisa Mekanikal dulu.")
            else:
                mech = st.session_state.mech_result
                elec = st.session_state.elec_result
                elec_stat = "TRIP" if (elec and elec['causes']) else "Normal"
                
                health = assess_overall_health(mech['zone'], elec_stat, max(mech['temps'].values()), mech['physical'])
                st.session_state.health_result = health

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

if __name__ == "__main__":
    main()
