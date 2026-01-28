import streamlit as st
import numpy as np
import pandas as pd
import scipy.fftpack
from scipy.signal import find_peaks, windows
import plotly.graph_objects as go

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Simulasi ESA - MCSA Tool", layout="wide")

st.title("🔩 Simulasi ESA: Motor Current Signature Analysis")
st.markdown("""
Aplikasi ini dirancang untuk menganalisis sinyal arus motor induksi (MCSA).
Metode: **Fast Fourier Transform (FFT)** untuk mendeteksi *sidebands* (frekuensi kerusakan) di sekitar frekuensi fundamental.
Referensi Dasar: *Brief Review of Motor Current Signature Analysis*.
""")

# --- Sidebar: Konfigurasi ---
st.sidebar.header("1. Input Data")
data_source = st.sidebar.radio("Sumber Data:", ("Gunakan Data Dummy (Simulasi)", "Upload File CSV"))

# Parameter Global
fs = st.sidebar.number_input("Sampling Frequency (Hz)", value=1000, min_value=100, help="Frekuensi pengambilan data sensor")
line_freq = st.sidebar.number_input("Line Frequency (Hz)", value=50.0, step=10.0, help="Frekuensi jala-jala listrik (biasanya 50Hz atau 60Hz)")

# --- Fungsi Generate Data Dummy ---
def generate_dummy_signal(fs, duration=2, fault=False):
    """
    Membuat sinyal arus sintetik.
    Jika fault=True, tambahkan sidebands untuk mensimulasikan Broken Rotor Bar.
    """
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    
    # 1. Komponen Fundamental (Line Frequency)
    # Amplitudo besar (misal 10 Ampere)
    signal = 10 * np.sin(2 * np.pi * line_freq * t)
    
    # 2. Noise Putih (Gaussian Noise)
    noise = np.random.normal(0, 0.2, size=len(t))
    signal = signal + noise
    
    if fault:
        # Simulasi Broken Rotor Bar: Sidebands di sekitar fundamental
        # Rumus teoritis: f_sb = f_line (1 ± 2s)
        # Kita asumsikan slip (s) = 0.05
        slip = 0.05
        f_sb_left = line_freq * (1 - 2*slip)  # Contoh: 50 * (1 - 0.1) = 45 Hz
        f_sb_right = line_freq * (1 + 2*slip) # Contoh: 50 * (1 + 0.1) = 55 Hz
        
        # Tambahkan sinyal gangguan (amplitudo lebih kecil, misal 0.5 A)
        signal += 0.5 * np.sin(2 * np.pi * f_sb_left * t)
        signal += 0.5 * np.sin(2 * np.pi * f_sb_right * t)
        
    return t, signal

# --- Logika Load Data ---
current_data = None
time_data = None

if data_source == "Gunakan Data Dummy (Simulasi)":
    st.sidebar.subheader("Simulasi Kerusakan")
    is_faulty = st.sidebar.checkbox("Simulasikan Motor Rusak (Sidebands)", value=True)
    duration = st.sidebar.slider("Durasi Sinyal (detik)", 1, 10, 2)
    
    # Generate Data
    time_data, current_data = generate_dummy_signal(fs, duration, is_faulty)
    
    status_text = "⚠️ RUSAK (Faulty)" if is_faulty else "✅ SEHAT (Healthy)"
    st.info(f"Mode Simulasi Aktif: Kondisi Motor **{status_text}**")

else:
    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Upload CSV (Kolom 1: Arus)", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            # Asumsi data arus ada di kolom pertama
            current_data = df.iloc[:, 0].values
            # Buat array waktu
            time_data = np.arange(len(current_data)) / fs
            st.success(f"File '{uploaded_file.name}' berhasil dimuat. Total sampel: {len(current_data)}")
        except Exception as e:
            st.error(f"Error membaca file CSV: {e}")

