import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq
from scipy.signal import windows

# --- Konfigurasi Halaman ---
st.set_page_config(layout="wide", page_title="ESA Analyzer Dashboard")

st.title("⚡ Electrical Signature Analysis (ESA) Simulator")
st.markdown("""
Aplikasi ini mensimulasikan analisis sinyal arus (MCSA) berdasarkan prinsip ESA.
Kita akan melihat bagaimana **Fast Fourier Transform (FFT)** mengubah sinyal waktu menjadi spektrum frekuensi untuk mendeteksi anomali.
""")

# --- Sidebar: Parameter Simulasi ---
st.sidebar.header("⚙️ Parameter Sinyal")

# Parameter Dasar
fs = st.sidebar.number_input("Sampling Rate (Hz)", value=4096, min_value=1000, step=100)
duration = st.sidebar.number_input("Durasi Sinyal (detik)", value=2.0, min_value=0.1, step=0.1)
f_fund = st.sidebar.number_input("Frekuensi Fundamental (Hz)", value=50.0, step=0.1)
amp_fund = 10.0 # Amplitudo sinyal utama (Ampere)

# Parameter Gangguan (Fault Injection)
st.sidebar.markdown("---")
st.sidebar.header("⚠️ Injeksi Kerusakan (Fault)")
add_noise = st.sidebar.checkbox("Tambahkan Noise Putih", value=True)
noise_level = st.sidebar.slider("Level Noise", 0.0, 1.0, 0.1) if add_noise else 0

add_fault = st.sidebar.checkbox("Simulasi Kerusakan (Sidebands)", value=False)
if add_fault:
    fault_type = st.sidebar.selectbox("Jenis Kerusakan", 
                                      ["Broken Rotor Bar", "Bearing Fault", "Eccentricity"])
    
    # Frekuensi kerusakan simulasi (offset dari fundamental)
    if fault_type == "Broken Rotor Bar":
        f_fault_offset = st.sidebar.slider("Slip Frequency Offset (Hz)", 0.5, 5.0, 2.1)
        fault_amp = 0.5
    elif fault_type == "Bearing Fault":
        f_fault_offset = st.sidebar.slider("Bearing Freq Offset (Hz)", 10.0, 100.0, 25.0)
        fault_amp = 0.3
    else:
        f_fault_offset = st.sidebar.slider("Eccentricity Offset (Hz)", 1.0, 25.0, 12.5)
        fault_amp = 0.4
else:
    f_fault_offset = 0
    fault_amp = 0

# --- Fungsi Generator Sinyal ---
def generate_signal(fs, duration, f_fund, amp_fund, noise_level, add_fault, f_fault_offset, fault_amp):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    
    # 1. Sinyal Fundamental (Gelombang Sinus Murni 50/60Hz)
    signal = amp_fund * np.sin(2 * np.pi * f_fund * t)
    
    # 2. Menambahkan Noise
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, len(t))
        signal += noise
        
    # 3. Menambahkan Frekuensi Kerusakan (Simulasi Sideband)
    # Kerusakan biasanya muncul sebagai sideband di f_fund ± f_fault
    if add_fault:
        # Sideband Kiri
        signal += fault_amp * np.sin(2 * np.pi * (f_fund - f_fault_offset) * t)
        # Sideband Kanan
        signal += fault_amp * np.sin(2 * np.pi * (f_fund + f_fault_offset) * t)
        
    return t, signal

# Generate Data
t, signal = generate_signal(fs, duration, f_fund, amp_fund, noise_level, add_fault, f_fault_offset, fault_amp)

# --- Proses FFT (Electrical Signature Analysis) ---
# Menggunakan Windowing untuk mengurangi spectral leakage
N = len(signal)
window = windows.hann(N) 
signal_windowed = signal * window

# Hitung FFT
yf = fft(signal_windowed)
xf = fftfreq(N, 1 / fs)

