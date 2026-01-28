import streamlit as st
import numpy as np
import pandas as pd
import scipy.fftpack
from scipy.signal import find_peaks, windows
import plotly.graph_objects as go

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Simulasi ESA - Auto Tracking", layout="wide")

st.title("🔩 Simulasi ESA: Auto-Tracking Fundamental Frequency")
st.markdown("""
**Status:** ✅ Fixed. Zona deteksi kini **otomatis mengikuti** pergeseran frekuensi fundamental.
""")

# --- Sidebar: Konfigurasi ---
st.sidebar.header("1. Input Data")
data_source = st.sidebar.radio("Sumber Data:", ("Gunakan Data Dummy (Simulasi)", "Upload File CSV"))

# Parameter Global
st.sidebar.markdown("### Parameter Sinyal")
fs = st.sidebar.number_input("Sampling Frequency (Hz)", value=2000, min_value=100)
line_freq_input = st.sidebar.number_input("Referensi Line Freq (Hz)", value=50.0, step=10.0, help="Hanya untuk referensi visual awal.")

st.sidebar.markdown("### Tuning Deteksi")
sensitivity = st.sidebar.slider("Sensitivitas Deteksi (%)", 0.1, 10.0, 1.0)
threshold_ratio = sensitivity / 100.0 

# --- Fungsi Generate Data Dummy ---
def generate_dummy_signal(fs, duration=2, fault=False):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    # Fundamental agak digeser sedikit dari 50Hz (misal 49.5Hz) untuk tes fitur tracking
    actual_fund = 49.5 
    signal = 10 * np.sin(2 * np.pi * actual_fund * t) 
    noise = np.random.normal(0, 0.2, size=len(t))
    signal = signal + noise
    
    if fault:
        # Sidebands relative terhadap actual_fund
        slip = 0.03
        f_sb_left = actual_fund * (1 - 2*slip) 
        f_sb_right = actual_fund * (1 + 2*slip)
        signal += 0.5 * np.sin(2 * np.pi * f_sb_left * t)
        signal += 0.5 * np.sin(2 * np.pi * f_sb_right * t)
        
    return t, signal

# --- Logika Load Data ---
current_data = None

if data_source == "Gunakan Data Dummy (Simulasi)":
    st.sidebar.subheader("Simulasi")
    is_faulty = st.sidebar.checkbox("Simulasikan Motor Rusak", value=True)
    duration = st.sidebar.slider("Durasi (detik)", 1, 10, 5)
    _, current_data = generate_dummy_signal(fs, duration, is_faulty)
    st.info(f"Menggunakan data simulasi (Fundamental diset ke 49.5Hz untuk tes tracking).")