# --- Proses Analisis Utama ---
if current_data is not None:
    
    # --- 1. Time Domain Plot ---
    st.subheader("2. Time Domain (Gelombang Arus)")
    fig_time = go.Figure()
    
    # Limit plot agar tidak berat jika data jutaan baris (ambil 1000 sampel pertama untuk preview)
    preview_limit = min(2000, len(current_data))
    fig_time.add_trace(go.Scatter(
        x=time_data[:preview_limit], 
        y=current_data[:preview_limit], 
        mode='lines', 
        name='Current (A)',
        line=dict(color='royalblue', width=1.5)
    ))
    fig_time.update_layout(
        title="Waveform Arus (Zoomed Preview)", 
        xaxis_title="Waktu (detik)", 
        yaxis_title="Amplitudo (Ampere)",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_time, use_container_width=True)

    # --- 2. Frequency Domain Processing (FFT) ---
    st.subheader("3. Frequency Domain (Spektrum MCSA)")
    
    # A. Hilangkan DC Offset (centering)
    signal_ac = current_data - np.mean(current_data)
    
    # B. Windowing (Hanning) - Penting untuk mengurangi spectral leakage sesuai jurnal
    N = len(signal_ac)
    window = windows.hann(N)
    signal_windowed = signal_ac * window
    
    # C. Hitung FFT
    yf = scipy.fftpack.fft(signal_windowed)
    xf = np.linspace(0.0, 1.0/(2.0*(1/fs)), N//2) # Sumbu Frekuensi (hanya sisi positif)
    
    # D. Hitung Magnitude Normal
    amplitude = 2.0/N * np.abs(yf[:N//2])
    
    # E. Konversi ke Decibel (dB)
    # Tambahkan epsilon 1e-6 untuk menghindari log(0)
    amplitude_db = 20 * np.log10(amplitude + 1e-6)

    # --- 3. FFT Plotting ---
    fig_fft = go.Figure()
    fig_fft.add_trace(go.Scatter(
        x=xf, 
        y=amplitude_db, 
        mode='lines', 
        name='Spectrum (dB)',
        line=dict(color='firebrick', width=1)
    ))
    
    # Garis bantu frekuensi jala-jala
    fig_fft.add_vline(x=line_freq, line_width=2, line_dash="dash", line_color="green", annotation_text="Line Freq")

    # Kontrol tampilan Grafik
    max_freq_view = st.sidebar.slider("Zoom Frekuensi Max (Hz)", 0, int(fs/2), 100)
    
    fig_fft.update_layout(
        title="Power Spectral Density (MCSA Spectrum)",
        xaxis_title="Frekuensi (Hz)",
        yaxis_title="Amplitudo (dB)",
        xaxis_range=[0, max_freq_view],
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_fft, use_container_width=True)

    # --- 4. Analisis Puncak (Peak Detection) ---
    st.markdown("### 4. Analisis Deteksi Kerusakan")
    
    col_res1, col_res2 = st.columns([1, 2])
    
    with col_res1:
        st.write("**Top Peaks Detected:**")
        
        # Cari puncak
        peaks, properties = find_peaks(amplitude, height=np.max(amplitude)*0.02) # Threshold 2%
        
        # Buat DataFrame hasil
        df_peaks = pd.DataFrame({
            "Freq (Hz)": xf[peaks],
            "Amp (dB)": amplitude_db[peaks]
        })
        
        # Filter tampilan sesuai zoom user
        df_peaks = df_peaks[df_peaks["Freq (Hz)"] <= max_freq_view]
        
        # Urutkan berdasarkan amplitudo terbesar
        df_peaks = df_peaks.sort_values(by="Amp (dB)", ascending=False).head(10).reset_index(drop=True)
        
        st.dataframe(df_peaks.style.format("{:.2f}"))

    with col_res2:
        st.info("ℹ️ **Interpretasi Berdasarkan Jurnal:**")
        st.markdown(f"""
        1. **Fundamental:** Puncak tertinggi seharusnya berada di **{line_freq} Hz**.
        2. **Broken Rotor Bar:** Cari puncak kembar (*sidebands*) di kiri-kanan frekuensi fundamental.
           - Rumus: $f_{{sb}} = f_{{line}} (1 \pm 2ks)$
           - Jika ada puncak signifikan di sekitar **{line_freq - 5} Hz** dan **{line_freq + 5} Hz** (tergantung slip), ini indikasi rotor bar retak/putus.
        3. **Eccentricity:** Sering muncul di frekuensi: $f_{{ecc}} = f_{{line}} \pm f_{{rotasi}}$.
        """)
        
        # Analisis Sederhana Otomatis
        has_sideband_left = df_peaks[(df_peaks["Freq (Hz)"] > line_freq - 7) & (df_peaks["Freq (Hz)"] < line_freq - 2)]
        has_sideband_right = df_peaks[(df_peaks["Freq (Hz)"] > line_freq + 2) & (df_peaks["Freq (Hz)"] < line_freq + 7)]
        
        if not has_sideband_left.empty and not has_sideband_right.empty:
            st.warning("⚠️ **PERINGATAN DETEKSI:** Terdeteksi pola Sidebands yang signifikan! Kemungkinan ada indikasi kerusakan rotor (Broken Rotor Bar) atau beban tidak seimbang.")
        elif not has_sideband_left.empty or not has_sideband_right.empty:
            st.warning("⚠️ **PERINGATAN:** Terdeteksi ketidakseimbangan spektrum (Asymmetric Sidebands).")
        else:
            st.success("✅ **ANALISIS:** Spektrum terlihat bersih di sekitar frekuensi fundamental (No major sidebands).")

else:
    st.warning("⬅️ Menunggu input data. Silakan pilih opsi di Sidebar.")

# Footer
st.markdown("---")
st.caption("File: `simulasi_esa.py` | Implementation of MCSA concepts using Python & Streamlit.")