# Ambil setengah spektrum (positif saja)
half_N = N // 2
xf_plot = xf[:half_N]
yf_plot = 2.0/N * np.abs(yf[:half_N]) # Normalisasi Amplitudo

# Konversi ke Desibel (dB) - Standar di ESA
# Menghindari log(0) dengan menambahkan epsilon kecil
yf_db = 20 * np.log10(yf_plot + 1e-12)

# --- Visualisasi ---

# Tab Layout
tab1, tab2 = st.tabs(["📈 Domain Waktu (Raw Signal)", "📊 Domain Frekuensi (Spectrum ESA)"])

with tab1:
    st.subheader("Sinyal Arus Mentah (Time Domain)")
    st.write("Ini adalah representasi sinyal listrik yang dibaca oleh sensor.")
    
    # Plot hanya sebagian kecil data agar tidak berat (zoom in 0.1 detik pertama)
    zoom_samples = int(fs * 0.2) 
    
    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(x=t[:zoom_samples], y=signal[:zoom_samples], mode='lines', name='Current (A)'))
    fig_time.update_layout(
        xaxis_title="Waktu (detik)",
        yaxis_title="Amplitudo (Ampere)",
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig_time, use_container_width=True)

with tab2:
    st.subheader("Analisis Spektrum (Frequency Domain)")
    st.write(f"""
    Grafik ini adalah hasil FFT. Dalam ESA, kita mencari puncak di luar frekuensi fundamental ({f_fund} Hz).
    Jika Anda mengaktifkan 'Simulasi Kerusakan', perhatikan munculnya puncak kecil di sisi kiri dan kanan puncak utama.
    """)
    
    fig_fft = go.Figure()
    
    # Plot Spectrum
    fig_fft.add_trace(go.Scatter(
        x=xf_plot, 
        y=yf_db, 
        mode='lines', 
        name='Spectrum (dB)',
        line=dict(color='firebrick', width=1.5)
    ))
    
    # Marker Fundamental
    fig_fft.add_vline(x=f_fund, line_width=1, line_dash="dash", line_color="green", annotation_text="Fund", annotation_position="top right")

    # Marker Kerusakan (jika aktif)
    if add_fault:
        fault_left = f_fund - f_fault_offset
        fault_right = f_fund + f_fault_offset
        
        fig_fft.add_vline(x=fault_left, line_width=1, line_dash="dot", line_color="orange")
        fig_fft.add_vline(x=fault_right, line_width=1, line_dash="dot", line_color="orange")
        
        fig_fft.add_annotation(x=fault_right, y=max(yf_db), text="Fault Sideband", showarrow=True, arrowhead=1)

    # Fokus pada range frekuensi yang relevan (0 - 150Hz biasanya cukup untuk ESA dasar)
    fig_fft.update_xaxes(range=[0, f_fund * 4]) 
    fig_fft.update_layout(
        xaxis_title="Frekuensi (Hz)",
        yaxis_title="Magnitude (dB)",
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    st.plotly_chart(fig_fft, use_container_width=True)

# --- Penjelasan Singkat ---
st.markdown("---")
st.markdown("""
### Cara Membaca Hasil ESA
1.  **Puncak Tertinggi (Hijau):** Ini adalah frekuensi jala-jala listrik (Line Frequency), biasanya 50Hz di Indonesia/Eropa atau 60Hz di AS.
2.  **Noise Floor:** Bagian bawah grafik yang acak. Semakin tinggi noise, semakin sulit mendeteksi kerusakan dini.
3.  **Sidebands (Oranye):** Dalam ESA, kerusakan (seperti batang rotor patah) memodulasi arus, menciptakan frekuensi "hantu" di:
    $$ f_{sideband} = f_{fund} \pm k \cdot f_{fault} $$
    Jika Anda melihat puncak simetris di sekitar frekuensi utama, itu indikasi kuat adanya masalah mekanis atau elektrik.
""")
