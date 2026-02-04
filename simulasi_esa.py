import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Import modul buatan sendiri
import assets_db
import iso_logic

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Digital Reliability Assistant", layout="wide")

# --- HEADER & SIDEBAR ---
st.title("🛡️ Digital Reliability Assistant")
st.markdown("Sistem Penunjang Keputusan Inspeksi Pompa - Pertamina Patra Niaga")

# Sidebar untuk Navigasi & Aset
with st.sidebar:
    st.header("Konfigurasi Inspeksi")
    
    # 1. Pilih Aset (Dari Database GitHub/Lokal)
    selected_asset_name = st.selectbox("Pilih Aset Pompa:", list(assets_db.ASSETS.keys()))
    asset_data = assets_db.ASSETS[selected_asset_name]
    
    st.info(f"""
    **Detail Aset:**
    \n📍 Lokasi: {asset_data['location']}
    \n🏷️ Tag: {asset_data['tag_no']}
    \n⚡ Power: {asset_data['power_kw']} kW
    \n⚙️ Class: {asset_data['class_iso']}
    """)
    
    st.divider()
    st.caption("Versi Aplikasi: 1.0 (Prototype)")

# --- TAB UTAMA (Menu Jenjang Inspeksi) ---
tab1, tab2, tab3 = st.tabs(["📋 Inspeksi Harian (Operator)", "🔍 Diagnosa Inspektor (Expert)", "📊 Riwayat Data"])

# === TAB 1: INSPEKSI HARIAN (TKI C-05) ===
with tab1:
    st.subheader("Checklist Harian (Visual & Indrawi)")
    st.markdown("*Referensi: TKI C-05 Pelaksanaan Pemeliharaan Pompa Produk (Harian)*")
    
    col_a, col_b = st.columns(2)
    with col_a:
        chk_clean = st.checkbox("Kebersihan Area & Motor (Bebas debu/oli?)")
        chk_leak = st.checkbox("Tidak ada Kebocoran (Seal/Pipa?)")
        chk_oil = st.checkbox("Level Oil/Grease Normal?")
    with col_b:
        chk_bolt = st.checkbox("Baut & Mur Kencang (Tidak kendor?)")
        chk_sound = st.checkbox("Suara Halus (Tidak kasar/dengung?)")
        chk_panel = st.checkbox("Panel Indikator Normal (Tidak alarm?)")
    
    if st.button("Submit Laporan Harian"):
        if all([chk_clean, chk_leak, chk_oil, chk_bolt, chk_sound, chk_panel]):
            st.success("✅ Kondisi Pompa AMAN (Normal Operation).")
        else:
            st.error("⚠️ Ditemukan Anomali! Segera laporkan ke Tim Pemeliharaan.")
            st.markdown("**Rekomendasi:** Cek TKI C-05 Lampiran 2 untuk langkah perbaikan ringan.")

