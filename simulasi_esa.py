import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Tuple, Dict
from enum import Enum
from datetime import datetime
import os

# ==========================================
# 1. STANDARDS & CONSTANTS LIBRARY
# ==========================================
class ANSI:
    """IEEE C37.2 Standard Device Numbers"""
    UV_27 = "27 - Undervoltage"
    UC_37 = "37 - Undercurrent (Dry Run)"
    UB_46 = "46 - Current Unbalance"
    VU_47 = "47 - Voltage Unbalance"
    TH_49 = "49 - Thermal Overload"
    IOC_50 = "50 - Instantaneous Overcurrent"
    GF_50N = "50N/51N - Ground Fault"
    LR_50LR = "50LR - Locked Rotor"
    TOC_51 = "51 - Time Overcurrent"
    OV_59 = "59 - Overvoltage"
    ST_66 = "66 - Start Limitation"

class ISOZone(Enum):
    """ISO 10816-3 Vibration Severity Zones"""
    A = "GOOD (Zone A)"
    B = "SATISFACTORY (Zone B)"
    C = "UNSATISFACTORY (Zone C)"
    D = "UNACCEPTABLE (Zone D)"

class Limits:
    # --- ELECTRICAL ---
    VOLTAGE_UNBALANCE_TRIP = 3.0
    CURRENT_UNBALANCE_ALARM = 5.0
    CURRENT_UNBALANCE_TRIP = 10.0
    
    # --- MECHANICAL (ISO 10816-3 Group 2 Rigid) ---
    VIB_WARN = 2.80 
    VIB_TRIP = 7.10 
    ISO_CLASS_II = [1.12, 2.80, 7.10] 
    
    # --- COMMISSIONING (API 686) ---
    MAX_SOFT_FOOT = 0.05
    ALIGNMENT_TOLERANCE = 0.05

# ==========================================
# 2. DATA MODELS
# ==========================================
@dataclass
class ProtectionSettings:
    flc_amps: float
    rated_volt: float
    pickup_51: float = 1.10
    pickup_50: float = 6.00
    pickup_27: float = 0.90
    pickup_59: float = 1.10
    pickup_37: float = 0.40
    pickup_50n: float = 1.0
    max_starts_hr: int = 3

@dataclass
class MechanicalSpecs:
    power_kw: float
    rpm_design: int
    bearing_temp_limit: float = 85.0

@dataclass
class Asset:
    tag: str
    name: str
    loc: str
    mech: MechanicalSpecs
    elec: ProtectionSettings

@dataclass
class VibrationReading:
    location: str
    axis: str
    value: float

# --- DATABASE ASET ---
ASSETS_DB = {
    "P-02": Asset(
        "0459599", "Pompa Pertalite", "FT Moutong",
        MechanicalSpecs(power_kw=18.5, rpm_design=2900),
        ProtectionSettings(flc_amps=35.5, rated_volt=380.0, max_starts_hr=4)
    ),
    "733-P-103": Asset(
        "1041535A", "Pompa Bio Solar", "FT Luwuk",
        MechanicalSpecs(power_kw=30.0, rpm_design=2900),
        ProtectionSettings(flc_amps=54.0, rated_volt=400.0, max_starts_hr=3)
    ),
    "706-P-203": Asset(
        "049-1611186", "Pompa LPG", "IT Makassar",
        MechanicalSpecs(power_kw=15.0, rpm_design=2955),
        ProtectionSettings(flc_amps=28.5, rated_volt=380.0, max_starts_hr=3)
    )
}

# ==========================================
# 3. DATABASE MANAGER
# ==========================================
DB_FILE = "reliability_history.csv"

def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
            "Timestamp", "Asset_Tag", "Type", "Max_Value", 
            "Status_Zone", "Diagnosa", "Details"
        ])
        df.to_csv(DB_FILE, index=False)

