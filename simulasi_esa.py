import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# ==========================================
# 1. KONFIGURASI & STANDAR (The "Brain")
# ==========================================

class ISOZone(Enum):
    A = "GOOD (Zone A)"
    B = "SATISFACTORY (Zone B)"
    C = "UNSATISFACTORY (Zone C)"
    D = "UNACCEPTABLE (Zone D)"

@dataclass
class AssetData:
    tag: str
    name: str
    location: str
    power_kw: float
    rpm: int
    mounting: str = "Rigid"
    
    @property
    def machine_class(self) -> str:
        # Logika Penentuan Class ISO 10816-1
        # Class I: < 15 kW
        # Class II: 15 - 300 kW (Mayoritas Pompa Anda)
        # Class III: > 300 kW (Rigid)
        if self.power_kw <= 15: return "Class I"
        elif self.power_kw <= 300: return "Class II"
        else: return "Class III"

@dataclass
class VibrationReading:
    location: str  # e.g., "Motor DE"
    axis: str      # e.g., "Horizontal"
    value: float   # RMS mm/s

@dataclass
class DiagnosticResult:
    max_vibration: float
    max_location: str
    iso_zone: ISOZone
    color_code: str
    root_causes: List[str]
    recommendations: List[str]

class ReliabilityEngine:
    """
    Mesin Logika Utama. 
    Menggabungkan standar ISO 10816 (Severity) dan TKI C-017 (Root Cause).
    """
    
    # Limit Vibrasi ISO 10816-1 (Zone Boundary)
    # Format: [Limit A/B, Limit B/C, Limit C/D]
    ISO_LIMITS = {
        "Class I":  [0.71, 1.80, 4.50],
        "Class II": [1.12, 2.80, 7.10], # Standar TKI C-04 Anda
        "Class III":[1.80, 4.50, 11.20]
    }

    @staticmethod
    def get_zone(value: float, machine_class: str) -> tuple[ISOZone, str]:
        limits = ReliabilityEngine.ISO_LIMITS.get(machine_class, ReliabilityEngine.ISO_LIMITS["Class II"])
        
        if value <= limits[0]:
            return ISOZone.A, "#2ecc71" # Green
        elif value <= limits[1]:
            return ISOZone.B, "#f1c40f" # Yellow
        elif value <= limits[2]:
            return ISOZone.C, "#e67e22" # Orange
        else:
            return ISOZone.D, "#e74c3c" # Red

    @staticmethod
    def diagnose(readings: List[VibrationReading], machine_class: str, temp: float, visual_issues: List[str]) -> DiagnosticResult:
        # 1. Cari Nilai MAX (Worst Case Severity)
        max_reading = max(readings, key=lambda x: x.value)
        zone, color = ReliabilityEngine.get_zone(max_reading.value, machine_class)
        
        # 2. Analisa Root Cause (Algoritma TKI C-017)
        causes = []
        
        # Filter titik yang bermasalah saja (> Limit Zone B/Warning)
        warning_limit = ReliabilityEngine.ISO_LIMITS[machine_class][1] # 2.80 mm/s for Class II
        problematic_points = [r for r in readings if r.value > warning_limit]
        
        if not problematic_points and zone in [ISOZone.A, ISOZone.B]:
             causes.append("Kondisi mesin normal. Tidak ada pola kerusakan dominan.")
        else:
            # Pola 1: Misalignment (Dominan di Axial)
            high_axial = any(r.value > warning_limit and r.axis == "Axial" for r in problematic_points)
            if high_axial:
                causes.append("🔴 **MISALIGNMENT (Indikasi Kuat):** Terdeteksi vibrasi tinggi pada arah Axial. Cek kelurusan kopling.")

            # Pola 2: Unbalance (Dominan di Radial - Horizontal)
            high_horiz = any(r.value > warning_limit and r.axis == "Horizontal" for r in problematic_points)
            if high_horiz and not high_axial:
                causes.append("🟠 **UNBALANCE / LOOSENESS:** Vibrasi dominan di arah Radial. Cek kekencangan baut atau kebersihan impeller.")

            # Pola 3: Masalah Mekanis Pompa
            pump_issue = any("Pump" in r.location and r.value > warning_limit for r in problematic_points)
            if pump_issue:
                causes.append("🔵 **PUMP END ISSUE:** Gangguan pada sisi pompa. Cek Bearing Pompa atau indikasi Kavitasi.")

        # 3. Analisa Tambahan (Suhu & Visual)
        if temp > 85: # Limit TKI C-04
            causes.append(f"🔥 **OVERHEAT:** Suhu bearing {temp}°C melebihi batas 85°C.")
        
        for issue in visual_issues:
            causes.append(f"👁️ **VISUAL:** {issue}")

        # 4. Generate Rekomendasi
        recs = []
        if zone == ISOZone.D:
            recs.append("STOP OPERASI SEGERA. Risiko kerusakan fatal.")
            recs.append("Lakukan pengecekan poros dan bearing secara fisik.")
        elif zone == ISOZone.C:
            recs.append("Jadwalkan perbaikan dalam waktu < 7 hari.")
            recs.append("Pantau vibrasi setiap hari.")
        else:
            recs.append("Lanjutkan pemeliharaan rutin sesuai TKI C-04.")

        return DiagnosticResult(
            max_vibration=max_reading.value,
            max_location=f"{max_reading.location} - {max_reading.axis}",
            iso_zone=zone,
            color_code=color,
            root_causes=causes,
            recommendations=recs
        )

