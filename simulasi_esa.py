import streamlit as st
import numpy as np
import pandas as pd
import scipy.fftpack
from scipy.signal import find_peaks, windows
import plotly.graph_objects as go

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Simulasi ESA - MCSA Tool (Fixed)", layout="wide")

st.title("🔩 Simulasi ESA: Motor Current Signature Analysis")
st.markdown("""
**Status:** Perbaikan Logika Deteksi & Sensitivitas.
Pastikan **Sampling Frequency** di Sidebar sesuai dengan data Anda (Data dummy tadi menggunakan **2000 Hz**).
""")

# --- Sidebar: Konfigurasi ---
st.sidebar.header("1. Input Data")
data_source = st.sidebar.radio("Sumber Data:", ("Gunakan Data Dummy (Simulasi)", "Upload File CSV"))

# Parameter Global
st.sidebar.markdown("### Parameter Sinyal")
# DEFAULT DIUBAH KE 2000 AGAR COCOK DENGAN DATA DUMMY
fs = st.sidebar.number_input("Sampling Frequency (Hz)", value=2000, min_value=100, help="Sangat PENTING! Harus sama dengan setting saat data direkam/dibuat.")
line_freq = st.sidebar.number_input("Line Frequency (Hz)", value=50.0, step=10.0)

st.sidebar.markdown("### Tuning Deteksi")
# Slider sensitivitas (Threshold)
sensitivity = st.sidebar.slider("Sensitivitas Deteksi (%)", 0.1, 10.0, 1.0, help="Semakin kecil %, semakin sensitif mendeteksi peak kecil.")
threshold_ratio = sensitivity / 100.0 

# --- Fungsi Generate Data Dummy ---
def generate_dummy_signal(fs, duration=2, fault=False):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    signal = 10 * np.sin(2 * np.pi * line_freq * t) # Fundamental
    noise = np.random.normal(0, 0.2, size=len(t))
    signal = signal + noise
    
    if fault:
        # Sidebands di 48Hz dan 52Hz (jika line=50)
        slip = 0.02 # Slip buatan agar sideband di +/- 2Hz
        f_sb_left = line_freq * (1 - 2*slip) 
        f_sb_right = line_freq * (1 + 2*slip)
        signal += 0.5 * np.sin(2 * np.pi * f_sb_left * t)
        signal += 0.5 * np.sin(2 * np.pi * f_sb_right * t)
        
    return t, signal

# --- Logika Load Data ---
current_data = None
time_data = None

if data_source == "Gunakan Data Dummy (Simulasi)":
    st.sidebar.subheader("Simulasi Kerusakan")
    is_faulty = st.sidebar.checkbox("Simulasikan Motor Rusak", value=True)
    duration = st.sidebar.slider("Durasi Sinyal (detik)", 1, 10, 5) # Default durasi diperpanjang agar resolusi bagus
    time_data, current_data = generate_dummy_signal(fs, duration, is_faulty)
    st.info(f"Mode Simulasi Aktif. Kondisi: {'⚠️ RUSAK' if is_faulty else '✅ SEHAT'}")

else:
    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Upload CSV (Kolom 1: Arus)", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            current_data = df.iloc[:, 0].values
            time_data = np.arange(len(current_data)) / fs
            st.success(f"File dimuat. Total sampel: {len(current_data)}")
        except Exception as e:
            st.error(f"Error membaca file CSV: {e}")