else:
    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Upload CSV (Kolom 1: Arus)", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            current_data = df.iloc[:, 0].values
            st.success(f"File dimuat. Total sampel: {len(current_data)}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Proses Analisis Utama ---
if current_data is not None:
    
    # 1. FFT Processing
    signal_ac = current_data - np.mean(current_data)
    N = len(signal_ac)
    window = windows.hann(N)
    signal_windowed = signal_ac * window
    
    yf = scipy.fftpack.fft(signal_windowed)
    xf = np.linspace(0.0, 1.0/(2.0*(1/fs)), N//2)
    amplitude = 2.0/N * np.abs(yf[:N//2])
    amplitude_db = 20 * np.log10(amplitude + 1e-6)

    # --- 2. LOGIKA AUTO-TRACKING (BARU) ---
    # Cari index amplitudo tertinggi (Asumsi: Fundamental adalah sinyal terkuat)
    max_peak_idx = np.argmax(amplitude)
    center_freq = xf[max_peak_idx] # <--- INI PUSAT BARU KITA
    max_amp_val = amplitude[max_peak_idx]

    # Validasi sederhana: Apakah peak yang ketemu masuk akal? (Dekat input user)
    freq_drift = abs(center_freq - line_freq_input)
    drift_warning = ""
    if freq_drift > 10.0:
        drift_warning = f"⚠️ Warning: Puncak terdeteksi ({center_freq:.2f}Hz) jauh dari referensi ({line_freq_input}Hz). Cek Sampling Freq."

    st.subheader("Analisis Spektrum Frekuensi")
    st.caption(f"📍 Center Frequency Terdeteksi (Fundamental): **{center_freq:.2f} Hz** {drift_warning}")

    # 3. Peak Detection (Relatif terhadap max_amp_val)
    peaks, _ = find_peaks(amplitude, height=max_amp_val * threshold_ratio)
    
    df_peaks = pd.DataFrame({
        "Freq (Hz)": xf[peaks],
        "Amp (Linear)": amplitude[peaks],
        "Amp (dB)": amplitude_db[peaks]
    })
    
    # 4. Plotting
    fig_fft = go.Figure()
    fig_fft.add_trace(go.Scatter(x=xf, y=amplitude_db, mode='lines', name='Spectrum', line=dict(color='firebrick', width=1)))
    
    # Marker Peaks
    fig_fft.add_trace(go.Scatter(
        x=df_peaks["Freq (Hz)"], 
        y=df_peaks["Amp (dB)"], 
        mode='markers', marker=dict(size=8, color='yellow', symbol='x'), name='Peaks'
    ))

    # --- VISUALISASI ZONA (Dinamis mengikuti center_freq) ---
    search_range = 8.0 # Lebar zona pencarian
    buffer = 1.0       # Jarak aman dari pusat

    # Zona Kiri (Merah Transparan)
    fig_fft.add_vrect(
        x0=center_freq - search_range, 
        x1=center_freq - buffer, 
        fillcolor="red", opacity=0.1, 
        annotation_text="Left Zone", annotation_position="top left"
    )
    # Zona Kanan (Merah Transparan)
    fig_fft.add_vrect(
        x0=center_freq + buffer, 
        x1=center_freq + search_range, 
        fillcolor="red", opacity=0.1, 
        annotation_text="Right Zone", annotation_position="top right"
    )
    # Garis Pusat (Hijau)
    fig_fft.add_vline(x=center_freq, line_dash="dash", line_color="green", annotation_text="Center")

    max_view = st.sidebar.slider("Zoom Frekuensi (Hz)", 0, 200, 100)
    fig_fft.update_layout(xaxis_range=[0, max_view], title="Spectrum Analysis", yaxis_title="dB", xaxis_title="Hz")
    st.plotly_chart(fig_fft, use_container_width=True)

    # 5. DIAGNOSA LOGIC (Menggunakan center_freq)
    st.markdown("### Hasil Diagnosa Otomatis")
    
    # Query menggunakan center_freq, BUKAN line_freq_input
    left_sidebands = df_peaks[
        (df_peaks["Freq (Hz)"] >= center_freq - search_range) & 
        (df_peaks["Freq (Hz)"] <= center_freq - buffer)
    ]
    
    right_sidebands = df_peaks[
        (df_peaks["Freq (Hz)"] >= center_freq + buffer) & 
        (df_peaks["Freq (Hz)"] <= center_freq + search_range)
    ]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Left Sidebands** ({center_freq - search_range:.1f} - {center_freq - buffer:.1f} Hz):")
        if not left_sidebands.empty:
            st.dataframe(left_sidebands[["Freq (Hz)", "Amp (Linear)"]])
        else:
            st.write("*Tidak ada peak*")
            
        st.write(f"**Right Sidebands** ({center_freq + buffer:.1f} - {center_freq + search_range:.1f} Hz):")
        if not right_sidebands.empty:
            st.dataframe(right_sidebands[["Freq (Hz)", "Amp (Linear)"]])
        else:
            st.write("*Tidak ada peak*")

    with col2:
        if not left_sidebands.empty or not right_sidebands.empty:
            st.error("⚠️ **DIAGNOSA: INDIKASI KERUSAKAN**")
            st.write(f"Ditemukan sideband di sekitar frekuensi fundamental aktual (**{center_freq:.2f} Hz**).")
            st.write("Sistem mendeteksi adanya peak di zona merah yang bergeser mengikuti fundamental.")
        else:
            st.success("✅ **DIAGNOSA: MOTOR SEHAT**")
            st.write(f"Area di sekitar fundamental aktual ({center_freq:.2f} Hz) bersih.")

else:
    st.info("Upload file CSV untuk memulai.")
