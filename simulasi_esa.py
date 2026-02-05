import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# ==========================================
# 1. STANDARDS & CONSTANTS LIBRARY
# ==========================================
class ANSI:
    """IEEE C37.2 Standard Device Numbers"""
    UV_27 = "27 - Undervoltage"
    UC_37 = "37 - Undercurrent (Dry Run)"
    UB_46 = "46 - Current Unbalance / Neg Seq"
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
    # --- ELECTRICAL (IEC 60034 / NEMA MG-1) ---
    VOLTAGE_TOLERANCE_PCT = 10.0
    UNBALANCE_ALARM = 2.0
    UNBALANCE_TRIP = 5.0
    
    # --- MECHANICAL (ISO 10816-3 / API 610) ---
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
    # Thresholds
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
    mounting: str = "Rigid"
    coupling_type: str = "Flexible"
    bearing_temp_limit: float = 85.0

@dataclass
class VibrationReading:
    location: str
    axis: str
    value: float

@dataclass
class Asset:
    tag: str
    name: str
    loc: str
    mech: MechanicalSpecs
    elec: ProtectionSettings

# --- ASSET DATABASE ---
ASSETS_DB = {
    "P-02": Asset(
        "0459599", "Pompa Pertalite", "FT Moutong",
        MechanicalSpecs(power_kw=18.5, rpm_design=2900, mounting="Rigid"),
        ProtectionSettings(flc_amps=35.5, rated_volt=380.0, max_starts_hr=4)
    ),
    "733-P-103": Asset(
        "1041535A", "Pompa Bio Solar", "FT Luwuk",
        MechanicalSpecs(power_kw=30.0, rpm_design=2900, mounting="Rigid"),
        ProtectionSettings(flc_amps=54.0, rated_volt=400.0, max_starts_hr=3)
    ),
    "706-P-203": Asset(
        "049-1611186", "Pompa LPG", "IT Makassar",
        MechanicalSpecs(power_kw=15.0, rpm_design=2955, mounting="Rigid"),
        ProtectionSettings(flc_amps=28.5, rated_volt=380.0, max_starts_hr=3)
    )
}

# ==========================================
# 3. LOGIC ENGINES
# ==========================================

class ElectricalEngine:
    def __init__(self, settings: ProtectionSettings):
        self.s = settings
        self.flags = []

    def analyze(self, v_in: list, i_in: list, i_g: float, starts: int, temp: float, status: str):
        self.flags = []
        v1, v2, v3 = v_in
        i1, i2, i3 = i_in
        is_starting = (status == "Starting")
        
        # 1. Voltage Check
        avg_v = np.mean([v1, v2, v3])
        if avg_v < (self.s.rated_volt * self.s.pickup_27):
            self.flags.append(f"TRIP {ANSI.UV_27}: Voltage {avg_v:.1f}V < Limit")
        elif avg_v > (self.s.rated_volt * self.s.pickup_59):
            self.flags.append(f"TRIP {ANSI.OV_59}: Voltage {avg_v:.1f}V > Limit")

        # 2. Current Check
        max_i = max(i1, i2, i3)
        avg_i = np.mean([i1, i2, i3])
        
        if is_starting:
            if max_i > (self.s.flc_amps * self.s.pickup_50):
                 self.flags.append(f"TRIP {ANSI.LR_50LR}: Starting Current {max_i:.1f}A too high")
        else:
            if max_i > (self.s.flc_amps * self.s.pickup_51):
                self.flags.append(f"TRIP {ANSI.TOC_51}: Overload {max_i:.1f}A detected")
            elif avg_i < (self.s.flc_amps * self.s.pickup_37) and avg_i > 1.0:
                self.flags.append(f"ALARM {ANSI.UC_37}: Dry Run / Underload {avg_i:.1f}A")

        # 3. Unbalance & Ground
        if avg_i > 0:
            max_dev = max(abs(i - avg_i) for i in [i1, i2, i3])
            unbal_pct = (max_dev / avg_i) * 100
            if unbal_pct > Limits.UNBALANCE_TRIP:
                self.flags.append(f"TRIP {ANSI.UB_46}: Current Unbalance {unbal_pct:.1f}%")
            elif unbal_pct > Limits.UNBALANCE_ALARM:
                self.flags.append(f"ALARM {ANSI.UB_46}: Current Unbalance {unbal_pct:.1f}%")
        else:
            unbal_pct = 0.0

        if i_g > self.s.pickup_50n:
            self.flags.append(f"TRIP {ANSI.GF_50N}: Ground Fault {i_g:.2f}A detected")

        # 4. Thermal & Stats
        if starts > self.s.max_starts_hr:
            self.flags.append(f"BLOCK {ANSI.ST_66}: {starts} Starts/Hr Exceeded")
        if temp > 130:
            self.flags.append(f"TRIP {ANSI.TH_49}: Winding Overheat {temp}°C")

        return self.flags, unbal_pct

