import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# ==========================================
# 1. STANDARDS & ANSI CODES LIBRARY
# ==========================================
class ANSI:
    """
    IEEE C37.2 Standard Device Numbers
    Digunakan untuk referensi Proteksi Elektrikal Migas.
    """
    UV_27 = "27 - Undervoltage"
    UC_37 = "37 - Undercurrent (Dry Run)"
    UB_46 = "46 - Current Unbalance / Negative Seq"
    TH_49 = "49 - Thermal Overload"
    IOC_50 = "50 - Instantaneous Overcurrent"
    GF_50N = "50N/51N - Ground Fault"
    LR_50LR = "50LR - Locked Rotor"
    TOC_51 = "51 - Time Overcurrent"
    OV_59 = "59 - Overvoltage"
    ST_66 = "66 - Start Limitation (Starts/Hour)"

class Limits:
    # IEC 60034-1 & NEMA MG-1 Limits
    VOLTAGE_TOLERANCE_PCT = 10.0  # +/- 10%
    FREQ_TOLERANCE_PCT = 5.0
    UNBALANCE_ALARM = 2.0  # %
    UNBALANCE_TRIP = 5.0   # %
    GROUND_FAULT_PICKUP = 0.5 # Amperes (Default setting, usually low)

# ==========================================
# 2. INDUSTRIAL DATA STRUCTURES
# ==========================================
@dataclass
class ProtectionSettings:
    """Setting Relay Proteksi (Bisa disesuaikan dengan datasheet motor)"""
    flc_amps: float         # Full Load Current (Amper Nominal)
    rated_volt: float       # Voltage Nominal (e.g., 380V)
    
    # Settings (Thresholds)
    pickup_51: float = 1.10  # 110% of FLC for Overcurrent
    pickup_50: float = 6.00  # 600% of FLC for Short Circuit
    pickup_27: float = 0.90  # 90% Voltage (Undervoltage)
    pickup_59: float = 1.10  # 110% Voltage (Overvoltage)
    pickup_37: float = 0.40  # 40% FLC (Undercurrent/Dry Run)
    pickup_50n: float = 1.0  # 1 Ampere Ground Fault Limit
    max_starts_hr: int = 3   # Max start per jam (ANSI 66)

@dataclass
class Asset:
    tag: str
    name: str
    loc: str
    protection: ProtectionSettings

# Database Aset Dummy
ASSETS = {
    "P-02 (FT Moutong)": Asset(
        "0459599", "Pompa Pertalite", "FT Moutong",
        ProtectionSettings(flc_amps=35.5, rated_volt=380, max_starts_hr=4)
    ),
    "733-P-103 (FT Luwuk)": Asset(
        "1041535A", "Pompa Bio Solar", "FT Luwuk",
        ProtectionSettings(flc_amps=54.0, rated_volt=400, max_starts_hr=3)
    )
}