def save_record(asset_tag, type_chk, max_val, status, diagnosa, details):
    init_db()
    new_data = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Asset_Tag": asset_tag,
        "Type": type_chk,
        "Max_Value": max_val,
        "Status_Zone": status,
        "Diagnosa": " | ".join(diagnosa),
        "Details": str(details)
    }
    df = pd.DataFrame([new_data])
    df.to_csv(DB_FILE, mode='a', header=False, index=False)
    return True

def load_history(tag_filter=None):
    init_db()
    try:
        df = pd.read_csv(DB_FILE)
        if tag_filter and tag_filter != "ALL":
            df = df[df["Asset_Tag"] == tag_filter]
        return df.sort_values(by="Timestamp", ascending=False)
    except Exception:
        return pd.DataFrame()

# ==========================================
# 4. LOGIC ENGINES
# ==========================================
class ElectricalEngine:
    def __init__(self, settings: ProtectionSettings):
        self.s = settings
        self.flags = []

    def analyze(self, v_in, i_in, i_g, starts, temp, status_m):
        self.flags = []
        v1, v2, v3 = v_in
        i1, i2, i3 = i_in
        is_starting = (status_m == "Starting")
        
        avg_v = np.mean([v1, v2, v3])
        if avg_v > 0:
            max_v_dev = max(abs(v - avg_v) for v in [v1, v2, v3])
            v_unbal = (max_v_dev / avg_v) * 100
            if v_unbal > Limits.VOLTAGE_UNBALANCE_TRIP:
                self.flags.append(f"TRIP {ANSI.VU_47}: Unbalance {v_unbal:.1f}%")
        else: v_unbal = 0.0

        if avg_v < (self.s.rated_volt * self.s.pickup_27):
            self.flags.append(f"TRIP {ANSI.UV_27}: Undervoltage {avg_v:.1f}V")
        elif avg_v > (self.s.rated_volt * self.s.pickup_59):
            self.flags.append(f"TRIP {ANSI.OV_59}: Overvoltage {avg_v:.1f}V")

        max_i = max(i1, i2, i3)
        avg_i = np.mean([i1, i2, i3])
        
        if is_starting:
            if max_i > (self.s.flc_amps * self.s.pickup_50):
                self.flags.append(f"TRIP {ANSI.LR_50LR}: Locked Rotor {max_i:.1f}A")
        else:
            if max_i > (self.s.flc_amps * self.s.pickup_51):
                self.flags.append(f"TRIP {ANSI.TOC_51}: Overload {max_i:.1f}A")
            elif avg_i < (self.s.flc_amps * self.s.pickup_37) and avg_i > 1.0:
                self.flags.append(f"ALARM {ANSI.UC_37}: Dry Run {avg_i:.1f}A")

        if avg_i > 0:
            max_i_dev = max(abs(i - avg_i) for i in [i1, i2, i3])
            i_unbal = (max_i_dev / avg_i) * 100
            if i_unbal > Limits.CURRENT_UNBALANCE_TRIP:
                self.flags.append(f"TRIP {ANSI.UB_46}: Unbalance {i_unbal:.1f}%")
        else: i_unbal = 0.0

        if i_g > self.s.pickup_50n:
            self.flags.append(f"TRIP {ANSI.GF_50N}: Ground Fault {i_g:.2f}A")
        if starts > self.s.max_starts_hr:
            self.flags.append(f"BLOCK {ANSI.ST_66}: Max Starts Exceeded")
        if temp > 130:
            self.flags.append(f"TRIP {ANSI.TH_49}: Overheat {temp}°C")

        return self.flags, i_unbal, v_unbal

