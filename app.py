import streamlit as st
import numpy as np
import pandas as pd
import scipy.fftpack
from scipy.signal import find_peaks, windows
import plotly.graph_objects as go

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="MCSA Analyzer", layout="wide")

st.title("🔩 Motor Current Signature Analysis (MCSA) Tool")
st.markdown("""
Aplikasi ini mengimplementasikan prinsip dasar dari jurnal *Review of Motor Current Signature Analysis*.
Metode utama: **Fast Fourier Transform (FFT)** untuk mendeteksi frekuensi kerusakan (sidebands) di sekitar frekuensi fundamental (Line Frequency).
""")

# --- Sidebar: Konfigurasi ---
st.sidebar.header("1. Input Data")
data_source = st.sidebar.radio("Sumber Data:", ("Gunakan Data Dummy (Simulasi)", "Upload File CSV"))

# Parameter Global
fs = st.sidebar.number_input("Sampling Frequency (Hz)", value=1000, min_value=100, help="Frekuensi pengambilan data sensor")
line_freq = st.sidebar.number_input("Line Frequency (Hz)", value=50.0, step=10.0, help="Frekuensi jala-jala listrik (biasanya 50Hz atau 60Hz)")

# --- Fungsi Generate Data Dummy ---
def generate_dummy_signal(fs, duration=2, fault=False):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    # Fundamental component (Line Frequency)
    signal = 10 * np.sin(2 * np.pi * line_freq * t)
    
    # Noise
    noise = np.random.normal(0, 0.5, size=len(t))
    
    signal = signal + noise
    
    if fault:
        # Simulasi Broken Rotor Bar: Sidebands di sekitar fundamental
        # f_sb = f_s (1 ± 2s) -> misal slip s=0.05
        slip = 0.05
        f_sb_left = line_freq * (1 - 2*slip) # 45 Hz
        f_sb_right = line_freq * (1 + 2*slip) # 55 Hz
        
        # Tambahkan sinyal kecil di frekuensi sideband (amplitude lebih rendah)
        signal += 0.8 * np.sin(2 * np.pi * f_sb_left * t)
        signal += 0.8 * np.sin(2 * np.pi * f_sb_right * t)
        
    return t, signal

# --- Logika Load Data ---
current_data = None
time_data = None

if data_source == "Gunakan Data Dummy (Simulasi)":
    st.sidebar.subheader("Simulasi Kerusakan")
    is_faulty = st.sidebar.checkbox("Simulasikan Motor Rusak (Sidebands)", value=True)
    duration = st.sidebar.slider("Durasi Sinyal (detik)", 1, 10, 2)
    time_data, current_data = generate_dummy_signal(fs, duration, is_faulty)
    st.info(f"Menggunakan data simulasi ({'Rusak' if is_faulty else 'Sehat'}).")

else:
    uploaded_file = st.sidebar.file_uploader("Upload CSV (Kolom harus berisi data arus)", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        # Asumsi kolom pertama adalah data
        try:
            current_data = df.iloc[:, 0].values
            # Buat array waktu berdasarkan sampling rate
            time_data = np.arange(len(current_data)) / fs
            st.success("File berhasil dimuat.")
        except Exception as e:
            st.error(f"Error membaca file: {e}")

# --- Proses Analisis ---
if current_data is not None:
    # 1. Plot Time Domain
    st.subheader("2. Time Domain Analysis")
    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(x=time_data[:1000], y=current_data[:1000], mode='lines', name='Current (Amp)'))
    fig_time.update_layout(title="Waveform Arus (Zoomed - 1000 sample awal)", xaxis_title="Waktu (s)", yaxis_title="Amplitudo (A)")
    st.plotly_chart(fig_time, use_container_width=True)

    # 2. Proses FFT
    st.subheader("3. Frequency Domain Analysis (FFT Spectrum)")
    
    # Mengurangi DC Offset
    signal_ac = current_data - np.mean(current_data)
    
    # Menerapkan Windowing (Hanning) untuk mengurangi spectral leakage
    N = len(signal_ac)
    window = windows.hann(N)
    signal_windowed = signal_ac * window
    
    # Hitung FFT
    yf = scipy.fftpack.fft(signal_windowed)
    xf = np.linspace(0.0, 1.0/(2.0*(1/fs)), N//2)
    
    # Normalisasi Amplitudo
    amplitude = 2.0/N * np.abs(yf[:N//2])
    
    # Konversi ke Decibel (dB) - Standar MCSA
    # Menghindari log(0)
    amplitude_db = 20 * np.log10(amplitude + 1e-6)

    # 3. Plot FFT
    fig_fft = go.Figure()
    fig_fft.add_trace(go.Scatter(x=xf, y=amplitude_db, mode='lines', name='Spectrum (dB)'))
    
    # Highlight Fundamental Frequency
    fig_fft.add_vline(x=line_freq, line_width=2, line_dash="dash", line_color="green", annotation_text="Line Freq")

    # Layout FFT
    max_freq_view = st.sidebar.slider("Max Frequency View (Hz)", 0, int(fs/2), 100)
    fig_fft.update_layout(
        title="Power Spectral Density (MCSA Spectrum)",
        xaxis_title="Frekuensi (Hz)",
        yaxis_title="Amplitudo (dB)",
        xaxis_range=[0, max_freq_view]
    )
    st.plotly_chart(fig_fft, use_container_width=True)

    # 4. Analisis Sidebands (Otomatis)
    st.markdown("### 4. Analisis Sidebands")
    st.write("Berdasarkan jurnal, kerusakan rotor sering muncul sebagai sidebands di: $f_{sb} = f_s(1 \pm 2ks)$")
    
    # Cari peaks di sekitar frekuensi jala-jala
    peaks, _ = find_peaks(amplitude, height=np.max(amplitude)*0.05) # Cari peak minimal 5% dari max
    
    found_peaks_df = pd.DataFrame({
        "Frekuensi (Hz)": xf[peaks],
        "Amplitudo (Linear)": amplitude[peaks],
        "Amplitudo (dB)": amplitude_db[peaks]
    })
    
    # Filter hanya peak di area visual
    found_peaks_df = found_peaks_df[found_peaks_df["Frekuensi (Hz)"] <= max_freq_view]
    found_peaks_df = found_peaks_df.sort_values(by="Amplitudo (Linear)", ascending=False).reset_index(drop=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Top Peaks Detected:**")
        st.dataframe(found_peaks_df.head(5))
    
    with col2:
        st.info("""
        **Cara Membaca:**
        1. Peak tertinggi haruslah **Line Frequency** (misal 50Hz).
        2. Jika ada peak signifikan di kanan/kiri 50Hz (misal 45Hz dan 55Hz), itu indikasi **Broken Rotor Bar** atau masalah beban.
        3. Gunakan skala **dB** untuk melihat perbedaan magnitude antara fundamental dan noise/fault.
        """)

else:
    st.warning("Silakan pilih sumber data atau upload file CSV untuk memulai.")

# Footer
st.markdown("---")
st.caption("Referensi: Brief Review of Motor Current Signature Analysis (ResearchGate). Code generated for Streamlit implementation.")