# --- Proses Analisis Utama ---
if current_data is not None:
    
    # 1. FFT Processing
    st.subheader("Analisis Spektrum Frekuensi")
    
    # Remove DC & Windowing
    signal_ac = current_data - np.mean(current_data)
    N = len(signal_ac)
    window = windows.hann(N)
    signal_windowed = signal_ac * window
    
    # FFT Calculation
    yf = scipy.fftpack.fft(signal_windowed)
    xf = np.linspace(0.0, 1.0/(2.0*(1/fs)), N//2)
    amplitude = 2.0/N * np.abs(yf[:N//2])
    amplitude_db = 20 * np.log10(amplitude + 1e-6)

    # 2. Pengecekan Validitas Data (PENTING)
    # Cari peak tertinggi absolut
    max_peak_idx = np.argmax(amplitude)
    max_freq_detected = xf[max_peak_idx]
    
    # Jika peak tertinggi jauh dari Line Frequency (misal beda > 5Hz), user mungkin salah input FS
    if abs(max_freq_detected - line_freq) > 5.0:
        st.error(f"""
        ⛔ **PERINGATAN KONFIGURASI!**
        Peak tertinggi terdeteksi di **{max_freq_detected:.2f} Hz**, padahal Line Frequency di set **{line_freq} Hz**.
        
        Kemungkinan besar **Sampling Frequency (Hz)** di Sidebar salah! 
        Coba ubah nilai Sampling Frequency sampai peak tertinggi mendekati {line_freq} Hz.
        (Jika pakai data `buat_data.py`, pastikan Fs = 2000).
        """)

    # 3. Peak Detection Logic
    # Kita cari peak yang tingginya minimal X% dari peak tertinggi (Fundamental)
    max_amp = np.max(amplitude)
    peaks, _ = find_peaks(amplitude, height=max_amp * threshold_ratio)
    
    # DataFrame Peak
    df_peaks = pd.DataFrame({
        "Freq (Hz)": xf[peaks],
        "Amp (Linear)": amplitude[peaks],
        "Amp (dB)": amplitude_db[peaks]
    })
    
    # 4. Plotting
    fig_fft = go.Figure()
    fig_fft.add_trace(go.Scatter(x=xf, y=amplitude_db, mode='lines', name='Spectrum', line=dict(color='firebrick', width=1)))
    
    # Tandai Peak yang terdeteksi
    fig_fft.add_trace(go.Scatter(
        x=df_peaks["Freq (Hz)"], 
        y=df_peaks["Amp (dB)"], 
        mode='markers', 
        marker=dict(size=8, color='yellow', symbol='x'),
        name='Detected Peaks'
    ))

    # Area Sideband (Visualisasi area pencarian)
    fig_fft.add_vrect(x0=line_freq-8, x1=line_freq-1, fillcolor="red", opacity=0.1, annotation_text="Left Sideband Zone", annotation_position="top left")
    fig_fft.add_vrect(x0=line_freq+1, x1=line_freq+8, fillcolor="red", opacity=0.1, annotation_text="Right Sideband Zone", annotation_position="top right")

    max_view = st.sidebar.slider("Zoom Frekuensi (Hz)", 0, 200, 100)
    fig_fft.update_layout(xaxis_range=[0, max_view], title="Spectrum Analysis", yaxis_title="dB", xaxis_title="Hz")
    st.plotly_chart(fig_fft, use_container_width=True)

    # 5. DIAGNOSA LOGIC (YANG DIPERBAIKI)
    st.markdown("### Hasil Diagnosa Otomatis")
    
    # Filter peak di sekitar fundamental
    # Kita cari peak di area: [Fundamental - 8Hz] s/d [Fundamental - 1Hz] (Left)
    # Dan [Fundamental + 1Hz] s/d [Fundamental + 8Hz] (Right)
    # Buffer 1Hz diberikan agar "kaki" dari gunung fundamental tidak dianggap fault.
    
    buffer = 0.8 # Jarak aman dari 50Hz (agar peak utama yang lebar tidak terdeteksi sbg sideband)
    search_range = 8.0 # Seberapa jauh mencari sideband
    
    left_sidebands = df_peaks[
        (df_peaks["Freq (Hz)"] >= line_freq - search_range) & 
        (df_peaks["Freq (Hz)"] <= line_freq - buffer)
    ]
    
    right_sidebands = df_peaks[
        (df_peaks["Freq (Hz)"] >= line_freq + buffer) & 
        (df_peaks["Freq (Hz)"] <= line_freq + search_range)
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Peaks di Zona Kiri (Left Sidebands):")
        st.dataframe(left_sidebands[["Freq (Hz)", "Amp (Linear)"]])
        
        st.write("Peaks di Zona Kanan (Right Sidebands):")
        st.dataframe(right_sidebands[["Freq (Hz)", "Amp (Linear)"]])

    with col2:
        # Logic Keputusan
        fault_detected = False
        reasons = []
        
        if not left_sidebands.empty:
            fault_detected = True
            reasons.append(f"Terdeteksi {len(left_sidebands)} peak signifikan di sisi kiri (Low Sideband). Peak terbesar di {left_sidebands.iloc[0]['Freq (Hz)']:.2f} Hz.")
            
        if not right_sidebands.empty:
            fault_detected = True
            reasons.append(f"Terdeteksi {len(right_sidebands)} peak signifikan di sisi kanan (High Sideband). Peak terbesar di {right_sidebands.iloc[0]['Freq (Hz)']:.2f} Hz.")
            
        if fault_detected:
            st.error("⚠️ **DIAGNOSA: INDIKASI KERUSAKAN (FAULT DETECTED)**")
            for r in reasons:
                st.write(f"- {r}")
            st.warning("Pola sideband di sekitar frekuensi jala-jala adalah ciri khas **Broken Rotor Bar** atau Eccentricity.")
        else:
            st.success("✅ **DIAGNOSA: MOTOR SEHAT (HEALTHY)**")
            st.write("Tidak ditemukan peak signifikan (sidebands) di area kritis sekitar frekuensi fundamental.")
            st.caption(f"Threshold deteksi saat ini: {threshold_ratio*100}% dari amplitude max. Jika ragu, geser slider Sensitivitas di sidebar.")

else:
    st.info("Upload file CSV untuk memulai.")
