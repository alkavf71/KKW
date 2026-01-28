import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq

# ==========================================
# 1. FUNGSI OTAK DIAGNOSA (ALGORITMA)
# ==========================================
def analyze_and_diagnose(signal_data, fs):
    # A. Lakukan FFT
    N = len(signal_data)
    yf = fft(signal_data)
    xf = fftfreq(N, 1 / fs)
    
    # Ambil sisi positif saja
    xf = xf[:N//2]
    amplitude = 2.0/N * np.abs(yf[0:N//2])
    
    # Konversi ke dB (hindari log 0)
    amplitude_db = 20 * np.log10(amplitude + 1e-9)
    
    # B. Temukan Puncak Fundamental (Sekitar 50Hz)
    # Cari index frekuensi yang paling dekat dengan 50Hz
    idx_50 = np.argmin(np.abs(xf - 50))
    # Cari puncak tertinggi di radius 5Hz sekitar 50Hz (untuk akurasi)
    search_radius = 100 # index points
    idx_peak = idx_50 - search_radius + np.argmax(amplitude_db[idx_50-search_radius : idx_50+search_radius])
    
    freq_fund = xf[idx_peak]
    amp_fund = amplitude_db[idx_peak]
    
    # C. Cek Sidebands (Indikasi Rotor Bar)
    # Kita cari di area kiri (sekitar -5Hz dari fundamental)
    target_sb_left = freq_fund - 5 
    idx_sb_left = np.argmin(np.abs(xf - target_sb_left))
    # Cari puncak lokal di sekitar situ
    idx_peak_sb = idx_sb_left - 50 + np.argmax(amplitude_db[idx_sb_left-50 : idx_sb_left+50])
    
    amp_sb = amplitude_db[idx_peak_sb]
    
    # D. Cek Harmonisa ke-3 (Indikasi Power Quality)
    idx_h3 = np.argmin(np.abs(xf - (freq_fund * 3)))
    amp_h3 = amplitude_db[idx_h3]

    # --- LOGIKA KEPUTUSAN (RULE BASED) ---
    diagnosis = []
    status = "NORMAL"
    
    # Rule 1: Cek Rotor (Selisih dB Sideband vs Fundamental)
    diff_rotor = amp_fund - amp_sb
    if diff_rotor < 30: # Jika selisih kurang dari 40dB (Sideband tinggi)
        status = "CRITICAL"
        diagnosis.append(f"⚠️ **BROKEN ROTOR BAR DETECTED!** (Sideband High: -{diff_rotor:.1f} dB diff)")
    
    # Rule 2: Cek Harmonisa
    diff_harm = amp_fund - amp_h3
    if diff_harm < 50:
        if status != "CRITICAL": status = "WARNING"
        diagnosis.append(f"⚠️ **POWER QUALITY ISSUE** (High 3rd Harmonic)")

    if status == "NORMAL":
        diagnosis.append("✅ Motor dalam kondisi Prima. Tidak ada anomali signifikan.")

    return xf, amplitude_db, status, diagnosis, freq_fund

# ==========================================
# 2. FUNGSI BANTUAN: MEMBUAT CSV DUMMY
# ==========================================
def create_dummy_csv(condition):
    fs = 2000
    duration = 2.0
    t = np.linspace(0.0, duration, int(fs*duration), endpoint=False)
    
    # Sinyal Dasar
    sig = 100 * np.sin(2 * np.pi * 50 * t)
    
    if condition == "Rusak (Rotor)":
        # Tambah Sidebands
        sig += 5 * np.sin(2 * np.pi * 45 * t)
        sig += 5 * np.sin(2 * np.pi * 55 * t)
        filename = "motor_rusak_rotor.csv"
    else:
        # Sehat
        filename = "motor_sehat.csv"
        
    sig += np.random.normal(0, 0.1, len(t)) # Sedikit noise
    
    # Simpan ke DataFrame
    df = pd.DataFrame(sig)
    return df.to_csv(index=False, header=False), filename

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.set_page_config(layout="wide", page_title="ESA Auto-Diagnose")
st.title("🤖 ESA Automated Diagnosis System")
st.markdown("**Infrastructure Management - Pertamina Patra Niaga**")

# --- SIDEBAR: DOWNLOAD DATA SAMPLE ---
st.sidebar.header("1. Persiapan Data (Simulasi)")
st.sidebar.info("Gunakan tombol ini untuk download contoh file CSV, lalu upload ulang di menu utama untuk mengetes diagnosa.")

# Tombol Download CSV Sehat
csv_sehat, name_sehat = create_dummy_csv("Sehat")
st.sidebar.download_button("⬇️ Download CSV Contoh: Motor Sehat", csv_sehat, name_sehat, "text/csv")

# Tombol Download CSV Rusak
csv_rusak, name_rusak = create_dummy_csv("Rusak (Rotor)")
st.sidebar.download_button("⬇️ Download CSV Contoh: Motor Rusak", csv_rusak, name_rusak, "text/csv")

# --- MAIN AREA: UPLOAD & DIAGNOSA ---
st.divider()
st.header("2. Upload & Analisa Data Lapangan")

uploaded_file = st.file_uploader("Upload File Rekaman Arus (Format .csv)", type=["csv", "txt"])

if uploaded_file is not None:
    try:
        # Baca File
        df = pd.read_csv(uploaded_file, header=None)
        data_signal = df.iloc[:, 0].values # Ambil kolom pertama
        
        # PROSES OTOMATIS
        fs_input = 2000 # Asumsi sampling rate (bisa dibuat inputan user jika perlu)
        xf, y_db, status, diagnosis_list, freq_fund = analyze_and_diagnose(data_signal, fs_input)
        
        # --- TAMPILAN HASIL DIAGNOSA (KARTU LAPORAN) ---
        st.subheader("📋 Laporan Hasil Diagnosa")
        
        # Warna Status
        status_color = "green" if status == "NORMAL" else "red"
        if status == "WARNING": status_color = "orange"
        
        col_stat, col_det = st.columns([1, 2])
        
        with col_stat:
            st.markdown(f"""
            <div style="text-align: center; border: 2px solid {status_color}; padding: 20px; border-radius: 10px;">
                <h2 style="color: {status_color}; margin:0;">{status}</h2>
                <p>Condition Status</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_det:
            for diag in diagnosis_list:
                if "✅" in diag:
                    st.success(diag)
                else:
                    st.error(diag)
            st.caption(f"Fundamental Frequency Detected: {freq_fund:.2f} Hz")

        # --- TAMPILAN GRAFIK ---
        st.divider()
        st.subheader("📊 Visualisasi Spektrum")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xf, y=y_db, mode='lines', name='Spectrum', line=dict(color='#1f77b4')))
        
        # Tambah garis batas aman (Threshold)
        peak_amp = np.max(y_db)
        fig.add_hline(y=peak_amp-40, line_dash="dash", line_color="red", annotation_text="Limit Bahaya (-40dB)")
        
        fig.update_layout(xaxis_title="Frekuensi (Hz)", yaxis_title="Amplitudo (dB)", height=500)
        fig.update_xaxes(range=[0, 100]) # Zoom default ke area relevan
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        st.info("Pastikan file CSV hanya berisi 1 kolom angka (data arus).")

else:
    st.info("👋 Silakan upload file CSV untuk memulai diagnosa otomatis.")
