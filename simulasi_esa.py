import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq
from scipy.signal import windows
import serial
import time
import threading

# --- Konfigurasi ---
st.set_page_config(layout="wide", page_title="Real-Time ESA Monitor")
st.title("⚡ Real-Time ESA Monitor (Live Sensor)")

# --- Sidebar: Koneksi Sensor ---
st.sidebar.header("🔌 Koneksi Sensor (Serial/USB)")

# Opsi Port (Sesuaikan dengan Port Arduino/Sensor di Device Manager, misal COM3 atau /dev/ttyUSB0)
serial_port = st.sidebar.text_input("Port Serial", value="COM3")
baud_rate = st.sidebar.selectbox("Baud Rate", [9600, 115200, 230400, 500000], index=1)
fs = st.sidebar.number_input("Sampling Rate Sensor (Hz)", value=1000, help="Harus sesuai dengan settingan coding di Microcontroller")
window_duration = st.sidebar.number_input("Durasi Window (detik)", value=1.0, help="Berapa detik data diambil untuk 1x analisa FFT")

# State untuk kontrol Start/Stop
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

def start_monitoring():
    st.session_state.is_running = True

def stop_monitoring():
    st.session_state.is_running = False

col1, col2 = st.sidebar.columns(2)
col1.button("▶️ Mulai", on_click=start_monitoring)
col2.button("⏹️ Stop", on_click=stop_monitoring)

# --- Placeholder Grafik ---
# Kita butuh placeholder kosong yang akan di-update terus menerus
status_text = st.empty()
tab1, tab2 = st.tabs(["Time Domain (Live)", "Frequency Domain (ESA)"])
with tab1:
    chart_time = st.empty()
with tab2:
    chart_freq = st.empty()

# --- Fungsi Baca Sensor ---
def read_serial_buffer(ser, num_samples):
    """
    Membaca sejumlah N data dari serial port.
    Format data dari sensor diharapkan mengirim angka baris per baris (e.g., "12.5\n12.6\n...")
    """
    data = []
    try:
        # Flush buffer lama agar data fresh
        ser.reset_input_buffer()
        
        while len(data) < num_samples:
            if not st.session_state.is_running:
                break
                
            line = ser.readline().decode('utf-8').strip()
            try:
                # Konversi string ke float
                val = float(line)
                data.append(val)
            except ValueError:
                continue # Skip data sampah/corrupt
                
    except Exception as e:
        st.error(f"Error membaca serial: {e}")
        return None
        
    return np.array(data)

# --- Loop Utama ---
if st.session_state.is_running:
    try:
        # Membuka koneksi serial
        # Timeout penting agar tidak hang jika sensor mati
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        status_text.success(f"Terhubung ke {serial_port}. Mengambil data...")
        
        # Hitung jumlah sampel yang dibutuhkan untuk 1 window
        num_samples = int(fs * window_duration)
        
        while st.session_state.is_running:
            # 1. Ambil Data Real-Time
            raw_data = read_serial_buffer(ser, num_samples)
            
            if raw_data is None or len(raw_data) < num_samples:
                continue # Tunggu buffer penuh

            # Buat array waktu
            t = np.linspace(0, window_duration, len(raw_data), endpoint=False)

            # 2. Proses FFT (Sama seperti sebelumnya)
            N = len(raw_data)
            window_func = windows.hann(N)
            signal_windowed = raw_data * window_func
            
            yf = fft(signal_windowed)
            xf = fftfreq(N, 1 / fs)
            
            half_N = N // 2
            xf_plot = xf[:half_N]
            yf_plot = 2.0/N * np.abs(yf[:half_N])
            # Konversi dB (tambah epsilon biar ga error log0)
            yf_db = 20 * np.log10(yf_plot + 1e-12)

            # 3. Update Grafik Time Domain
            fig_time = go.Figure()
            fig_time.add_trace(go.Scatter(y=raw_data, mode='lines', name='Arus (Raw)'))
            fig_time.update_layout(title="Sinyal Arus Real-Time", height=300, margin=dict(l=0, r=0, t=30, b=0))
            chart_time.plotly_chart(fig_time, use_container_width=True)

            # 4. Update Grafik Frequency Domain
            fig_freq = go.Figure()
            fig_freq.add_trace(go.Scatter(x=xf_plot, y=yf_db, mode='lines', name='Spectrum', line=dict(color='firebrick')))
            fig_freq.update_layout(
                title="Spektrum ESA Real-Time", 
                xaxis_title="Frekuensi (Hz)", 
                yaxis_title="dB",
                xaxis_range=[0, 150], # Fokus ke 0-150Hz
                height=400,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            chart_freq.plotly_chart(fig_freq, use_container_width=True)
            
            # Jeda sebentar agar browser tidak hang (opsional)
            time.sleep(0.1)

    except serial.SerialException as e:
        status_text.error(f"Gagal membuka port {serial_port}. Pastikan tidak dipakai aplikasi lain (Arduino IDE, dll). Error: {e}")
        st.session_state.is_running = False
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
else:
    status_text.info("Tekan 'Mulai' untuk menghubungkan ke sensor.")