class MechanicalEngine:
    @staticmethod
    def calculate_averages(readings: List[VibrationReading]) -> List[dict]:
        groups = {"Motor H": [], "Motor V": [], "Motor A": [], "Pump H": [], "Pump V": [], "Pump A": []}
        for r in readings:
            key = ""
            if "Motor" in r.location: key += "Motor "
            elif "Pump" in r.location: key += "Pump "
            if "Horizontal" in r.axis: key += "H"
            elif "Vertical" in r.axis: key += "V"
            elif "Axial" in r.axis: key += "A"
            if key in groups: groups[key].append(r.value)
        
        return [{"label": k, "value": sum(v)/len(v)} for k, v in groups.items() if v]

    @staticmethod
    def get_iso_status(val: float) -> Tuple[ISOZone, str]:
        limits = Limits.ISO_CLASS_II
        if val <= limits[0]: return ISOZone.A, "#2ecc71"
        elif val <= limits[1]: return ISOZone.B, "#f1c40f"
        elif val <= limits[2]: return ISOZone.C, "#e67e22"
        else: return ISOZone.D, "#e74c3c"

    @staticmethod
    def analyze_root_cause(readings: List[VibrationReading], noise_chk: bool, temps: Dict[str, float], limit_temp: float) -> List[str]:
        causes = []
        warning_limit = Limits.VIB_WARN
        problem_points = [r for r in readings if r.value > warning_limit]
        
        # 1. TEMPERATUR CHECK (Specific Location)
        # Cari suhu tertinggi
        max_t_loc = max(temps, key=temps.get)
        max_t_val = temps[max_t_loc]
        
        if max_t_val > limit_temp:
            causes.append(f"🔥 OVERHEAT: {max_t_loc} mencapai {max_t_val}°C > {limit_temp}°C")

        # 2. VIBRATION CHECK
        if not problem_points and not noise_chk and max_t_val <= limit_temp:
            return ["Normal Operation"]

        # A. Misalignment
        if any(r.axis == "Axial" and "DE" in r.location and r.value > warning_limit for r in problem_points):
            causes.append("🔴 MISALIGNMENT (Ref: TKI C-017): Dominan Axial pada sisi DE.")
        
        # B. Unbalance
        high_horiz = [r for r in problem_points if r.axis == "Horizontal"]
        high_axial = [r for r in problem_points if r.axis == "Axial"]
        if high_horiz:
            if not high_axial or (max(h.value for h in high_horiz) > max(a.value for a in high_axial)):
                causes.append("🟠 UNBALANCE (Ref: TKI C-017): Dominan Radial/Horizontal.")

        # C. Looseness
        if any(r.axis == "Vertical" and r.value > warning_limit for r in problem_points):
             causes.append("🔧 LOOSENESS (Ref: TKI C-017): Dominan Vertikal.")

        # D. Bearing/Flow
        if any("Pump NDE" in r.location and r.value > warning_limit for r in problem_points):
            causes.append("🔩 BEARING/HYDRAULIC: Vibrasi tinggi di ujung pompa (NDE).")

        # 3. NOISE CHECK
        if noise_chk:
            max_val = max(r.value for r in readings)
            if max_val > warning_limit:
                 causes.append("🔊 NOISE + VIBRASI: Kerusakan Mekanis (Bearing hancur / Rubbing).")
            else:
                 causes.append("🔊 NOISE (HIDROLIK): Vibrasi rendah tapi berisik (Kavitasi / Masuk Angin).")

        return list(set(causes))

class CommissioningEngine:
    @staticmethod
    def validate(soft_foot, v_off, h_off, grout_ok, pipe_ok):
        issues = []
        if soft_foot > Limits.MAX_SOFT_FOOT: issues.append(f"❌ Soft Foot {soft_foot}mm > {Limits.MAX_SOFT_FOOT}mm")
        max_align = max(abs(v_off), abs(h_off))
        if max_align > Limits.ALIGNMENT_TOLERANCE: issues.append(f"❌ Alignment {max_align}mm > {Limits.ALIGNMENT_TOLERANCE}mm")
        if not grout_ok: issues.append("❌ Grouting Check Failed")
        if not pipe_ok: issues.append("❌ Pipe Strain Detected")
        status = "FAILED" if issues else "PASSED"
        return status, issues

