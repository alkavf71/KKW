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
    
    xf = xf[:N//2]
    amplitude = 2.0/N * np.abs(yf[0:N//2])
    amplitude_db = 20 * np.log10(amplitude + 1e-9)
    
    # B. Temukan Puncak Fundamental (Sekitar 50Hz)
    idx_50 = np.argmin(np.abs(xf - 50))
    search_radius = 100 
    idx_peak = idx_50 - search_radius + np.argmax(amplitude_db[idx_50-search_radius : idx_50+search_radius])
    
    freq_fund = xf[idx_peak]
    amp_fund = amplitude_db[idx_peak]
    
    # C. Cek Sidebands (Indikasi Rotor Bar)
    target_sb_left = freq_fund - 5 
    idx_sb_left = np.argmin(np.abs(xf - target_sb_left))
    # Cari puncak noise tertinggi di area sideband
    idx_peak_sb = idx_sb_left - 50 + np.argmax(amplitude_db[idx_sb_left-50 : idx_sb_left+50])
    
    amp_sb = amplitude_db[idx_peak_sb]
    
    # D. Cek Harmonisa ke-3
    idx_h3 = np.argmin(np.abs(xf - (freq_fund * 3)))
    amp_h3 = amplitude_db[idx_h3]

    # --- LOGIKA KEPUTUSAN (RULE BASED) - TUNED ---
    diagnosis = []
    status = "NORMAL"
    
    # Rule 1: Cek Rotor 
    # REVISI: Threshold diubah dari 40 jadi 30 agar tidak terlalu sensitif noise
    diff_rotor = amp_fund - amp_sb
    if diff_rotor < 30: 
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
        # Sidebands (Amplitude 5)
        sig += 5 * np.sin(2 * np.pi * 45 * t)
        sig += 5 * np.sin(2 * np.pi * 55 * t)
        # Noise level sedang
        sig += np.random.normal(0, 0.5, len(t))
        filename = "motor_rusak_rotor.csv"
    else:
        # Sehat - Noise SANGAT KECIL (REVISI: 0.1)
        sig += np.random.normal(0, 0.1, len(t))
        filename = "motor_sehat.csv"
        
    df = pd.DataFrame(sig)
    return df.to_csv(index=False, header=False), filename

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.set_page_config(layout="wide", page_title="ESA Auto-Diagnose")
st.title("🤖 ESA Automated Diagnosis System (Tuned)")
st.markdown("**Infrastructure Management - Pertamina Patra Niaga**")

# --- SIDEBAR ---
st.sidebar.header("1. Persiapan Data")
st.sidebar.warning("⚠️ PENTING: Klik tombol download di bawah ini lagi untuk mendapatkan data CSV versi terbaru (yang sudah di-tuning).")

csv_sehat, name_sehat = create_dummy_csv("Sehat")
st.sidebar.download_button("⬇️ Download CSV: Motor Sehat (v2)", csv_sehat, name_sehat, "text/csv")

csv_rusak, name_rusak = create_dummy_csv("Rusak (Rotor)")
st.sidebar.download_button("⬇️ Download CSV: Motor Rusak (v2)", csv_rusak, name_rusak, "text/csv")

# --- MAIN AREA ---
st.divider()
st.header("2. Upload & Analisa")

uploaded_file = st.file_uploader("Upload File Rekaman Arus (Format .csv)", type=["csv", "txt"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, header=None)
        data_signal = df.iloc[:, 0].values
        
        fs_input = 2000
        xf, y_db, status, diagnosis_list, freq_fund = analyze_and_diagnose(data_signal, fs_input)
        
        # TAMPILAN
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
                if "✅" in diag: st.success(diag)
                else: st.error(diag)
            
            # Tampilkan info selisih dB untuk debugging saat presentasi
            # Ini fitur bagus untuk menunjukkan kenapa dia Normal/Critical
            st.info(f"Fundamental Freq: {freq_fund:.2f} Hz")

        st.subheader("📊 Visualisasi Spektrum")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xf, y=y_db, mode='lines', name='Spectrum', line=dict(color='#1f77b4')))
        
        # Tampilkan batas Threshold visual
        peak_amp = np.max(y_db)
        # Garis batas 30dB dari puncak
        fig.add_hline(y=peak_amp-30, line_dash="dash", line_color="red", annotation_text="Limit Bahaya (-30dB)")
        
        fig.update_layout(xaxis_title="Frekuensi (Hz)", yaxis_title="dB", height=500)
        fig.update_xaxes(range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error: {e}")
