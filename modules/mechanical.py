import streamlit as st
import pandas as pd
import numpy as np

# --- 1. DEFINISI STANDAR ISO 10816-3 & WARNA ---
def get_iso_zone(value, machine_class):
    """
    Menentukan Zona ISO dan Warna berdasarkan Velocity RMS (mm/s).
    """
    # Batas Limit [Batas A/B, Batas B/C, Batas C/D]
    # Referensi: ISO 10816-3 untuk Rigid Foundation (Umum di pompa)
    limits = {
        "Class I (Kecil <15kW)": [0.71, 1.80, 4.50],
        "Class II (Medium 15-300kW)": [1.12, 2.80, 4.50], # Standard Pompa Sentrifugal
        "Class III (Besar >300kW Rigid)": [1.80, 4.50, 7.10],
        "Class IV (Besar Soft)": [2.80, 7.10, 11.20]
    }
    
    lim = limits[machine_class]
    
    # Logika Penentuan Zona & Warna
    if value < lim[0]:
        # ZONE A: Green
        return "A", "New machine condition", "green"
    elif value < lim[1]:
        # ZONE B: Yellow
        return "B", "Unlimited long-term operation allowable", "yellow"
    elif value < lim[2]:
        # ZONE C: Orange
        return "C", "Short-term operation allowable", "orange"
    else:
        # ZONE D: Red
        return "D", "Vibration causes damage", "red"

# --- 2. LOGIKA DIAGNOSA KERUSAKAN (AI DIAGNOSTIC) ---
def analyze_root_cause(h_val, v_val, a_val, warning_threshold):
    """
    Diagnosa akar masalah (Misalignment, Unbalance, Looseness, Bearing)
    berdasarkan perbandingan arah getaran.
    """
    diagnosa = []
    rekomendasi = []
    
    # Ambil nilai tertinggi untuk safety factor
    max_val = max(h_val, v_val, a_val)
    
    # Jika getaran masih Zona A atau B (Aman/Kuning), diagnosa normal
    # Kita ambil threshold batas B ke C (misal 2.80 untuk Class II)
    if max_val < warning_threshold:
        return ["Kondisi Normal"], ["Lanjutkan monitoring rutin (Predictive Maintenance)"]

    # --- RULE 1: MISALIGNMENT (Ketidaklurusan) ---
    # Ciri: Getaran Axial tinggi (Dominan > 50% dari Radial tertinggi)
    if a_val > (0.5 * max(h_val, v_val)) and a_val > (warning_threshold * 0.8):
        diagnosa.append("Angular Misalignment (Poros Miring)")
        rekomendasi.append("Cek alignment kopling (Laser/Dial). Pastikan offset < 0.05mm.")
        rekomendasi.append("Cek 'Pipe Strain' (Pipa menekan pompa).")

    # --- RULE 2: UNBALANCE (Tidak Seimbang) ---
    # Ciri: Radial (H/V) tinggi, Axial rendah. Biasanya frekuensi 1x RPM.
    if (h_val > warning_threshold or v_val > warning_threshold) and a_val < (0.5 * max(h_val, v_val)):
        diagnosa.append("Unbalance (Massa Tidak Seimbang)")
        rekomendasi.append("Cek fisik impeller/kipas motor dari kotoran/kerak.")
        rekomendasi.append("Lakukan balancing ulang (Standar G2.5/G6.3).")

    # --- RULE 3: MECHANICAL LOOSENESS / SOFT FOOT ---
    # Ciri: Vertikal jauh lebih tinggi dari Horizontal pada tumpuan.
    if v_val > (1.5 * h_val) and v_val > warning_threshold:
        diagnosa.append("Mechanical Looseness / Soft Foot")
        rekomendasi.append("Kencangkan baut angkur (Anchor Bolt).")
        rekomendasi.append("Cek kerataan kaki motor (Soft foot) dengan feeler gauge.")

    # --- RULE 4: BEARING ISSUE (Umum) ---
    # Jika getaran tinggi tapi pola tidak spesifik ke arah tertentu
    if not diagnosa: # Jika list diagnosa masih kosong tapi nilai tinggi
        diagnosa.append("Indikasi Kerusakan Bearing / Kavitasi")
        rekomendasi.append("Cek lubrikasi (Greasing).")
        rekomendasi.append("Analisa suara bearing (Stetoskop).")
        rekomendasi.append("Cek tekanan suction (Kavitasi).")

    return diagnosa, rekomendasi

