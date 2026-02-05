import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from enum import Enum

# ==========================================
# 1. STANDARDS LIBRARY (HARD CODES)
# ==========================================
class StandardLimit:
    # IEC 60034-1: Rotating Electrical Machines
    MAX_CURRENT_UNBALANCE_PCT = 5.0  # Industry practice (NEMA MG1 allows 10%, IEC stricter)
    MAX_VOLTAGE_UNBALANCE_PCT = 1.0  # IEC 60034-1
    
    # IEEE 43: Insulation Resistance
    MIN_PI_CLASS_F = 2.0  # Polarization Index min for Class F insulation
    MIN_IR_1MIN = 100.0   # M-Ohm (Conservative limit for 400V motors)

    # API 610: Centrifugal Pumps
    # Vibration limits based on Region (Preferred vs Allowable)
    API_VIB_PREFERRED = 3.0  # mm/s RMS
    API_VIB_ALLOWABLE = 5.0  # mm/s RMS (Site Acceptance Limit)

# ==========================================
# 2. DATA STRUCTURES (INDUSTRIAL GRADE)
# ==========================================
@dataclass
class ElectricalSpecs:
    rated_voltage: float  # Volts
    rated_current: float  # Amps (FLA)
    phase: int = 3
    insulation_class: str = "F"
    service_factor: float = 1.15

@dataclass
class MechanicalSpecs:
    power_kw: float
    rpm_design: int
    pump_type: str  # 'Overhung', 'Between Bearings', etc.
    coupling_type: str
    api_plan: str   # e.g., "Plan 53A"

@dataclass
class Asset:
    tag: str
    name: str
    location: str
    mech: MechanicalSpecs
    elec: ElectricalSpecs
    commissioning_date: str

# Database Aset (Mockup - Bisa diganti SQL Database)
ASSETS_DB = {
    "P-02": Asset(
        "0459599", "Pompa Pertalite", "FT Moutong",
        MechanicalSpecs(18.5, 2900, "Overhung", "Flexible", "Plan 11"),
        ElectricalSpecs(380, 35.5, 3, "F", 1.15),
        "2004-01-01"
    ),
    "733-P-103": Asset(
        "1041535A", "Pompa Bio Solar", "FT Luwuk",
        MechanicalSpecs(30.0, 2900, "Overhung", "Spacer", "Plan 11/52"),
        ElectricalSpecs(400, 54.0, 3, "F", 1.15),
        "2014-06-20"
    ),
    "706-P-203": Asset(
        "049-1611186", "Pompa LPG", "IT Makassar",
        MechanicalSpecs(15.0, 2955, "Overhung", "Magnetic", "Plan 53B"),
        ElectricalSpecs(380, 28.5, 3, "F", 1.0),
        "2017-01-19"
    )
}

# ==========================================
# 3. CALCULATION ENGINES (LOGIC LAYER)
# ==========================================
class ElectricalAnalyzer:
    @staticmethod
    def calculate_unbalance(ph1: float, ph2: float, ph3: float) -> tuple[float, float, str]:
        """
        Menghitung Unbalance sesuai NEMA MG-1 / IEC.
        Formula: Max Deviation from Avg / Avg * 100
        """
        avg = (ph1 + ph2 + ph3) / 3
        if avg == 0: return 0.0, 0.0, "OFF"
        
        max_dev = max(abs(ph1 - avg), abs(ph2 - avg), abs(ph3 - avg))
        unbalance_pct = (max_dev / avg) * 100
        
        status = "NORMAL"
        if unbalance_pct > StandardLimit.MAX_CURRENT_UNBALANCE_PCT:
            status = "CRITICAL (High Unbalance)"
        elif unbalance_pct > (StandardLimit.MAX_CURRENT_UNBALANCE_PCT / 2):
            status = "WARNING"
            
        return avg, unbalance_pct, status

    @staticmethod
    def analyze_insulation(ir_1min: float, ir_10min: float) -> tuple[float, str]:
        """
        Menghitung Polarization Index (PI) sesuai IEEE 43.
        PI = R_10min / R_1min
        """
        if ir_1min == 0: return 0.0, "INVALID"
        pi_val = ir_10min / ir_1min
        
        if pi_val >= StandardLimit.MIN_PI_CLASS_F:
            return pi_val, "PASS (Good Insulation)"
        elif pi_val >= 1.5:
            return pi_val, "WARNING (Aging Insulation)"
        else:
            return pi_val, "FAIL (Brittle/Wet Insulation)"

