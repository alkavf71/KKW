import streamlit as st
import pandas as pd
import numpy as np

def diagnosa_vibrasi(h_val, v_val, a_val, limit):
    """
    Logika Diagnosa Awal berdasarkan Pola Arah Getaran.
    Dasar: Praktik umum Analisa Getaran (Mobius/API) dikombinasikan dengan limit ISO.
    """
    max_val = max(h_val, v_val, a_val)
    diagnosa = []
    
    # 1. Cek Severity (Keparahan) berdasarkan ISO 10816
    if max_val <= limit:
        status = "Good/Satisfactory"
        color = "green"
    elif max_val <= (limit * 1.5): # Asumsi Zone C awal
        status = "Alert (Investigate)"
        color = "orange"
    else:
        status = "Danger (Action Required)"
        color = "red"

    # 2. Cek Pola Masalah (Root Cause Analysis Sederhana)
    if status != "Good/Satisfactory":
        # Cek Misalignment: Axial dominan (biasanya > 50% dari radial tertinggi)
        if a_val > (0.5 * max(h_val, v_val)) and a_val > limit:
            diagnosa.append("Indikasi Misalignment (Poros tidak lurus)")
        
        # Cek Unbalance: Radial (H atau V) tinggi, Axial rendah
        if (h_val > limit or v_val > limit) and a_val < (0.5 * max(h_val, v_val)):
            diagnosa.append("Indikasi Unbalance (Ketidakseimbangan Massa)")
            
        # Cek Looseness/Soft Foot: Vertikal jauh lebih tinggi dari Horizontal (pada tumpuan)
        if v_val > (1.5 * h_val) and v_val > limit:
            diagnosa.append("Indikasi Mechanical Looseness / Soft Foot")
            
        if not diagnosa:
            diagnosa.append("Getaran Umum Tinggi (Perlu Analisa Spektrum)")
    else:
        diagnosa.append("Operasi Normal")

    return status, ", ".join(diagnosa), color

def app():
    st.header("⚙️ Inspeksi Mekanikal & Vibrasi")
    st.subheader("Input Data Vibrasi (Velocity RMS mm/s)")

    # 1. Konfigurasi Mesin (Untuk menentukan Limit ISO)
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        machine_class = st.selectbox("Kelas Mesin (ISO 10816)", 
                                     ["Class I (Kecil <15kW)", "Class II (Medium 15-300kW)", "Class III (Besar >300kW Rigid)", "Class IV (Besar Soft)"], index=1)
    
    # Tentukan Limit berdasarkan Kelas (Contoh simplified)
    limits = {
        "Class I (Kecil <15kW)": 2.8,   # Batas Zone B/C
        "Class II (Medium 15-300kW)": 4.5, # Batas Zone B/C (Sesuai screenshot Anda)
        "Class III (Besar >300kW Rigid)": 7.1,
        "Class IV (Besar Soft)": 11.2
    }
    limit_iso = limits[machine_class]
    with col_conf2:
        st.metric("Limit ISO (Zone B/C)", f"{limit_iso} mm/s")

    st.divider()

    # 2. Form Input (Layout seperti Laporan Pertamina)
    col1, col2 = st.columns(2)
    
    # DRIVER (MOTOR)
    with col1:
        st.info("DRIVER (MOTOR)")
        # Horizontal
        d_h_de = st.number_input("Driver H - DE", 0.0, 100.0, 1.31, step=0.01)
        d_h_nde = st.number_input("Driver H - NDE", 0.0, 100.0, 2.96, step=0.01)
        # Vertical
        d_v_de = st.number_input("Driver V - DE", 0.0, 100.0, 4.49, step=0.01)
        d_v_nde = st.number_input("Driver V - NDE", 0.0, 100.0, 9.80, step=0.01)
        # Axial
        d_a_de = st.number_input("Driver A - DE", 0.0, 100.0, 2.24, step=0.01)
        d_a_nde = st.number_input("Driver A - NDE", 0.0, 100.0, 2.50, step=0.01)

    # DRIVEN (POMPA)
    with col2:
        st.warning("DRIVEN (POMPA)")
        # Horizontal
        p_h_de = st.number_input("Driven H - DE", 0.0, 100.0, 3.73, step=0.01)
        p_h_nde = st.number_input("Driven H - NDE", 0.0, 100.0, 1.80, step=0.01)
        # Vertical
        p_v_de = st.number_input("Driven V - DE", 0.0, 100.0, 4.89, step=0.01)
        p_v_nde = st.number_input("Driven V - NDE", 0.0, 100.0, 1.76, step=0.01)
        # Axial
        p_a_de = st.number_input("Driven A - DE", 0.0, 100.0, 4.13, step=0.01)
        p_a_nde = st.number_input("Driven A - NDE", 0.0, 100.0, 3.07, step=0.01)

    # 3. Kalkulasi & Diagnosa
    if st.button("Analisa & Generate Report"):
        
        # Helper untuk hitung rata-rata
        def calc_row(label, h_de, h_nde, v_de, v_nde, a_de, a_nde):
            # Rata-rata per Axis
            avg_h = (h_de + h_nde) / 2
            avg_v = (v_de + v_nde) / 2
            avg_a = (a_de + a_nde) / 2
            
            # Diagnosa berdasarkan nilai MAX per axis (bukan rata-rata, agar lebih aman)
            # Kita ambil nilai max dari DE/NDE untuk diagnosa agar tidak false negative
            max_h = max(h_de, h_nde)
            max_v = max(v_de, v_nde)
            max_a = max(a_de, a_nde)
            
            status, diagnosis_text, color = diagnosa_vibrasi(max_h, max_v, max_a, limit_iso)
            
            return [
                {"Point": label, "Dir": "H", "DE": h_de, "NDE": h_nde, "Avr": avg_h, "Limit": limit_iso, "Remark": diagnosis_text if avg_h > limit_iso else "Normal"},
                {"Point": "", "Dir": "V", "DE": v_de, "NDE": v_nde, "Avr": avg_v, "Limit": limit_iso, "Remark": diagnosis_text if avg_v > limit_iso else "Normal"},
                {"Point": "", "Dir": "A", "DE": a_de, "NDE": a_nde, "Avr": avg_a, "Limit": limit_iso, "Remark": diagnosis_text if avg_a > limit_iso else "Normal"}
            ]

        data_rows = []
        data_rows.extend(calc_row("Driver", d_h_de, d_h_nde, d_v_de, d_v_nde, d_a_de, d_a_nde))
        data_rows.extend(calc_row("Driven", p_h_de, p_h_nde, p_v_de, p_v_nde, p_a_de, p_a_nde))

        df = pd.DataFrame(data_rows)
        
        st.write("### Laporan Hasil Inspeksi")
        
        # Formatting Table dengan Pandas Styler
        def highlight_danger(val):
            if isinstance(val, float) and val > limit_iso:
                return 'color: red; font-weight: bold'
            return ''

        st.dataframe(
            df.style.applymap(highlight_danger, subset=['Avr', 'DE', 'NDE'])
                    .format("{:.2f}", subset=['DE', 'NDE', 'Avr', 'Limit']),
            use_container_width=True,
            hide_index=True
        )

        st.success("Diagnosa Selesai. Silakan export data atau screenshot untuk laporan.")
