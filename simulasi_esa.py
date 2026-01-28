import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq
import time

# --- FUNGSI FFT ---
def perform_esa_analysis(signal_data, fs):
    N = len(signal_data)
    yf = fft(signal_data)
    xf = fftfreq(N, 1 / fs)
    xf = xf[:N//2]
    amplitude = 2.0/N * np.abs(yf[0:N//2])
    amplitude_db = 20 * np.log10(amplitude + 1e-6)
    return xf, amplitude_db

# --- SETUP HALAMAN ---
st.set_page_config(layout="wide", page_title="ESA All-in-One Simulator")

st.title("⚡ ESA Multi-Fault Simulator")
st.markdown("**Infrastructure Management - Pertamina Patra Niaga**")
st.markdown("Prototype simulasi diagnosa 4 kondisi utama motor listrik.")

# --- SIDEBAR KONTROL UTAMA ---
st.sidebar.header("⚙️ Panel Kontrol")

# Pilihan Skenario Kerusakan
fault_type = st.sidebar.radio(
    "Pilih Skenario Diagnosa:",
    ("1. Motor Sehat (Healthy)", 
     "2. Broken Rotor Bar", 
     "3. Bearing Fault", 
     "4. Power Harmonics")
)

st.sidebar.divider()
severity = st.sidebar.slider("Tingkat Keparahan (Severity)", 0.0, 10.0, 0.0)
noise_level = st.sidebar.slider("Level Noise Lapangan", 0.0, 1.0, 0.1)

# --- LOGIKA GENERATOR SINYAL ---
def generate_signal(fault_mode, sev, noise, duration=1.0, fs=2000):
    t = np.linspace(0.0, duration, int(fs * duration), endpoint=False)
    
    # 1. Fundamental (50Hz) - Selalu ada
    sig = 100 * np.sin(2 * np.pi * 50 * t)
    
    # 2. Logika Sesuai Mode
    if "Sehat" in fault_mode:
        # Tidak ada tambahan sinyal gangguan
        pass
        
    elif "Rotor Bar" in fault_mode:
        # Sidebands dekat (45Hz & 55Hz)
        # Rumus: 50 +/- (2 * slip_freq)
        sb_amp = sev * 2.5 # Pengali amplitudo
        sig += sb_amp * np.sin(2 * np.pi * 45 * t)
        sig += sb_amp * np.sin(2 * np.pi * 55 * t)
        
    elif "Bearing" in fault_mode:
        # Bearing biasanya memodulasi di frekuensi mekanis (bukan kelipatan slip)
        # Kita simulasikan di 30Hz & 70Hz (jarak 20Hz dari fundamental)
        # Dan menambahkan 'Broadband Noise' (lantai noise naik)
        bearing_amp = sev * 1.5
        sig += bearing_amp * np.sin(2 * np.pi * 30 * t) # Outer Race freq simulation
        sig += bearing_amp * np.sin(2 * np.pi * 70 * t)
        # Bearing rusak sering membuat sinyal terlihat 'kasar'
        noise = noise * (1 + (sev/5)) 
        
    elif "Harmonics" in fault_mode:
        # Harmonisa kelipatan ganjil: 3rd (150Hz) dan 5th (250Hz)
        # Ini merusak bentuk gelombang sinus (Distorsi)
        h3_amp = sev * 3.0
        h5_amp = sev * 1.5
        sig += h3_amp * np.sin(2 * np.pi * 150 * t)
        sig += h5_amp * np.sin(2 * np.pi * 250 * t)

    # 3. Tambahkan Noise Random
    sig += np.random.normal(0, noise * 5, len(t))
    
    return t, sig

# --- GENERATE DATA UTAMA ---
fs = 2000
t, signal_total = generate_signal(fault_type, severity, noise_level, duration=0.2, fs=fs) # Durasi pendek untuk zoom view
_, signal_full = generate_signal(fault_type, severity, noise_level, duration=1.0, fs=fs) # Durasi panjang untuk FFT akurat

# Analisa FFT
xf, y_db = perform_esa_analysis(signal_full, fs)

# --- VISUALISASI ---
col1, col2 = st.columns([1, 1])

# GRAFIK 1: TIME DOMAIN (BENTUK GELOMBANG)
with col1:
    st.subheader("1. Time Domain (Bentuk Gelombang)")
    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(x=t, y=signal_total, mode='lines', name='Arus', line=dict(color='#00CC96')))
    
    # Anotasi Edukasi Time Domain
    if "Harmonics" in fault_type and severity > 3:
        st.caption("Perhatikan: Gelombang tidak lagi sinus mulus, tapi 'penyok' akibat harmonisa.")
    elif "Bearing" in fault_type and severity > 3:
        st.caption("Perhatikan: Gelombang terlihat kasar/berbulu akibat getaran bearing.")
    else:
        st.caption("Gelombang arus listrik (Zoom 0.2 detik).")
        
    fig_time.update_layout(height=400, xaxis_title="Waktu (s)", yaxis_title="Amper (A)")
    st.plotly_chart(fig_time, use_container_width=True)

# GRAFIK 2: FREQUENCY DOMAIN (SPEKTRUM ESA)
with col2:
    st.subheader("2. Frequency Domain (Diagnosa)")
    fig_fft = go.Figure()
    fig_fft.add_trace(go.Scatter(x=xf, y=y_db, mode='lines', name='Spectrum', line=dict(color='#EF553B')))
    
    # Marker 50Hz
    fig_fft.add_vline(x=50, line_dash="dash", line_color="green", annotation_text="50Hz")
    
    # Logika Zoom & Marker berdasarkan Fault Type
    if "Rotor" in fault_type:
        st.caption("Diagnosa: Perhatikan **Sidebands** kembar yang muncul mengapit 50Hz.")
        fig_fft.update_xaxes(range=[30, 70]) # Zoom dekat
        if severity > 1:
            fig_fft.add_vline(x=45, line_dash="dot", line_color="red", annotation_text="L-Side")
            fig_fft.add_vline(x=55, line_dash="dot", line_color="red", annotation_text="R-Side")
            
    elif "Bearing" in fault_type:
        st.caption("Diagnosa: Perhatikan frekuensi gangguan mekanis (biasanya lebih lebar dari sideband rotor).")
        fig_fft.update_xaxes(range=[0, 100]) # Zoom medium
        if severity > 1:
            fig_fft.add_vline(x=30, line_dash="dot", line_color="orange", annotation_text="Bearing Freq")
            fig_fft.add_vline(x=70, line_dash="dot", line_color="orange", annotation_text="Bearing Freq")

    elif "Harmonics" in fault_type:
        st.caption("Diagnosa: Perhatikan munculnya tiang di kelipatan 50Hz (150Hz, 250Hz).")
        fig_fft.update_xaxes(range=[0, 300]) # Zoom jauh (Wideband)
        if severity > 1:
            fig_fft.add_vline(x=150, line_dash="dot", line_color="purple", annotation_text="3rd Harm")
            fig_fft.add_vline(x=250, line_dash="dot", line_color="purple", annotation_text="5th Harm")
            
    else: # Sehat
        st.caption("Diagnosa: Spektrum bersih. Hanya ada satu puncak dominan di 50Hz.")
        fig_fft.update_xaxes(range=[0, 100])

    fig_fft.update_yaxes(range=[-40, 80], title="Amplitude (dB)")
    fig_fft.update_layout(height=400, xaxis_title="Frekuensi (Hz)")
    st.plotly_chart(fig_fft, use_container_width=True)

# --- PENJELASAN TEKNIS (Expandable) ---
with st.expander("📘 Penjelasan Teknis & Rumus Diagnosa"):
    st.markdown("""
    ### Panduan Membaca Grafik
    
    **1. Motor Sehat (Healthy)**
    * **Grafik:** Bersih, hanya ada satu tiang tinggi di **50Hz**.
    * **Arti:** Listrik murni, motor berputar presisi.
    
    **2. Broken Rotor Bar**
    * **Grafik:** Muncul "pengawal" kecil di kiri-kanan 50Hz (misal 45Hz & 55Hz).
    * **Rumus:** $F_{sideband} = F_{line} \pm (2 \times Slip)$.
    * **Bahaya:** Rotor panas berlebih, bisa melukai stator (konslet).
    
    **3. Bearing Fault**
    * **Grafik:** Muncul frekuensi aneh (bukan kelipatan 50) atau noise lantai naik.
    * **Fisika:** Bola bearing yang cacat memukul dinding race, memodulasi celah udara.
    * **Bahaya:** Motor macet (jammed), as patah.
    
    **4. Harmonics (Kualitas Daya)**
    * **Grafik:** Muncul tiang di 150Hz (Harmonisa ke-3), 250Hz (ke-5), dst.
    * **Fisika:** Akibat beban non-linear (VSD, Lampu LED besar, Rectifier).
    * **Bahaya:** Motor cepat panas (overheat) meski beban ringan.
    """)