class MechanicalEngine:
    @staticmethod
    def get_iso_status(val: float) -> Tuple[ISOZone, str]:
        limits = Limits.ISO_CLASS_II
        if val <= limits[0]: return ISOZone.A, "#2ecc71"
        elif val <= limits[1]: return ISOZone.B, "#f1c40f"
        elif val <= limits[2]: return ISOZone.C, "#e67e22"
        else: return ISOZone.D, "#e74c3c"

    @staticmethod
    def analyze_root_cause(readings: List[VibrationReading], warning_limit: float) -> List[str]:
        causes = []
        problem_points = [r for r in readings if r.value > warning_limit]
        
        if not problem_points: return []

        if any(r.axis == "Axial" and r.value > warning_limit for r in problem_points):
            causes.append("🔴 **MISALIGNMENT:** Vibrasi dominan di arah Axial (Cek Kopling).")
        
        high_horiz = [r for r in problem_points if r.axis == "Horizontal"]
        high_axial = [r for r in problem_points if r.axis == "Axial"]
        
        if high_horiz and not high_axial:
            causes.append("🟠 **UNBALANCE:** Vibrasi dominan di arah Radial (Cek Impeller/Rotor).")

        if any(r.axis == "Vertical" and r.value > warning_limit for r in problem_points):
             causes.append("🔧 **MECHANICAL LOOSENESS:** Vibrasi tinggi di arah Vertikal (Cek Baut Pondasi).")

        return list(set(causes))

class CommissioningEngine:
    @staticmethod
    def check_installation(soft_foot: float, v_offset: float, h_offset: float) -> List[str]:
        issues = []
        if soft_foot > Limits.MAX_SOFT_FOOT:
            issues.append(f"❌ REJECT: Soft Foot {soft_foot}mm > {Limits.MAX_SOFT_FOOT}mm")
        
        max_align = max(abs(v_offset), abs(h_offset))
        if max_align > Limits.ALIGNMENT_TOLERANCE:
             issues.append(f"❌ REJECT: Alignment Offset {max_align}mm > {Limits.ALIGNMENT_TOLERANCE}mm")
             
        if not issues:
            return ["✅ ACCEPTED: Installation within API 686 tolerances."]
        return issues