# ==========================================
# 5. STREAMLIT FRONTEND
# ==========================================
def main():
    st.set_page_config(page_title="Reliability Pro Dashboard", layout="wide", page_icon="🏭")
    
    if 'mech_result' not in st.session_state: st.session_state.mech_result = None
    if 'elec_result' not in st.session_state: st.session_state.elec_result = None
    if 'comm_result' not in st.session_state: st.session_state.comm_result = None

    with st.sidebar:
        st.title("🏭 Reliability Pro")
        st.caption("Industrial Grade Asset Diagnostics")
        selected_tag = st.selectbox("Select Asset:", list(ASSETS_DB.keys()))
        asset = ASSETS_DB[selected_tag]
        
        st.info(f"""
        **{asset.name}**
        📍 {asset.loc}
        ⚡ {asset.elec.flc_amps}A / {asset.elec.rated_volt}V
        🌊 {asset.mech.power_kw}kW / {asset.mech.rpm_design}RPM
        """)
        
        st.divider()
        if st.checkbox("Show History"):
            hist_df = load_history(selected_tag)
            st.dataframe(hist_df, use_container_width=True)
            csv = hist_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "history.csv", "text/csv")

    st.title(f"Dashboard Diagnosa: {asset.tag}")
    tab1, tab2, tab3 = st.tabs(["🌊 Mechanical", "⚡ Electrical", "🚀 Commissioning"])

    # === TAB 1: MECHANICAL ===
    with tab1:
        st.subheader("Vibration & Temperature (ISO 10816-3 / TKI C-017)")
        
        with st.form("mech_form"):
            col_m, col_p = st.columns(2)
            def v_in(lbl): return st.number_input(lbl, 0.0, 50.0, 0.5, 0.01)
            def t_in(lbl): return st.number_input(lbl, 0.0, 150.0, 45.0, 0.1)
            
            with col_m:
                st.markdown("#### ⚡ Driver (Motor)")
                c1, c2, c3 = st.columns(3)
                m_nde_h, m_nde_v, m_nde_a = c1.number_input("M-NDE H",0.0,50.0,0.5), c2.number_input("M-NDE V",0.0,50.0,0.5), c3.number_input("M-NDE A",0.0,50.0,0.5)
                c4, c5, c6 = st.columns(3)
                m_de_h, m_de_v, m_de_a = c4.number_input("M-DE H",0.0,50.0,0.5), c5.number_input("M-DE V",0.0,50.0,0.5), c6.number_input("M-DE A",0.0,50.0,0.5)
                
                st.markdown("---")
                st.markdown("**🌡️ Motor Temp (°C)**")
                tm1, tm2 = st.columns(2)
                t_m_nde = tm1.number_input("Motor NDE Temp", 0.0, 150.0, 50.0)
                t_m_de = tm2.number_input("Motor DE Temp", 0.0, 150.0, 62.0)

            with col_p:
                st.markdown("#### 💧 Driven (Pompa)")
                c7, c8, c9 = st.columns(3)
                p_de_h, p_de_v, p_de_a = c7.number_input("P-DE H",0.0,50.0,0.5), c8.number_input("P-DE V",0.0,50.0,0.5), c9.number_input("P-DE A",0.0,50.0,0.5)
                c10, c11, c12 = st.columns(3)
                p_nde_h, p_nde_v, p_nde_a = c10.number_input("P-NDE H",0.0,50.0,0.5), c11.number_input("P-NDE V",0.0,50.0,0.5), c12.number_input("P-NDE A",0.0,50.0,0.5)
                
                st.markdown("---")
                st.markdown("**🌡️ Pump Temp (°C)**")
                tp1, tp2 = st.columns(2)
                t_p_de = tp1.number_input("Pump DE Temp", 0.0, 150.0, 75.0)
                t_p_nde = tp2.number_input("Pump NDE Temp", 0.0, 150.0, 55.0)
            
            st.markdown("---")
            noise_chk = st.checkbox("🔊 Abnormal Noise Detected?")
            submit_mech = st.form_submit_button("🔍 ANALYZE MECHANICAL")
        
        if submit_mech:
            readings = [
                VibrationReading("Motor NDE", "Horizontal", m_nde_h), VibrationReading("Motor NDE", "Vertical", m_nde_v), VibrationReading("Motor NDE", "Axial", m_nde_a),
                VibrationReading("Motor DE", "Horizontal", m_de_h), VibrationReading("Motor DE", "Vertical", m_de_v), VibrationReading("Motor DE", "Axial", m_de_a),
                VibrationReading("Pump DE", "Horizontal", p_de_h), VibrationReading("Pump DE", "Vertical", p_de_v), VibrationReading("Pump DE", "Axial", p_de_a),
                VibrationReading("Pump NDE", "Horizontal", p_nde_h), VibrationReading("Pump NDE", "Vertical", p_nde_v), VibrationReading("Pump NDE", "Axial", p_nde_a),
            ]
            temps = {"Motor NDE": t_m_nde, "Motor DE": t_m_de, "Pump DE": t_p_de, "Pump NDE": t_p_nde}
            
            # Logic TKI: Average for Limit
            avgs = MechanicalEngine.calculate_averages(readings)
            max_avg_obj = max(avgs, key=lambda x: x['value'])
            iso_zone, color = MechanicalEngine.get_iso_status(max_avg_obj['value'])
            
            # Logic Diagnosa: Individual + Temp Locations
            causes = MechanicalEngine.analyze_root_cause(readings, noise_chk, temps, asset.mech.bearing_temp_limit)
            
            st.session_state.mech_result = {
                "max": max_avg_obj['value'], "zone": iso_zone.value, "color": color, 
                "causes": causes, "loc": f"Avg {max_avg_obj['label']}",
                "raw_vib": {r.location+r.axis: r.value for r in readings},
                "raw_temp": temps
            }

        if st.session_state.mech_result:
            res = st.session_state.mech_result
            d1, d2 = st.columns([1,2])
            with d1:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=res['max'],
                    title={'text': "Max Average Vibration"},
                    gauge={'axis': {'range': [0, 10]}, 'bar': {'color': "black"},
                           'steps': [{'range': [0, 2.8], 'color': "#2ecc71"}, {'range': [2.8, 7.1], 'color': "#f1c40f"}, {'range': [7.1, 10], 'color': "#e74c3c"}]}
                ))
                fig.update_layout(height=250, margin=dict(t=30,b=20,l=20,r=20))
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📍 Determinant: {res['loc']}")
            
            with d2:
                st.markdown(f"### Status: :{ 'green' if 'A' in res['zone'] or 'B' in res['zone'] else 'red' }[{res['zone']}]")
                st.markdown("**Diagnosa AI:**")
                for c in res['causes']: st.write(f"- {c}")
                
                if st.button("💾 SIMPAN HASIL MEKANIKAL"):
                    details = f"Vibs: {res['raw_vib']} | Temps: {res['raw_temp']}"
                    save_record(asset.tag, "Mechanical", f"{res['max']:.2f} mm/s", res['zone'], res['causes'], details)
                    st.success("✅ Data tersimpan di History.")

    # === TAB 2: ELECTRICAL ===
    with tab2:
        st.subheader("Protection Relay Simulation")
        with st.form("elec_form"):
            e1, e2, e3 = st.columns(3)
            v_def = float(asset.elec.rated_volt)
            c_def = float(asset.elec.flc_amps * 0.8)
            
            with e1:
                st.markdown("Voltage")
                v1 = st.number_input("L1-L2", 0.0, 1000.0, v_def, 0.1)
                v2 = st.number_input("L2-L3", 0.0, 1000.0, v_def, 0.1)
                v3 = st.number_input("L3-L1", 0.0, 1000.0, v_def, 0.1)
            with e2:
                st.markdown("Current")
                i1 = st.number_input("Ph 1", 0.0, 1000.0, c_def, 0.1)
                i2 = st.number_input("Ph 2", 0.0, 1000.0, c_def, 0.1)
                i3 = st.number_input("Ph 3", 0.0, 1000.0, c_def, 0.1)
                ig = st.number_input("Gnd", 0.0, 100.0, 0.0, 0.01)
            with e3:
                st.markdown("Stats")
                starts = st.number_input("Starts/Hr", 0, 10, 0)
                temp_w = st.number_input("Wind Temp", 0.0, 200.0, 60.0)
                state = st.radio("State", ["Running", "Starting"])
            
            submit_elec = st.form_submit_button("🔍 ANALYZE PROTECTION")

        if submit_elec:
            eng = ElectricalEngine(asset.elec)
            logs, iu, vu = eng.analyze([v1,v2,v3], [i1,i2,i3], ig, starts, temp_w, state)
            st.session_state.elec_result = {"logs": logs, "iu": iu, "vu": vu, "vals": f"Vavg:{np.mean([v1,v2,v3]):.0f}, Iavg:{np.mean([i1,i2,i3]):.0f}"}

        if st.session_state.elec_result:
            res = st.session_state.elec_result
            logs = res['logs']
            codes = [ANSI.UV_27, ANSI.OV_59, ANSI.VU_47, ANSI.IOC_50, ANSI.TOC_51, ANSI.UC_37, ANSI.UB_46, ANSI.GF_50N]
            cols = st.columns(4)
            for i, c in enumerate(codes):
                is_trip = any(c.split(' - ')[0] in l for l in logs)
                color = "red" if is_trip else "green"
                cols[i%4].markdown(f"<div style='border:1px solid {color};padding:5px;text-align:center;border-radius:5px;background-color:{'#ffcccc' if is_trip else '#ccffcc'}'><b>{c.split(' - ')[0]}</b><br><small>{c.split(' - ')[1]}</small></div>", unsafe_allow_html=True)
            
            st.divider()
            if logs:
                st.error("🚨 ACTIVE FAULTS:")
                for l in logs: st.write(f"- {l}")
                status_txt = "TRIP / ALARM"
            else:
                st.success("✅ SYSTEM HEALTHY")
                status_txt = "NORMAL"

            if st.button("💾 SIMPAN HASIL ELEKTRIKAL"):
                save_record(asset.tag, "Electrical", res['vals'], status_txt, logs if logs else ["Healthy"], res['vals'])
                st.success("✅ Data tersimpan.")

    # === TAB 3: COMMISSIONING ===
    with tab3:
        st.subheader("Installation Check (API 686)")
        with st.form("comm_form"):
            c1, c2 = st.columns(2)
            soft_foot = c1.number_input("Max Soft Foot (mm)", 0.00, 1.00, 0.00, 0.01)
            v_off = c2.number_input("Vertical Offset (mm)", -1.0, 1.0, 0.00, 0.01)
            h_off = c2.number_input("Horizontal Offset (mm)", -1.0, 1.0, 0.00, 0.01)
            chk_g = st.checkbox("Grouting Sound?")
            chk_p = st.checkbox("Pipe Strain Free?")
            submit_comm = st.form_submit_button("✅ VALIDATE")

        if submit_comm:
            stat, issues = CommissioningEngine.validate(soft_foot, v_off, h_off, chk_g, ch_p)
            st.session_state.comm_result = {"status": stat, "issues": issues}

        if st.session_state.comm_result:
            res = st.session_state.comm_result
            if res['status'] == "FAILED":
                st.error("⛔ COMMISSIONING FAILED")
                for i in res['issues']: st.write(i)
            else:
                st.success("🎉 PASSED (Ready for Start-up)")
            if st.button("💾 SIMPAN KOMISIONING"):
                save_record(asset.tag, "Commissioning", res['status'], res['status'], res['issues'], f"SF:{soft_foot}")
                st.success("✅ Data tersimpan.")

if __name__ == "__main__":
    main()