# ==========================================
# 3. CORE LOGIC: DIGITAL RELAY SIMULATOR
# ==========================================
class DigitalRelay:
    """
    Simulasi Logic Protection Relay (Multilin/Sepam).
    Menerima input raw, mengeluarkan Status Trip/Alarm sesuai ANSI Code.
    """
    def __init__(self, settings: ProtectionSettings):
        self.s = settings
        self.flags = [] # Menyimpan log trip

    def check_voltage(self, v_l1, v_l2, v_l3):
        avg_v = (v_l1 + v_l2 + v_l3) / 3
        
        # ANSI 27: Undervoltage
        if avg_v < (self.s.rated_volt * self.s.pickup_27):
            self.flags.append(f"TRIP {ANSI.UV_27}: {avg_v:.1f}V < Limit {self.s.rated_volt * self.s.pickup_27:.1f}V")
            return "TRIP", "red"
            
        # ANSI 59: Overvoltage
        if avg_v > (self.s.rated_volt * self.s.pickup_59):
            self.flags.append(f"TRIP {ANSI.OV_59}: {avg_v:.1f}V > Limit {self.s.rated_volt * self.s.pickup_59:.1f}V")
            return "TRIP", "red"
            
        return "NORMAL", "green"

    def check_current(self, i_l1, i_l2, i_l3, is_starting=False):
        max_i = max(i_l1, i_l2, i_l3)
        avg_i = (i_l1 + i_l2 + i_l3) / 3

        # ANSI 50/51: Overcurrent
        if is_starting:
            # ANSI 50LR: Locked Rotor Check (Jika start current diam lama di > 6x FLA)
            if max_i > (self.s.flc_amps * self.s.pickup_50):
                self.flags.append(f"TRIP {ANSI.LR_50LR} / {ANSI.IOC_50}: Current {max_i:.1f}A Detected")
                return "TRIP (LOCKED ROTOR)", "red"
        else:
            # Normal Running
            if max_i > (self.s.flc_amps * self.s.pickup_51):
                self.flags.append(f"TRIP {ANSI.TOC_51}: Overload {max_i:.1f}A > {self.s.flc_amps * self.s.pickup_51:.1f}A")
                return "TRIP (OVERLOAD)", "red"
        
        # ANSI 37: Undercurrent (Dry Run Protection)
        if avg_i < (self.s.flc_amps * self.s.pickup_37) and not is_starting and avg_i > 1.0:
            self.flags.append(f"ALARM {ANSI.UC_37}: Dry Run Detected ({avg_i:.1f}A)")
            return "ALARM (UNDERLOAD)", "orange"

        return "NORMAL", "green"

    def check_unbalance_ground(self, i_l1, i_l2, i_l3, i_g_measured=0.0):
        # ANSI 46: Current Unbalance / Negative Sequence
        avg_i = (i_l1 + i_l2 + i_l3) / 3
        if avg_i > 0:
            max_dev = max(abs(i_l1 - avg_i), abs(i_l2 - avg_i), abs(i_l3 - avg_i))
            unbal_pct = (max_dev / avg_i) * 100
            
            if unbal_pct > Limits.UNBALANCE_TRIP:
                self.flags.append(f"TRIP {ANSI.UB_46}: Unbalance {unbal_pct:.1f}%")
            elif unbal_pct > Limits.UNBALANCE_ALARM:
                self.flags.append(f"ALARM {ANSI.UB_46}: Unbalance {unbal_pct:.1f}%")

        # ANSI 50N/51N: Ground Fault
        # 1. Calculation (Residual)
        i_residual = abs(i_l1 + i_l2 + i_l3) # Simplified vector sum approx for scalar input
        # Note: In real AC vectors, it's Vector Sum. Here we use Measured input if avail.
        
        check_val = i_g_measured if i_g_measured > 0 else 0.0
        
        if check_val > self.s.pickup_50n:
             self.flags.append(f"TRIP {ANSI.GF_50N}: Ground Current {check_val:.2f}A > {self.s.pickup_50n}A")

        return unbal_pct

    def check_thermal_stats(self, starts_last_hour, motor_temp):
        # ANSI 66: Start Limitation
        if starts_last_hour > self.s.max_starts_hr:
             self.flags.append(f"BLOCK {ANSI.ST_66}: {starts_last_hour} Starts/Hr > Max {self.s.max_starts_hr}")

        # ANSI 49: Thermal Overload (Temperature)
        if motor_temp > 130: # Class B/F Limit rough check
             self.flags.append(f"TRIP {ANSI.TH_49}: Winding Temp {motor_temp}°C")

    def get_diagnostics(self):
        if not self.flags:
            return "SYSTEM HEALTHY", "green", []
        else:
            return "PROTECTION TRIP/ALARM", "red", self.flags