class CommissioningValidator:
    """
    Validasi berdasarkan API 686 (Installation) & API 610 (Performance).
    """
    @staticmethod
    def check_alignment(offset_vertical: float, offset_horizontal: float, rpm: int) -> str:
        # Toleransi umum alignment (rule of thumb based on API 686 for 3000 RPM)
        # 0.05 mm untuk offset
        limit = 0.05 
        max_offset = max(abs(offset_vertical), abs(offset_horizontal))
        
        if max_offset <= limit:
            return "ACCEPTABLE (Within API 686 Tolerance)"
        else:
            return f"REJECTED (Offset {max_offset}mm > Limit {limit}mm)"

# ==========================================
# 4. FRONTEND (STREAMLIT UI)
# ==========================================
def main():
    st.set_page_config(page_title="Industrial Reliability Suite", layout="wide", page_icon="🏭")
    
    # --- Sidebar ---
    st.sidebar.title("🏭 Reliability Suite")
    st.sidebar.markdown("**Standard Compliance:**\n- API 610 / 686\n- ISO 10816-3\n- IEC 60034-1 / IEEE 43")
    
    selected_tag = st.sidebar.selectbox("Select Asset Tag:", list(ASSETS_DB.keys()))
    asset = ASSETS_DB[selected_tag]
    
    # Asset Info Card
    with st.sidebar:
        st.info(f"""
        **{asset.name}**
        \n📍 {asset.location}
        \n⚡ {asset.elec.rated_voltage}V / {asset.elec.rated_current}A
        \n⚙️ {asset.mech.power_kw} kW / {asset.mech.rpm_design} RPM
        """)
        
    # --- Main Dashboard ---
    st.title(f"Dashboard Pengujian: {asset.tag}")
    
    # Tabs Structure
    tab_comm, tab_elec, tab_vib = st.tabs([
        "🚀 Commissioning (API 686)", 
        "⚡ Electrical Analysis (IEC/IEEE)", 
        "🌊 Vibration & Mechanical (ISO/API)"
    ])

    # === TAB 1: COMMISSIONING (API 686) ===
    with tab_comm:
        st.header("Site Acceptance Test (SAT) Protocol")
        st.caption("Referensi: API 686 Chapter 7 - Installation & Commissioning")
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Shaft Alignment Check")
            align_v = st.number_input("Vertical Offset (mm):", -1.0, 1.0, 0.00, step=0.01)
            align_h = st.number_input("Horizontal Offset (mm):", -1.0, 1.0, 0.00, step=0.01)
            align_status = CommissioningValidator.check_alignment(align_v, align_h, asset.mech.rpm_design)
            
            if "REJECTED" in align_status:
                st.error(align_status)
            else:
                st.success(align_status)

        with c2:
            st.subheader("2. Soft Foot Check")
            soft_foot = st.number_input("Max Soft Foot (mm):", 0.00, 1.00, 0.00, step=0.01)
            if soft_foot > 0.05: # API 686 limit
                st.error(f"FAIL: Soft foot {soft_foot}mm > 0.05mm (API 686 Limit)")
            else:
                st.success("PASS: Soft foot within tolerance.")

        st.divider()
        st.subheader("3. Pre-Start Checklist (API 686)")
        chk_1 = st.checkbox("Grouting cured & sound (Ketuk pondasi)")
        chk_2 = st.checkbox("Pipe Strain Free (Flange sejajar tanpa paksaan)")
        chk_3 = st.checkbox(f"Auxiliary Systems (Lube Oil/Seal {asset.mech.api_plan}) Ready")
        chk_4 = st.checkbox("Coupling Guard Installed")
        
        if chk_1 and chk_2 and chk_3 and chk_4:
            st.success("✅ READY FOR START-UP")
        else:
            st.warning("⚠️ Pending Checklist Items")

    # === TAB 2: ELECTRICAL (IEC/IEEE) ===
    with tab_elec:
        st.header("Electrical Health Assessment")
        
        # Section A: Power Quality
        st.markdown("### A. Power Analysis (IEC 60034-1)")
        ce1, ce2, ce3, ce4 = st.columns(4)
        with ce1: l1 = st.number_input("Current L1 (Amp):", 0.0, 500.0, asset.elec.rated_current)
        with ce2: l2 = st.number_input("Current L2 (Amp):", 0.0, 500.0, asset.elec.rated_current)
        with ce3: l3 = st.number_input("Current L3 (Amp):", 0.0, 500.0, asset.elec.rated_current)
        
        avg_amp, unbal_pct, amp_status = ElectricalAnalyzer.calculate_unbalance(l1, l2, l3)
        
        with ce4:
            st.metric("Avg Current", f"{avg_amp:.1f} A")
            st.metric("Unbalance", f"{unbal_pct:.2f} %")
        
        # Load Calculation
        load_pct = (avg_amp / asset.elec.rated_current) * 100
        st.progress(min(load_pct/150, 1.0), text=f"Motor Load: {load_pct:.1f}% of FLA")
        
        if load_pct > 100 * asset.elec.service_factor:
            st.error(f"🚨 OVERLOAD: Load melebihi Service Factor ({asset.elec.service_factor})")
        elif "CRITICAL" in amp_status:
            st.error(f"🚨 {amp_status}: Cek koneksi kabel atau lilitan stator (IEC Limit < {StandardLimit.MAX_CURRENT_UNBALANCE_PCT}%)")
        elif "WARNING" in amp_status:
            st.warning(f"⚠️ {amp_status}: Unbalance terdeteksi.")
        else:
            st.success("✅ Power Condition Optimal")

        # Section B: Insulation Resistance (IEEE 43)
        st.divider()
        st.markdown("### B. Insulation Resistance (Megger Test - IEEE 43)")
        ci1, ci2 = st.columns(2)
        with ci1: ir_1 = st.number_input("IR @ 1 Min (MΩ):", 0.0, 5000.0, 200.0)
        with ci2: ir_10 = st.number_input("IR @ 10 Min (MΩ):", 0.0, 5000.0, 600.0)
        
        pi_val, pi_msg = ElectricalAnalyzer.analyze_insulation(ir_1, ir_10)
        
        c_pi1, c_pi2 = st.columns([1,3])
        with c_pi1:
            st.metric("Polarization Index (PI)", f"{pi_val:.2f}")
        with c_pi2:
            if "PASS" in pi_msg: st.success(pi_msg)
            elif "WARNING" in pi_msg: st.warning(pi_msg)
            else: st.error(pi_msg)
            st.caption("*IEEE 43 Std: PI > 2.0 diperlukan untuk Class F Insulation*")

    # === TAB 3: VIBRATION (ISO/API) ===
    with tab_vib:
        st.header("Vibration Analysis (API 610 / ISO 10816)")
        st.info("NOTE: Sistem menggunakan nilai MAKSIMUM dari setiap titik ukur untuk menentukan keparahan, bukan rata-rata.")
        
        # Input Grid yang ringkas
        with st.form("vib_form"):
            col_m, col_p = st.columns(2)
            with col_m:
                st.markdown("#### ⚡ Motor (Driver)")
                m_de = st.number_input("Motor DE Max (mm/s):", 0.0, 50.0, 0.5)
                m_nde = st.number_input("Motor NDE Max (mm/s):", 0.0, 50.0, 0.5)
            with col_p:
                st.markdown("#### 💧 Pompa (Driven)")
                p_de = st.number_input("Pump DE Max (mm/s):", 0.0, 50.0, 0.5)
                p_nde = st.number_input("Pump NDE Max (mm/s):", 0.0, 50.0, 0.5)
            
            submit_vib = st.form_submit_button("Analisa Vibrasi")
            
        if submit_vib:
            # Logic Max Value
            max_v = max(m_de, m_nde, p_de, p_nde)
            
            # API 610 Logic for Commissioning
            if max_v <= StandardLimit.API_VIB_PREFERRED:
                status = "PREFERRED OPERATING REGION"
                color = "green"
            elif max_v <= StandardLimit.API_VIB_ALLOWABLE:
                status = "ALLOWABLE OPERATING REGION (Acceptable for SAT)"
                color = "orange"
            else:
                status = "REJECTED / OUTSIDE LIMITS"
                color = "red"
                
            # Gauge Visualization
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = max_v,
                title = {'text': f"Max Vibration ({status})"},
                gauge = {
                    'axis': {'range': [0, 10]},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, 3.0], 'color': "#2ecc71"},
                        {'range': [3.0, 5.0], 'color': "#f1c40f"},
                        {'range': [5.0, 10.0], 'color': "#e74c3c"}
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': max_v}
                }
            ))
            st.plotly_chart(fig, use_container_width=True)
            
            if color == "red":
                st.error("🚨 VIBRATION REJECTED: Cek Alignment, Soft Foot, atau Unbalance segera.")

if __name__ == "__main__":
    main()