# --- 3. APLIKASI UTAMA ---
def app():
    st.header("⚙️ Inspeksi Mekanikal & Vibrasi (ISO 10816)")
    st.markdown("---")

    # --- A. SETUP ---
    col_conf1, col_conf2 = st.columns([3, 1])
    with col_conf1:
        machine_class = st.selectbox(
            "Klasifikasi Mesin (ISO 10816-3)", 
            [
                "Class I (Kecil <15kW)", 
                "Class II (Medium 15-300kW)", 
                "Class III (Besar >300kW Rigid)", 
                "Class IV (Besar Soft)"
            ], 
            index=1,
            help="Pilih Class II untuk pompa standar industri Pertamina."
        )
    
    # Tentukan limit ambang batas Warning (Zona C) untuk trigger diagnosa
    limits_map = {
        "Class I (Kecil <15kW)": 1.80,
        "Class II (Medium 15-300kW)": 2.80, # Batas Kuning ke Oranye
        "Class III (Besar >300kW Rigid)": 4.50,
        "Class IV (Besar Soft)": 7.10
    }
    warning_threshold = limits_map[machine_class]

    with col_conf2:
        st.metric("Batas Alert (Zona C)", f"{warning_threshold} mm/s")

    # --- B. INPUT DATA ---
    st.subheader("Input Data Vibrasi (Velocity RMS)")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("🔌 DRIVER (MOTOR)")
        d_h_de = st.number_input("H - DE (Motor)", 0.00, 50.00, 1.31)
        d_h_nde = st.number_input("H - NDE (Motor)", 0.00, 50.00, 2.96)
        st.write("") # Spacer
        d_v_de = st.number_input("V - DE (Motor)", 0.00, 50.00, 4.49)
        d_v_nde = st.number_input("V - NDE (Motor)", 0.00, 50.00, 9.80)
        st.write("")
        d_a_de = st.number_input("A - DE (Motor)", 0.00, 50.00, 2.24)
        d_a_nde = st.number_input("A - NDE (Motor)", 0.00, 50.00, 2.50)

    with col2:
        st.warning("💧 DRIVEN (POMPA)")
        p_h_de = st.number_input("H - DE (Pompa)", 0.00, 50.00, 3.73)
        p_h_nde = st.number_input("H - NDE (Pompa)", 0.00, 50.00, 1.80)
        st.write("")
        p_v_de = st.number_input("V - DE (Pompa)", 0.00, 50.00, 4.89)
        p_v_nde = st.number_input("V - NDE (Pompa)", 0.00, 50.00, 1.76)
        st.write("")
        p_a_de = st.number_input("A - DE (Pompa)", 0.00, 50.00, 4.13)
        p_a_nde = st.number_input("A - NDE (Pompa)", 0.00, 50.00, 3.07)

    # --- C. PROSES ---
    if st.button("📊 Analisa & Generate Report", type="primary"):
        
        # --- LOGIC TABLE GENERATION ---
        def create_table_row(comp_name, h_de, h_nde, v_de, v_nde, a_de, a_nde):
            # 1. Hitung Average (Sesuai format user)
            avg_h = (h_de + h_nde) / 2
            avg_v = (v_de + v_nde) / 2
            avg_a = (a_de + a_nde) / 2

            # 2. Cari Remark & Zone berdasarkan nilai Average
            # (Jika user ingin remark berdasarkan Max value, ganti avg_h dengan max(h_de, h_nde))
            z_h, rem_h, _ = get_iso_zone(avg_h, machine_class)
            z_v, rem_v, _ = get_iso_zone(avg_v, machine_class)
            z_a, rem_a, _ = get_iso_zone(avg_a, machine_class)

            rows = [
                [f"{comp_name} H", h_de, h_nde, avg_h, z_h, rem_h],
                [f"{comp_name} V", v_de, v_nde, avg_v, z_v, rem_v],
                [f"{comp_name} A", a_de, a_nde, avg_a, z_a, rem_a]
            ]
            
            # 3. Diagnosa Kerusakan (Pakai MAX value agar sensitif)
            max_h, max_v, max_a = max(h_de, h_nde), max(v_de, v_nde), max(a_de, a_nde)
            diag, rec = analyze_root_cause(max_h, max_v, max_a, warning_threshold)
            
            return rows, diag, rec

        # Generate Data
        rows_d, diag_d, rec_d = create_table_row("Driver", d_h_de, d_h_nde, d_v_de, d_v_nde, d_a_de, d_a_nde)
        rows_p, diag_p, rec_p = create_table_row("Driven", p_h_de, p_h_nde, p_v_de, p_v_nde, p_a_de, p_a_nde)

        all_rows = rows_d + rows_p
        df = pd.DataFrame(all_rows, columns=["Titik", "DE", "NDE", "Avr", "Zone", "Remark"])

        # --- D. TAMPILAN OUTPUT ---
        st.divider()
        st.subheader("1. Tabel Hasil Pengujian")

        # Styling Function untuk Pandas (Highlighting Background)
        def highlight_remark(val):
            val_lower = str(val).lower()
            if "damage" in val_lower: # Merah (Zone D)
                return 'background-color: #ff4b4b; color: white; font-weight: bold;'
            elif "short-term" in val_lower: # Oranye (Zone C)
                return 'background-color: #ffa500; color: black; font-weight: bold;'
            elif "unlimited" in val_lower: # Kuning (Zone B)
                return 'background-color: #ffd700; color: black; font-weight: bold;'
            elif "new machine" in val_lower: # Hijau (Zone A)
                return 'background-color: #90ee90; color: black; font-weight: bold;'
            return ''

        # Render Tabel dengan Style
        st.dataframe(
            df.style.applymap(highlight_remark, subset=['Remark'])
                    .format("{:.2f}", subset=['DE', 'NDE', 'Avr']),
            use_container_width=True,
            hide_index=True,
            height=300
        )

        st.subheader("2. Diagnosa & Rekomendasi Teknis")
        
        c_diag1, c_diag2 = st.columns(2)
        
        # Display Diagnosa Driver
        with c_diag1:
            st.markdown("#### ⚡ Driver (Motor)")
            if "Normal" in diag_d[0]:
                st.success("✅ Kondisi Mekanikal Baik")
            else:
                for d in diag_d:
                    st.error(f"⚠️ **{d}**")
                with st.expander("Lihat Rekomendasi Perbaikan", expanded=True):
                    for r in rec_d:
                        st.markdown(f"- {r}")

        # Display Diagnosa Driven
        with c_diag2:
            st.markdown("#### 💧 Driven (Pompa)")
            if "Normal" in diag_p[0]:
                st.success("✅ Kondisi Mekanikal Baik")
            else:
                for d in diag_p:
                    st.error(f"⚠️ **{d}**")
                with st.expander("Lihat Rekomendasi Perbaikan", expanded=True):
                    for r in rec_p:
                        st.markdown(f"- {r}")
