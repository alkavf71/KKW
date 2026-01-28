import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq

# --- KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="Simulasi ESA - Pertamina Patra Niaga")

# --- JUDUL & HEADER ---
st.title("⚡ ESA (Electrical Signature Analysis) Simulator")
st.markdown("""
**Prototype Digital Twin untuk Monitoring Kesehatan Motor Listrik**
*Infrastructure Management - Pertamina Patra Niaga*
""")
st.divider()

# --- SIDEBAR (PANEL KONTROL) ---
st.sidebar.header("🎛️ Panel Kontrol Simulasi")

# 1. Parameter Motor
st.sidebar.subheader("1. Parameter Motor")
freq_fundamental = st.sidebar.number_input("Frekuensi Listrik (Hz)", value=50.0, disabled=True)
sampling_rate = 2000 # Hz
duration = 2.0 # detik

# 2. Simulasi Kerusakan (Fault Injection)
st.sidebar.subheader("2. Simulasi Kerusakan (Fault)")
st.sidebar.info("Geser slider di bawah untuk mensimulasikan kerusakan Rotor Bar.")
fault_severity = st.sidebar.slider("Tingkat Kerusakan (Severity)", 0.0, 10.0, 0.0, help="0 = Sehat, 10 = Rusak Parah")
noise_level = st.sidebar.slider("Level Noise (Gangguan Sinyal)", 0.0, 0.5, 0.05)

# --- LOGIKA PEMBUATAN SINYAL (CORE LOGIC) ---
# Membuat sumbu waktu
N = int(sampling_rate * duration)
t = np.linspace(0.0, duration, N, endpoint=False)

# 1. Sinyal Fundamental (50Hz murni) - Representasi Listrik PLN/Genset
signal_pure = 100 * np.sin(2 * np.pi * freq_fundamental * t)

# 2. Sinyal Gangguan (Sidebands) - Representasi Broken Rotor Bar
# Biasanya muncul di frekuensi (Fund - slip) dan (Fund + slip)
# Kita asumsikan sideband muncul di 45Hz dan 55Hz
sideband_freq_1 = freq_fundamental - 5
sideband_freq_2 = freq_fundamental + 5
signal_fault = (fault_severity * 2) * np.sin(2 * np.pi * sideband_freq_1 * t) + \
               (fault_severity * 2) * np.sin(2 * np.pi * sideband_freq_2 * t)

# 3. Noise (Gangguan Acak)
noise = np.random.normal(0, noise_level * 10, N)

# Sinyal Total (Yang ditangkap sensor)
signal_total = signal_pure + signal_fault + noise

# --- PROSES FFT (TRANSFORMASI SINYAL) ---
yf = fft(signal_total)
xf = fftfreq(N, 1 / sampling_rate)
# Ambil setengah spektrum saja (positif)
xf = xf[:N//2]
amplitude = 2.0/N * np.abs(yf[0:N//2])

# Ubah ke dB (Logarithmic scale) agar mirip alat ESA asli
# Menghindari log(0)
amplitude_db = 20 * np.log10(amplitude + 1e-6) 

# --- VISUALISASI DASHBOARD ---

col1, col2 = st.columns(2)

# GRAFIK 1: TIME DOMAIN (GELOMBANG SINUS)
with col1:
    st.subheader("1. Time Domain (Bentuk Gelombang)")
    st.caption("Ini adalah tampilan gelombang arus listrik mentah.")
    fig_time = go.Figure()
    # Tampilkan hanya 0.1 detik pertama agar gelombang terlihat jelas
    subset_n = int(0.1 * sampling_rate) 
    fig_time.add_trace(go.Scatter(x=t[:subset_n], y=signal_total[:subset_n], mode='lines', name='Arus Aktual', line=dict(color='#00CC96')))
    fig_time.update_layout(yaxis_title='Amplitudo (Ampere)', xaxis_title='Waktu (Detik)', height=400)
    st.plotly_chart(fig_time, use_container_width=True)

# GRAFIK 2: FREQUENCY DOMAIN (FFT SPECTRUM)
with col2:
    st.subheader("2. Frequency Domain (Analisa ESA)")
    st.caption("Ini adalah hasil FFT. Perhatikan 'Sidebands' saat kerusakan dinaikkan.")
    fig_fft = go.Figure()
    
    # Plot Spektrum
    fig_fft.add_trace(go.Scatter(x=xf, y=amplitude_db, mode='lines', name='Spektrum Frekuensi', line=dict(color='#EF553B')))
    
    # Zoom area sekitar 50Hz (fokus area analisa)
    fig_fft.update_xaxes(range=[30, 70]) 
    fig_fft.update_yaxes(range=[-20, 50]) # Sesuaikan range dB
    
    # Anotasi Penjelasan
    fig_fft.add_vline(x=50, line_dash="dash", line_color="green", annotation_text="50Hz (Main)")
    
    if fault_severity > 2:
        fig_fft.add_vline(x=45, line_dash="dot", line_color="red", annotation_text="Sideband L")
        fig_fft.add_vline(x=55, line_dash="dot", line_color="red", annotation_text="Sideband R")
        st.error(f"⚠️ PERINGATAN: Terdeteksi pola Sidebands! Indikasi gangguan rotor. (Severity: {fault_severity}/10)")
    else:
        st.success("✅ STATUS MOTOR: NORMAL. Tidak ada frekuensi gangguan signifikan.")

    fig_fft.update_layout(yaxis_title='Amplitudo (dB)', xaxis_title='Frekuensi (Hz)', height=400)
    st.plotly_chart(fig_fft, use_container_width=True)

# --- FOOTER ---
with st.expander("ℹ️ Cara Membaca Simulasi Ini"):
    st.markdown("""
    1. **Grafik Kiri (Time Domain):** Adalah apa yang dilihat mata biasa. Sulit membedakan motor sehat vs rusak hanya dari sini, kecuali rusaknya parah sekali.
    2. **Grafik Kanan (Frequency Domain):** Adalah "Mata ESA". 
       - Tiang tengah hijau adalah frekuensi listrik PLN (50Hz).
       - Saat slider **Severity** digeser naik, akan muncul tiang merah kecil di kiri (45Hz) dan kanan (55Hz). 
       - Inilah yang disebut **Sidebands**, tanda khas kerusakan batang rotor (Broken Rotor Bar).
    """)