# ==========================================
# 4. STREAMLIT FRONTEND
# ==========================================
def main():
    st.set_page_config(page_title="Industrial Reliability Suite", layout="wide", page_icon="🏭")
    
    st.title("🛡️ Digital Reliability & Protection Dashboard")
    st.markdown("Integrated Mechanical (ISO/API) & Electrical (ANSI/IEEE) Analysis System")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ Asset Selection")
        selected_key = st.selectbox("Choose Asset Tag:", list(ASSETS_DB.keys()))
        asset = ASSETS_DB[selected_key]
        
        st.info(f"""
        **Asset Profile:**
        \n🏷️ **Tag:** `{asset.tag}`
        \n📍 **Loc:** `{asset.loc}`
        \n⚡ **Elec:** {asset.elec.flc_amps}A / {asset.elec.rated_volt}V
        \n🌊 **Mech:** {asset.mech.power_kw}kW / {asset.mech.rpm_design}RPM
        """)
        st.divider()
        st.caption("Standards: ISO 10816-3, API 686, IEEE C37.2")

    tab_vib, tab_elec, tab_comm = st.tabs([
        "🌊 Mechanical & Vibration (ISO)", 
        "⚡ Electrical Protection (ANSI)",
        "🚀 Commissioning (API 686)"
    ])

    # ==========================================
    # TAB 1: MECHANICAL VIBRATION
    # ==========================================
    with tab_vib:
        st.subheader(f"Vibration Diagnostics: {asset.name}")
        
        # Mulai Form Vibrasi
        with st.form("vib_input_form"):
            col_m, col_p = st.columns(2)
            
            # Menggunakan float() pada value default untuk menghindari MixedNumericTypesError
            def v_in(label): return st.number_input(label, min_value=0.0, max_value=50.0, value=0.5, step=0.01)

            with col_m:
                st.markdown("#### ⚡ MOTOR (Driver)")
                c1, c2, c3 = st.columns(3)
                with c1: m_nde_h = v_in("NDE Horiz")
                with c2: m_nde_v = v_in("NDE Vert")
                with c3: m_nde_a = v_in("NDE Axial")
                st.markdown("---")
                c4, c5, c6 = st.columns(3)
                with c4: m_de_h = v_in("DE Horiz")
                with c5: m_de_v = v_in("DE Vert")
                with c6: m_de_a = v_in("DE Axial")

            with col_p:
                st.markdown("#### 💧 POMPA (Driven)")
                c7, c8, c9 = st.columns(3)
                with c7: p_de_h = v_in("Pump DE Horiz")
                with c8: p_de_v = v_in("Pump DE Vert")
                with c9: p_de_a = v_in("Pump DE Axial")
                st.markdown("---")
                c10, c11, c12 = st.columns(3)
                with c10: p_nde_h = v_in("Pump NDE Horiz")
                with c11: p_nde_v = v_in("Pump NDE Vert")
                with c12: p_nde_a = v_in("Pump NDE Axial")

            st.markdown("#### Parameter Operasi")
            co1, co2 = st.columns(2)
            with co1: 
                # Pastikan float
                temp_bear = st.number_input("Bearing Temp (°C)", min_value=0.0, max_value=150.0, value=60.0, step=0.1)
            with co2: 
                noise_chk = st.checkbox("Abnormal Noise Detected?")

            # TOMBOL SUBMIT ADA DI DALAM BLOK FORM (Indentasi Benar)
            submit_vib = st.form_submit_button("🔍 ANALYZE VIBRATION")

        # Logic Eksekusi Vibrasi (Di luar form block, tapi dieksekusi jika tombol ditekan)
        if submit_vib:
            readings = [
                VibrationReading("Motor NDE", "Horizontal", m_nde_h),
                VibrationReading("Motor NDE", "Vertical", m_nde_v),
                VibrationReading("Motor NDE", "Axial", m_nde_a),
                VibrationReading("Motor DE", "Horizontal", m_de_h),
                VibrationReading("Motor DE", "Vertical", m_de_v),
                VibrationReading("Motor DE", "Axial", m_de_a),
                VibrationReading("Pump DE", "Horizontal", p_de_h),
                VibrationReading("Pump DE", "Vertical", p_de_v),
                VibrationReading("Pump DE", "Axial", p_de_a),
                VibrationReading("Pump NDE", "Horizontal", p_nde_h),
                VibrationReading("Pump NDE", "Vertical", p_nde_v),
                VibrationReading("Pump NDE", "Axial", p_nde_a),
            ]
            
            max_reading = max(readings, key=lambda x: x.value)
            iso_zone, color_hex = MechanicalEngine.get_iso_status(max_reading.value)
            
            roots = MechanicalEngine.analyze_root_cause(readings, warning_limit=Limits.ISO_CLASS_II[1])
            if temp_bear > asset.mech.bearing_temp_limit:
                roots.append(f"🔥 **OVERHEAT:** Bearing Temp {temp_bear}°C > {asset.mech.bearing_temp_limit}°C")
            if noise_chk:
                roots.append("🔊 **NOISE:** Indikasi kerusakan fisik / kavitasi.")

            st.divider()
            d1, d2 = st.columns([1, 2])
            
            with d1:
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number", value = max_reading.value,
                    title = {'text': f"Max Severity ({iso_zone.name})"},
                    gauge = {
                        'axis': {'range': [0, 15]},
                        'bar': {'color': "black"},
                        'steps': [
                            {'range': [0, 1.12], 'color': "#2ecc71"},
                            {'range': [1.12, 2.80], 'color': "#f1c40f"},
                            {'range': [2.80, 7.10], 'color': "#e67e22"},
                            {'range': [7.10, 15], 'color': "#e74c3c"}
                        ],
                        'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': max_reading.value}
                    }
                ))
                fig.update_layout(height=250, margin=dict(l=20,r=20,t=30,b=20))
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📍 Location: {max_reading.location} - {max_reading.axis}")

            with d2:
                if iso_zone == ISOZone.A: st.success(f"### {iso_zone.value}")
                elif iso_zone == ISOZone.B: st.warning(f"### {iso_zone.value}")
                elif iso_zone == ISOZone.C: st.error(f"### {iso_zone.value}")
                else: st.error(f"### 🚨 {iso_zone.value}")

                st.markdown("#### 🧠 AI Root Cause Analysis:")
                if roots:
                    for r in roots: st.write(f"- {r}")
                else:
                    st.write("- Pola vibrasi normal. Tidak ada indikasi kerusakan spesifik.")

    # ==========================================
    # TAB 2: ELECTRICAL PROTECTION
    # ==========================================
    with tab_elec:
        st.subheader(f"Protection Relay Simulation: {asset.name}")
        
        # Mulai Form Electrical
        with st.form("elec_input"):
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                st.markdown("### ⚡ Voltage (V)")
                # FIX ERROR 1: Cast float(asset.elec.rated_volt) agar tidak clash dengan 0.0
                v_def = float(asset.elec.rated_volt)
                v1 = st.number_input("V L1-L2", min_value=0.0, max_value=1000.0, value=v_def, step=0.1)
                v2 = st.number_input("V L2-L3", min_value=0.0, max_value=1000.0, value=v_def, step=0.1)
                v3 = st.number_input("V L3-L1", min_value=0.0, max_value=1000.0, value=v_def, step=0.1)
            with ec2:
                st.markdown("### 🔌 Current (A)")
                # FIX ERROR: Cast float
                def_curr = float(asset.elec.flc_amps * 0.8)
                i1 = st.number_input("I Phase 1", min_value=0.0, max_value=1000.0, value=def_curr, step=0.1)
                i2 = st.number_input("I Phase 2", min_value=0.0, max_value=1000.0, value=def_curr, step=0.1)
                i3 = st.number_input("I Phase 3", min_value=0.0, max_value=1000.0, value=def_curr, step=0.1)
                ig = st.number_input("I Ground (Zero Seq)", min_value=0.0, max_value=100.0, value=0.0, step=0.01)
            with ec3:
                st.markdown("### ⚙️ Stats")
                # Int inputs are safe here
                starts = st.number_input("Starts/Hour", min_value=0, max_value=10, value=1, step=1)
                temp_wind = st.number_input("Winding Temp (°C)", min_value=20.0, max_value=200.0, value=65.0, step=0.1)
                status_m = st.radio("Motor State", ["Running", "Starting", "Stopped"])

            # FIX ERROR 2: Tombol Submit di dalam form
            submit_elec = st.form_submit_button("🔍 ANALYZE PROTECTION")

        if submit_elec:
            engine = ElectricalEngine(asset.elec)
            logs, unbal = engine.analyze([v1,v2,v3], [i1,i2,i3], ig, starts, temp_wind, status_m)

            st.divider()
            st.markdown("#### Relay Status Indicators (ANSI Device Codes)")
            
            def check_code(code_str):
                return "red" if any(code_str.split(' - ')[0] in s for s in logs) else "green"

            cols = st.columns(4)
            ansi_list = [ANSI.UV_27, ANSI.OV_59, ANSI.IOC_50, ANSI.TOC_51, 
                         ANSI.UC_37, ANSI.UB_46, ANSI.GF_50N, ANSI.TH_49]
            
            for i, code in enumerate(ansi_list):
                color = check_code(code)
                with cols[i % 4]:
                    st.markdown(f"""
                    <div style="
                        border: 2px solid {color}; border-radius: 5px; padding: 10px;
                        text-align: center; margin-bottom: 10px;
                        background-color: {'rgba(255,0,0,0.1)' if color=='red' else 'rgba(0,255,0,0.1)'};
                    ">
                        <strong>{code.split(' - ')[0]}</strong><br>
                        <span style="font-size:0.7em">{code.split(' - ')[1]}</span>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()
            el_c1, el_c2 = st.columns([2,1])
            
            with el_c1:
                if logs:
                    st.error("### 🚨 ACTIVE FAULTS DETECTED:")
                    for l in logs: st.write(f"❌ {l}")
                else:
                    st.success("### ✅ SYSTEM HEALTHY")
                    st.write("Semua parameter listrik dalam batas aman.")

            with el_c2:
                st.markdown("**Electrical Metrics:**")
                st.metric("Avg Voltage", f"{np.mean([v1,v2,v3]):.1f} V")
                st.metric("Avg Current", f"{np.mean([i1,i2,i3]):.1f} A")
                st.metric("Unbalance", f"{unbal:.2f} %", delta_color="inverse", 
                          delta="High" if unbal > Limits.UNBALANCE_ALARM else "Normal")

            if logs:
                st.info("""
                **Standard Operating Procedure (SOP) saat Trip:**
                1. 🛑 **JANGAN RESET** relay sebelum inspeksi visual.
                2. 🔍 Cek fisik panel (bau hangus/flashover).
                3. 📥 Download **Fault Record** dari relay untuk investigasi.
                """)

    # ==========================================
    # TAB 3: COMMISSIONING
    # ==========================================
    with tab_comm:
        st.subheader("Site Acceptance Test (API 686)")
        
        # Untuk commissioning, kita gunakan Form juga agar konsisten
        with st.form("comm_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("#### 1. Soft Foot Check")
                soft_foot_val = st.number_input("Max Soft Foot (mm)", 0.00, 1.00, 0.00, 0.01)
                st.caption(f"Limit API 686: {Limits.MAX_SOFT_FOOT} mm")
                
            with col_c2:
                st.markdown("#### 2. Alignment Check")
                v_off = st.number_input("Vertical Offset (mm)", -1.0, 1.0, 0.00, 0.01)
                h_off = st.number_input("Horizontal Offset (mm)", -1.0, 1.0, 0.00, 0.01)
                st.caption(f"Limit Tolerance: {Limits.ALIGNMENT_TOLERANCE} mm")

            chk_grout = st.checkbox("Grouting Cured & Sound?")
            chk_pipe = st.checkbox("Pipe Strain Free?")
            
            submit_comm = st.form_submit_button("✅ VALIDATE INSTALLATION")
        
        if submit_comm:
            comm_res = CommissioningEngine.check_installation(soft_foot_val, v_off, h_off)
            
            if not chk_grout: comm_res.append("❌ Grouting check pending.")
            if not chk_pipe: comm_res.append("❌ Pipe strain check pending.")
            
            st.divider()
            if any("❌" in s for s in comm_res):
                st.error("### ⛔ COMMISSIONING FAILED")
                for r in comm_res: st.write(r)
            else:
                st.success("### 🎉 COMMISSIONING PASSED")
                st.write("Instalasi memenuhi standar API 686. Siap untuk Start-up.")

if __name__ == "__main__":
    main()