# ==========================================
# 2. DATABASE ASET (Mockup Data)
# ==========================================
ASSETS_DB = {
    "P-02": AssetData("0459599", "Pompa Pertalite", "FT Moutong", 18.5, 2900),
    "733-P-103": AssetData("1041535A", "Pompa Bio Solar", "FT Luwuk", 30.0, 2900),
    "706-P-203": AssetData("Unknown", "Pompa LPG", "IT Makassar", 45.0, 2950),
}

# ==========================================
# 3. USER INTERFACE (Streamlit)
# ==========================================

def main():
    st.set_page_config(page_title="Industrial Pump Diagnoser", layout="wide", page_icon="⚙️")
    
    st.title("🛡️ Industrial Reliability Assistant")
    st.markdown("Diagnosa Kesehatan Pompa Berbasis Standar **ISO 10816-3** & **TKI Pertamina**")
    
    # --- Sidebar: Asset Selection ---
    with st.sidebar:
        st.header("Konfigurasi Aset")
        selected_id = st.selectbox("Pilih Aset:", list(ASSETS_DB.keys()))
        asset = ASSETS_DB[selected_id]
        
        st.info(f"""
        **Asset Profile:**
        \n🏷️ Tag: `{asset.tag}`
        \n📍 Loc: `{asset.location}`
        \n⚡ Power: `{asset.power_kw} kW` ({asset.machine_class})
        """)
        
        inspector = st.text_input("Inspector Name:", "Petugas Lapangan")

    # --- Main Form: Industrial Grid Layout ---
    st.subheader(f"📝 Input Data Inspeksi: {asset.name}")
    
    with st.form("industrial_input_form"):
        st.markdown("### 1. Vibration Data Acquisition (Velocity mm/s RMS)")
        st.caption("Masukkan data sesuai pembacaan alat. Desimal menggunakan titik (.)")

        # Container untuk input
        c_motor, c_pump = st.columns(2)
        
        # Helper function untuk membuat input field dengan cepat
        def vib_input(label, key):
            return st.number_input(label, min_value=0.0, max_value=50.0, step=0.01, key=key)

        with c_motor:
            st.markdown("#### ⚡ DRIVER (Motor)")
            c1, c2, c3 = st.columns(3)
            with c1: m_nde_h = vib_input("NDE Horiz", "m_nde_h")
            with c2: m_nde_v = vib_input("NDE Vert", "m_nde_v")
            with c3: m_nde_a = vib_input("NDE Axial", "m_nde_a")
            st.markdown("---")
            c4, c5, c6 = st.columns(3)
            with c4: m_de_h = vib_input("DE Horiz", "m_de_h")
            with c5: m_de_v = vib_input("DE Vert", "m_de_v")
            with c6: m_de_a = vib_input("DE Axial", "m_de_a")

        with c_pump:
            st.markdown("#### 💧 DRIVEN (Pump)")
            c7, c8, c9 = st.columns(3)
            with c7: p_de_h = vib_input("DE Horiz", "p_de_h")
            with c8: p_de_v = vib_input("DE Vert", "p_de_v")
            with c9: p_de_a = vib_input("DE Axial", "p_de_a")
            st.markdown("---")
            c10, c11, c12 = st.columns(3)
            with c10: p_nde_h = vib_input("NDE Horiz", "p_nde_h")
            with c11: p_nde_v = vib_input("NDE Vert", "p_nde_v")
            with c12: p_nde_a = vib_input("NDE Axial", "p_nde_a")

        st.markdown("### 2. Operational Parameters")
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            temp_bearing = st.number_input("Max Bearing Temp (°C):", 0.0, 150.0, step=0.1)
        with col_op2:
            visual_check = st.multiselect("Temuan Visual (TKI Checklist):", 
                ["Baut Kendor", "Kebocoran Seal", "Suara Abnormal (Noise)", "Grounding Lepas", "Coating Rusak"])

        submit_btn = st.form_submit_button("🚀 RUN DIAGNOSTIC ANALYSIS")

    # --- Processing & Output ---
    if submit_btn:
        # 1. Agregasi Data ke Objek VibrationReading
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

        # 2. Jalankan Engine Diagnosa
        result = ReliabilityEngine.diagnose(
            readings=readings,
            machine_class=asset.machine_class,
            temp=temp_bearing,
            visual_issues=visual_check
        )

        # 3. Tampilkan Hasil Dashboard
        st.divider()
        st.markdown("## 📊 Diagnostic Report")
        
        # Kolom Layout Hasil
        col_res_left, col_res_right = st.columns([1, 2])
        
        with col_res_left:
            # Gauge Chart Plotly
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = result.max_vibration,
                title = {'text': "Max Severity (mm/s)"},
                gauge = {
                    'axis': {'range': [0, 15]},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, 1.12], 'color': "#2ecc71"},
                        {'range': [1.12, 2.80], 'color': "#f1c40f"},
                        {'range': [2.80, 7.10], 'color': "#e67e22"},
                        {'range': [7.10, 15], 'color': "#e74c3c"}
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': result.max_vibration}
                }
            ))
            fig.update_layout(height=300, margin=dict(l=20,r=20,t=50,b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption(f"📍 Critical Point: **{result.max_location}**")

        with col_res_right:
            # Status Box
            if result.iso_zone == ISOZone.A:
                st.success(f"### {result.iso_zone.value}")
            elif result.iso_zone == ISOZone.B:
                st.warning(f"### {result.iso_zone.value}")
            elif result.iso_zone == ISOZone.C:
                st.error(f"### {result.iso_zone.value}") # Streamlit ga punya orange box, pake error/warning
            else:
                st.error(f"### 🚨 {result.iso_zone.value}")

            # Root Causes List
            st.markdown("#### 🔍 Root Cause Analysis (AI Based)")
            if result.root_causes:
                for rc in result.root_causes:
                    st.write(f"- {rc}")
            else:
                st.write("- Tidak ada anomali spesifik terdeteksi.")

            # Recommendations
            st.markdown("#### 🛠️ Action Plan")
            for rec in result.recommendations:
                st.write(f"1. {rec}")

        # 4. Data Table (Expandable)
        with st.expander("Lihat Detail Data Mentah"):
            df_raw = pd.DataFrame([vars(r) for r in readings])
            st.dataframe(df_raw, use_container_width=True)

if __name__ == "__main__":
    main()
