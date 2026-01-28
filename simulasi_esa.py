import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq

# ==========================================
# 1. ALGORITMA ESA (VOLTAGE + CURRENT)
# ==========================================
def analyze_esa_industrial(voltage, current, fs):
    N = len(voltage)
    
    # --- STEP A: ANALISA SIGNAL DASAR ---
    # Hitung RMS
    v_rms = np.sqrt(np.mean(voltage**2))
    i_rms = np.sqrt(np.mean(current**2))
    
    # Hitung Daya (Instantaneous Power)
    # p(t) = v(t) * i(t) -> Teknik paling ampuh di ESA
    power_signal = voltage * current
    
    # --- STEP B: FFT PROCESSSING ---
    # Kita lakukan FFT pada sinyal Arus (untuk MCSA) DAN sinyal Tegangan
    
    # Fungsi FFT Helper
    def get_spectrum(signal):
        yf = fft(signal)
        xf = fftfreq(N, 1 / fs)
        xf = xf[:N//2]
        amp = 2.0/N * np.abs(yf[0:N//2])
        db = 20 * np.log10(amp + 1e-9)
        return xf, db, amp

    xf, v_db, v_amp = get_spectrum(voltage)
    _, i_db, i_amp = get_spectrum(current)
    
    # --- STEP C: SMART TRACKING (Cari Frekuensi Tegangan) ---
    # Tegangan adalah referensi paling stabil
    idx_peak_v = np.argmax(v_amp) 
    freq_fund = xf[idx_peak_v]
    
    # --- STEP D: DIAGNOSA LANJUTAN (Korelasi V & I) ---
    diagnosis = []
    status = "NORMAL"
    
    # 1. Cek Kualitas Tegangan (Supply Side)
    # Cari noise di tegangan (Harmonisa tegangan)
    v_thd_est = (np.sum(v_amp) - v_amp[idx_peak_v]) / v_amp[idx_peak_v] * 100
    
    if v_thd_est > 5.0: # Standar IEEE 519 (Voltage distortion > 5%)
        status = "WARNING"
        diagnosis.append(f"⚠️ **SUPPLY ISSUE:** Kualitas Tegangan Buruk (Distorsi {v_thd_est:.1f}%). Masalah ada di Genset/Trafo, bukan Motor.")
    
    # 2. Cek Rotor (Load Side)
    # Cari Sideband di ARUS
    target_sb = freq_fund - 5 # Asumsi slip
    idx_sb = np.argmin(np.abs(xf - target_sb))
    
    # Ambil peak sideband di arus
    search_w = 50
    low = max(0, idx_sb-search_w)
    high = min(len(i_db), idx_sb+search_w)
    idx_peak_sb_i = low + np.argmax(i_db[low:high])
    
    diff_rotor = i_db[idx_peak_v] - i_db[idx_peak_sb_i]
    
    # Logika Cerdas: Apakah tegangan juga punya sideband sama?
    # Jika Tegangan bersih, tapi Arus kotor -> Fix Motor Rusak
    # Jika Tegangan kotor, dan Arus kotor -> Suplai yang salah
    
    idx_peak_sb_v = low + np.argmax(v_db[low:high])
    diff_voltage_noise = v_db[idx_peak_v] - v_db[idx_peak_sb_v]
    
    if diff_rotor < 35: # Indikasi kerusakan di arus kuat
        if diff_voltage_noise > 50: 
            # Tegangan bersih (beda jauh), Arus kotor (beda dikit)
            status = "CRITICAL"
            diagnosis.append(f"⚠️ **MOTOR FAULT:** Broken Rotor Bar Terdeteksi! (Suplai listrik bersih, tapi arus motor cacat).")
        else:
            # Tegangan juga kotor
            if status != "CRITICAL": status = "WARNING"
            diagnosis.append(f"⚠️ **FALSE ALARM:** Terdeteksi fluktuasi arus, TAPI tegangan juga berfluktuasi. Kemungkinan beban sumber tidak stabil.")

    if status == "NORMAL":
        diagnosis.append("✅ Sistem Sehat. Kualitas Daya & Kondisi Motor Prima.")

    return xf, v_db, i_db, freq_fund, v_rms, i_rms, status, diagnosis

# ==========================================
# 2. GENERATOR DUAL CHANNEL (V + I)
# ==========================================
def create_esa_csv(scenario):
    fs = 2000
    duration = 2.0
    t = np.linspace(0.0, duration, int(fs*duration), endpoint=False)
    
    # --- SINYAL TEGANGAN (VOLTAGE) ---
    # Biasanya tegangan PLN relatif bersih (Sinus Murni)
    voltage = 220 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t) # 220V RMS
    
    # --- SINYAL ARUS (CURRENT) ---
    # Arus tertinggal (lagging) dari tegangan karena sifat induktif motor
    phase_lag = np.pi / 4 # 45 derajat
    current = 100 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t - phase_lag)
    
    filename = "ESA_Normal.csv"
    
    if scenario == "Motor Rusak (Rotor)":
        # Tegangan TETAP BERSIH (Karena suplai bagus)
        voltage += np.random.normal(0, 0.5, len(t))
        
        # Arus KOTOR (Ada sideband kerusakan)
        current += 5 * np.sin(2 * np.pi * 45 * t - phase_lag)
        current += 5 * np.sin(2 * np.pi * 55 * t - phase_lag)
        current += np.random.normal(0, 0.5, len(t))
        filename = "ESA_MotorRusak.csv"
        
    elif scenario == "Supply Jelek (Genset Hunting)":
        # Tegangan KOTOR (Ada modulasi frekuensi rendah)
        modulasi = 10 * np.sin(2 * np.pi * 5 * t)
        voltage += modulasi # Tegangan naik turun
        
        # Arus IKUT KOTOR (Karena tegangan naik turun, arus pasti ikut)
        current += (modulasi / 2) # Arus ikut terpengaruh
        voltage += np.random.normal(0, 2.0, len(t))
        current += np.random.normal(0, 1.0, len(t))
        filename = "ESA_SupplyJelek.csv"
        
    else: # Normal
        voltage += np.random.normal(0, 0.2, len(t))
        current += np.random.normal(0, 0.2, len(t))

    # Gabungkan jadi 2 Kolom (Voltage, Current)
    df = pd.DataFrame({'Voltage': voltage, 'Current': current})
    return df.to_csv(index=False, header=False), filename

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.set_page_config(layout="wide", page_title="Industrial ESA")

st.title("🏭 True ESA System (Voltage + Current)")
st.markdown("**Infrastructure Management - Pertamina Patra Niaga**")
st.markdown("Analisis korelasi Tegangan (Suplai) dan Arus (Beban) untuk diagnosa presisi.")

# --- SIDEBAR GENERATOR ---
st.sidebar.header("1. Generator Data (2-Channel)")
st.sidebar.info("Data CSV ini sekarang berisi 2 kolom: Tegangan (V) & Arus (A).")

csv_norm, n_norm = create_esa_csv("Normal")
st.sidebar.download_button("⬇️ Download: Normal", csv_norm, n_norm, "text/csv")

csv_fault, n_fault = create_esa_csv("Motor Rusak (Rotor)")
st.sidebar.download_button("⬇️ Download: Motor Rusak", csv_fault, n_fault, "text/csv")

csv_sup, n_sup = create_esa_csv("Supply Jelek (Genset Hunting)")
st.sidebar.download_button("⬇️ Download: Supply Problem", csv_sup, n_sup, "text/csv")

# --- MAIN UPLOAD ---
st.divider()
uploaded_file = st.file_uploader("Upload CSV ESA (Format: Col1=Volt, Col2=Amp)", type=["csv", "txt"])

if uploaded_file:
    try:
        # Baca CSV (Harus 2 Kolom)
        df = pd.read_csv(uploaded_file, header=None)
        
        if df.shape[1] < 2:
            st.error("⚠️ File harus memiliki minimal 2 kolom (Voltage & Current). Ini sistem ESA, bukan MCSA.")
        else:
            volts = df.iloc[:, 0].values
            amps = df.iloc[:, 1].values
            
            # PROSES ANALISA
            xf, v_db, i_db, freq, v_rms, i_rms, status, diags = analyze_esa_industrial(volts, amps, 2000)
            
            # --- DASHBOARD HASIL ---
            # 1. KARTU STATUS
            c1, c2, c3 = st.columns([1, 1, 2])
            c1.metric("Tegangan (RMS)", f"{v_rms:.1f} V")
            c2.metric("Arus (RMS)", f"{i_rms:.1f} A")
            
            color = "green" if status == "NORMAL" else "red" 
            if status == "WARNING": color = "orange"
            
            with c3:
                st.markdown(f"<h2 style='color:{color};'>STATUS: {status}</h2>", unsafe_allow_html=True)
                for d in diags:
                    if "✅" in d: st.success(d)
                    elif "⚠️" in d: st.warning(d) if status == "WARNING" else st.error(d)

            # 2. GRAFIK PERBANDINGAN V vs I
            st.divider()
            st.subheader("🔍 Analisa Sumber Masalah (Source vs Load)")
            
            tab_graph1, tab_graph2 = st.tabs(["Spektrum Gabungan (V & I)", "Waveform Asli"])
            
            with tab_graph1:
                fig = go.Figure()
                # Plot Arus (Beban)
                fig.add_trace(go.Scatter(x=xf, y=i_db, name='Arus (Motor)', line=dict(color='blue')))
                # Plot Tegangan (Suplai) - Transparan dikit
                fig.add_trace(go.Scatter(x=xf, y=v_db, name='Tegangan (PLN/Genset)', line=dict(color='orange', dash='dot')))
                
                fig.update_layout(title="Apakah Tegangan ikut kotor?", xaxis_title="Hz", yaxis_title="dB", height=500)
                fig.update_xaxes(range=[freq-20, freq+20]) # Zoom ke fundamental
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Tips: Jika Garis Biru (Arus) muncul paku sideband, tapi Garis Oranye (Tegangan) mulus rata, berarti kerusakan dari MOTOR.")

            with tab_graph2:
                # Tampilkan cuplikan gelombang 0.1 detik
                limit = 200 # 2000Hz * 0.1s
                fig_wave = go.Figure()
                # Normalisasi agar bisa digambar bareng (V dibagi 2 supaya skalanya mirip I)
                fig_wave.add_trace(go.Scatter(y=volts[:limit], name='Voltage (V)', line=dict(color='orange')))
                fig_wave.add_trace(go.Scatter(y=amps[:limit]*2, name='Current (x2)', line=dict(color='blue'))) 
                fig_wave.update_layout(title="Bentuk Gelombang (0.1 detik pertama)", height=400)
                st.plotly_chart(fig_wave, use_container_width=True)

    except Exception as e:
        st.error(f"Error pembacaan file: {e}")