# ==========================================
# 4. STREAMLIT UI IMPLEMENTATION
# ==========================================
def main():
    st.set_page_config(page_title="Industrial Protection Relay", layout="wide", page_icon="⚡")
    
    st.title("🛡️ Digital Reliability & Protection Dashboard")
    st.markdown("Electrical Protection System Simulation (ANSI/IEEE Std)")

    # Sidebar Config
    with st.sidebar:
        st.header("Asset Configuration")
        sel_asset = st.selectbox("Select Asset:", list(ASSETS.keys()))
        asset = ASSETS[sel_asset]
        
        st.info(f"""
        **Relay Settings ({asset.name})**
        \nRated Volts: {asset.protection.rated_volt} V
        \nFLA (In): {asset.protection.flc_amps} A
        \nANSI 50 Set: {asset.protection.pickup_50}x In
        \nANSI 51 Set: {asset.protection.pickup_51}x In
        \nANSI 66 Max: {asset.protection.max_starts_hr} Starts/Hr
        """)

    # --- MAIN INPUT FORM ---
    with st.form("protection_input"):
        st.subheader("📡 Live Data Injection (Simulated)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### ⚡ Voltage (V)")
            v1 = st.number_input("V L1-L2", value=float(asset.protection.rated_volt))
            v2 = st.number_input("V L2-L3", value=float(asset.protection.rated_volt))
            v3 = st.number_input("V L3-L1", value=float(asset.protection.rated_volt))
        
        with col2:
            st.markdown("### 🔌 Current (A)")
            i1 = st.number_input("I Phase 1", value=float(asset.protection.flc_amps * 0.8))
            i2 = st.number_input("I Phase 2", value=float(asset.protection.flc_amps * 0.8))
            i3 = st.number_input("I Phase 3", value=float(asset.protection.flc_amps * 0.8))
            ig = st.number_input("I Ground (Zero Seq)", value=0.0, step=0.1)

        with col3:
            st.markdown("### ⚙️ Operational Status")
            starts = st.number_input("Starts in Last Hour:", 0, 10, 1)
            temp = st.number_input("Winding Temp (°C):", 25.0, 180.0, 60.0)
            status_motor = st.radio("Motor Status:", ["Running", "Starting", "Stopped"])
        
        submit = st.form_submit_button("🔍 ANALYZE PROTECTION LOGIC")

    # --- LOGIC EXECUTION ---
    if submit:
        # Initialize Relay Simulator
        relay = DigitalRelay(asset.protection)
        
        # 1. Run Checks
        is_starting = (status_motor == "Starting")
        
        # Check Voltage (27, 59)
        volt_stat, volt_col = relay.check_voltage(v1, v2, v3)
        
        # Check Current (50, 51, 37, 50LR)
        curr_stat, curr_col = relay.check_current(i1, i2, i3, is_starting)
        
        # Check Unbalance & Ground (46, 50N)
        unbal_val = relay.check_unbalance_ground(i1, i2, i3, ig)
        
        # Check Thermal & Stats (49, 66)
        relay.check_thermal_stats(starts, temp)
        
        # Get Final Results
        final_status, final_color, logs = relay.get_diagnostics()

        # --- DISPLAY RESULTS (DASHBOARD) ---
        st.divider()
        st.header("📊 Protection Relay Output")
        
        # Top KPI Cards
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("System Voltage", f"{(v1+v2+v3)/3:.1f} V", delta_color="inverse", delta="Trip" if volt_col=="red" else "Normal")
        kpi2.metric("Max Current", f"{max(i1,i2,i3):.1f} A", delta_color="inverse", delta="Trip" if curr_col=="red" else "Normal")
        kpi3.metric("Unbalance (ANSI 46)", f"{unbal_val:.2f} %", delta_color="inverse", delta="High" if unbal_val > Limits.UNBALANCE_ALARM else "Normal")
        kpi4.metric("Thermal (ANSI 49)", f"{temp} °C", delta_color="inverse", delta="Overheat" if temp>130 else "Normal")

        # Visual Relay Flags (The Manager Request)
        st.subheader("Relay Flags (ANSI Codes)")
        
        # Grid visual for ANSI codes
        ansi_codes = {
            ANSI.UV_27: "red" if any("27" in s for s in logs) else "green",
            ANSI.OV_59: "red" if any("59" in s for s in logs) else "green",
            ANSI.IOC_50: "red" if any("50:" in s for s in logs) else "green",
            ANSI.TOC_51: "red" if any("51" in s for s in logs) else "green",
            ANSI.UC_37: "orange" if any("37" in s for s in logs) else "green",
            ANSI.UB_46: "orange" if any("46" in s for s in logs) else "green",
            ANSI.GF_50N: "red" if any("50N" in s for s in logs) else "green",
            ANSI.ST_66: "orange" if any("66" in s for s in logs) else "green",
        }

        # Create a visual grid of 'LEDs'
        cols = st.columns(4)
        for i, (code, color) in enumerate(ansi_codes.items()):
            with cols[i % 4]:
                st.markdown(f"""
                <div style="
                    border: 2px solid {color};
                    border-radius: 5px;
                    padding: 10px;
                    text-align: center;
                    background-color: {'rgba(255,0,0,0.1)' if color=='red' else 'rgba(0,255,0,0.1)'};
                ">
                    <strong>{code.split(' - ')[0]}</strong><br>
                    <span style="font-size:0.8em">{code.split(' - ')[1]}</span>
                </div>
                """, unsafe_allow_html=True)

        # Message Log Area
        st.divider()
        if logs:
            st.error("### 🚨 ACTIVE TRIPS / ALARMS:")
            for log in logs:
                st.write(f"❌ {log}")
            
            st.markdown("""
            **Rekomendasi Tindakan:**
            1. Cek fisik panel dan motor.
            2. Jangan reset relay sebelum penyebab ditemukan.
            3. Download rekaman gangguan (Fault Record).
            """)
        else:
            st.success("### ✅ SYSTEM HEALTHY - NO ACTIVE FAULTS")
            st.write("Semua parameter operasi berada dalam batas aman setting proteksi.")

if __name__ == "__main__":
    main()