# === TAB 2: DIAGNOSA INSPEKTOR (TKI C-04 & ISO 10816) ===
with tab2:
    st.subheader("Analisa Vibrasi & Kesehatan Aset")
    st.markdown(f"*Referensi: TKI C-04 Bulanan & Laporan Inspeksi Lapangan {asset_data['location']}*")
    
    # Input Form (Seperti alat ukur Vibrometer)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 1. Vibrasi (Velocity RMS)")
        vib_val = st.number_input("Input Nilai Vibrasi Tertinggi (mm/s):", min_value=0.0, step=0.01, format="%.2f")
        vib_pos = st.selectbox("Posisi Pengukuran:", ["DE - Horizontal", "DE - Vertical", "DE - Axial", "NDE - Horizontal", "NDE - Vertical"])
    
    with col2:
        st.markdown("### 2. Parameter Operasi")
        temp_val = st.number_input("Suhu Bearing (°C):", min_value=0.0, step=0.1)
        rpm_act = st.number_input("RPM Aktual:", value=asset_data['rpm_design'])
    
    with col3:
        st.markdown("### 3. Temuan Visual Kritis")
        vis_baut = st.checkbox("Baut/Mur Kendor")
        vis_bocor = st.checkbox("Kebocoran Aktif")
        vis_cat = st.checkbox("Coating/Cat Terkelupas")

    # Tombol Analisa
    if st.button("🚀 JALANKAN DIAGNOSA"):
        # 1. Panggil Logic Vibrasi
        status, color_code, message = iso_logic.get_vibration_status(vib_val, asset_data['class_iso'])
        
        # 2. Panggil Logic Visual
        visual_issues = iso_logic.check_visual_anomaly({
            "baut_kendor": vis_baut, 
            "kebocoran": vis_bocor, 
            "suara_abnormal": False # Asumsi dari input vibrasi
        })
        
        st.divider()
        
        # TAMPILAN HASIL (RESULT)
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            # Gauge Chart untuk Vibrasi
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = vib_val,
                title = {'text': f"Vibrasi ({status})"},
                gauge = {
                    'axis': {'range': [0, 10]}, # Max 10 mm/s biar grafik bagus
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, 1.12], 'color': "lightgreen"},
                        {'range': [1.12, 2.80], 'color': "yellow"},
                        {'range': [2.80, 7.10], 'color': "orange"},
                        {'range': [7.10, 10], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': vib_val
                    }
                }
            ))
            fig.update_layout(height=300, margin=dict(l=20,r=20,t=50,b=20))
            st.plotly_chart(fig, use_container_width=True)
            
        with res_col2:
            st.subheader("Hasil Diagnosa AI:")
            
            # Tampilkan Alert Box Sesuai Status
            if color_code == "success":
                st.success(f"### {status}\n{message}")
            elif color_code == "warning":
                st.warning(f"### {status}\n{message}")
            elif color_code == "orange": # Streamlit ga punya st.orange, pakai warning dgn icon beda
                st.warning(f"### {status}\n⚠️ {message}")
            else:
                st.error(f"### {status}\n🚨 {message}")
            
            # Tampilkan Rekomendasi Visual
            if visual_issues or vis_cat:
                st.markdown("#### 🛠️ Tindakan Perbaikan Fisik:")
                for issue in visual_issues:
                    st.write(f"- {issue}")
                if vis_cat:
                    st.write("- Lakukan *touch-up painting* pada area terkelupas (Ref: TKI 2 Tahunan).")
            
            # Cek Suhu
            if temp_val > 85: # Limit standar API 610 / TKI C-04
                st.error(f"🌡️ SUHU OVERHEAT ({temp_val}°C)! Batas aman < 85°C. Cek pelumasan.")

        # SIMPAN DATA (Sesi Sementara - Demo)
        # Nanti bagian ini diganti koneksi ke Google Sheets
        if 'history' not in st.session_state:
            st.session_state['history'] = []
            
        new_record = {
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Aset": selected_asset_name,
            "Vibrasi": vib_val,
            "Status": status,
            "Isu Visual": ", ".join(visual_issues) if visual_issues else "-"
        }
        st.session_state['history'].append(new_record)
        st.toast("Data berhasil disimpan sementara!", icon="💾")

# === TAB 3: RIWAYAT DATA ===
with tab3:
    st.subheader("Log Data Inspeksi (Sesi Ini)")
    st.info("Catatan: Data ini tersimpan sementara di memori browser. Untuk penyimpanan permanen, hubungkan ke Google Sheets.")
    
    if 'history' in st.session_state and st.session_state['history']:
        df_hist = pd.DataFrame(st.session_state['history'])
        st.dataframe(df_hist, use_container_width=True)
        
        # Download Button
        csv = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button("Unduh Laporan CSV", data=csv, file_name="laporan_inspeksi.csv", mime="text/csv")
    else:
        st.write("Belum ada data inspeksi yang masuk.")
