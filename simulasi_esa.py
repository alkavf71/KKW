import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq

# --- FUNGSI FFT ---
def perform_esa_analysis(signal_data, fs):
    N = len(signal_data)
    yf = fft(signal_data)
    xf = fftfreq(N, 1 / fs)
    xf = xf[:N//2]
    amplitude = 2.0/N * np.abs(yf[0:N//2])
    amplitude_db = 20 * np.log10(amplitude + 1e-6)
    return xf, amplitude_db

# --- KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="ESA Analyzer - Pertamina Patra Niaga")

# --- HEADER ---
st.title("⚡ ESA Analyzer & Simulator Prototype")
st.markdown("**Infrastructure Management - Pertamina Patra Niaga**")

# --- TABS UTAMA ---
tab1, tab2 = st.tabs(["🎛️ Mode Simulasi (Konsep)", "📂 Mode Analisa (Data Lapangan)"])

# =========================================
# TAB 1: MODE SIMULASI (Edukasi)
# =========================================
with tab1:
    col_control, col_display = st.columns([1, 3])
    
    with col_control:
        st.subheader("Parameter")
        freq_fund = st.number_input("Frekuensi (Hz)", 50.0, disabled=True, key="f1")
        severity = st.slider("Tingkat Kerusakan Rotor", 0.0, 10.0, 0.0)
        noise = st.slider("Noise Level", 0.0, 0.5, 0.05)
        st.info("Geser slider untuk melihat efek 'Sidebands' pada grafik spektrum.")

    # Generate Data
    fs = 2000
    duration = 2.0
    N = int(fs * duration)
    t = np.linspace(0.0, duration, N, endpoint=False)
    
    # Sinyal Logic
    sig_pure = 100 * np.sin(2 * np.pi * freq_fund * t)
    sig_fault = (severity * 2) * np.sin(2 * np.pi * (freq_fund-5) * t) + \
                (severity * 2) * np.sin(2 * np.pi * (freq_fund+5) * t)
    sig_total = sig_pure + sig_fault + np.random.normal(0, noise * 10, N)

    # Analisa
    xf, y_db = perform_esa_analysis(sig_total, fs)

    with col_display:
        # Plot Spectrum Only (Focus)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xf, y=y_db, name='Spectrum', line=dict(color='#EF553B')))
        fig.update_xaxes(range=[30, 70], title="Frekuensi (Hz)")
        fig.update_yaxes(title="Amplitude (dB)")
        fig.add_vline(x=50, line_dash="dash", line_color="green", annotation_text="50Hz")
        
        if severity > 2:
            fig.add_vline(x=45, line_dash="dot", line_color="red")
            fig.add_vline(x=55, line_dash="dot", line_color="red")
            st.warning(f"⚠️ Terdeteksi Indikasi Kerusakan Rotor (Sidebands muncul)")
        
        st.plotly_chart(fig, use_container_width=True)

# =========================================
# TAB 2: MODE ANALISA (Upload CSV)
# =========================================
with tab2:
    st.markdown("### Upload Data Arus Aktual (CSV/Excel)")
    st.caption("Gunakan fitur ini untuk menganalisa data rekaman dari alat ukur portable.")
    
    uploaded_file = st.file_uploader("Pilih file CSV (Kolom harus berisi angka urutan waktu)", type=["csv", "txt"])
    
    col_input, col_result = st.columns([1, 3])
    
    if uploaded_file is not None:
        try:
            # Baca CSV (Asumsi 1 kolom data tanpa header, atau header di baris 1)
            df = pd.read_csv(uploaded_file, header=None)
            
            # Ambil data kolom pertama
            data_signal = df.iloc[:, 0].values
            
            with col_input:
                st.success("File berhasil dibaca!")
                fs_real = st.number_input("Sampling Rate Alat Ukur (Hz)", value=1000, step=100)
                st.write(f"Jumlah Data: {len(data_signal)} titik")
                
                if st.button("Lakukan Analisa FFT"):
                    with col_result:
                        xf_real, y_db_real = perform_esa_analysis(data_signal, fs_real)
                        
                        fig_real = go.Figure()
                        fig_real.add_trace(go.Scatter(x=xf_real, y=y_db_real, name='Real Spectrum'))
                        fig_real.update_layout(title="Hasil Analisa Spektrum Data Upload", xaxis_title="Frekuensi (Hz)", yaxis_title="dB")
                        
                        # Auto-zoom ke area 50Hz (Asumsi fundamental 50Hz)
                        fig_real.update_xaxes(range=[0, 100])
                        st.plotly_chart(fig_real, use_container_width=True)
                        
        except Exception as e:
            st.error(f"Error membaca file: {e}")
    else:
        st.info("Belum ada file diupload. Silakan upload file CSV berisi data arus (Time Series).")
