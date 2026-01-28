import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq

# ==========================================
# 1. FUNGSI GENERATOR SINYAL (LIVE)
# ==========================================
def generate_live_signals(freq, v_noise_level, rotor_fault_level, duration=0.5, fs=2000):
    t = np.linspace(0, duration, int(fs*duration), endpoint=False)
    
    # --- A. SINYAL TEGANGAN (SOURCE) ---
    # Tegangan ideal (Sinus Murni)
    voltage = 220 * np.sqrt(2) * np.sin(2 * np.pi * freq * t)
    
    # Injeksi Gangguan Suplai (Harmonisa/Distorsi)
    # Jika slider V_Noise digeser, bentuk gelombang tegangan jadi "penyok"
    if v_noise_level > 0:
        voltage += (v_noise_level * 50) * np.sin(2 * np.pi * (freq*3) * t) # Harmonisa ke-3
        voltage += (v_noise_level * 20) * np.sin(2 * np.pi * (freq*5) * t) # Harmonisa ke-5
        voltage += np.random.normal(0, v_noise_level * 5, len(t)) # Noise acak

    # --- B. SINYAL ARUS (LOAD) ---
    # Arus dasar (mengikuti frekuensi tegangan)
    # Biasanya arus tertinggal (lagging)
    current = 100 * np.sqrt(2) * np.sin(2 * np.pi * freq * t - (np.pi/4))
    
    # EFEK 1: Jika Tegangan jelek, Arus OTOMATIS ikut jelek (Hukum Fisika)
    if v_noise_level > 0:
        current += (v_noise_level * 25) * np.sin(2 * np.pi * (freq*3) * t - (np.pi/4))
    
    # EFEK 2: Kerusakan Motor (Rotor Fault)
    # Ini murni dari motor, tidak ada hubungannya dengan tegangan
    if rotor_fault_level > 0:
        # Sidebands (Kiri & Kanan)
        sb_amp = rotor_fault_level * 5 # Pengali amplitudo
        current += sb_amp * np.sin(2 * np.pi * (freq - 5) * t)
        current += sb_amp * np.sin(2 * np.pi * (freq + 5) * t)

    # Tambah noise alami arus
    current += np.random.normal(0, 0.5, len(t))
    
    return t, voltage, current

# ==========================================
# 2. FUNGSI ANALISA & DIAGNOSA
# ==========================================
def analyze_signals(voltage, current, fs=2000):
    N = len(voltage)
    
    # Fungsi FFT Helper
    def get_fft(sig):
        yf = fft(sig)
        xf = fftfreq(N, 1/fs)[:N//2]
        amp = 2.0/N * np.abs(yf[0:N//2])
        db = 20 * np.log10(amp + 1e-9)
        return xf, db, amp

    xf, v_db, v_amp = get_fft(voltage)
    _, i_db, i_amp = get_fft(current)
    
    # Cari Frekuensi Dominan
    idx_peak = np.argmax(v_amp)
    freq_fund = xf[idx_peak]
    
    # --- LOGIKA DIAGNOSA ESA ---
    diagnosis = []
    status = "NORMAL"
    
    # 1. Cek Kualitas Tegangan (Distorsi Suplai)
    # Kita cek apakah ada "sampah" di sinyal tegangan selain di frekuensi utama
    v_clean_amp = v_amp[idx_peak]
    v_total_amp = np.sum(v_amp)
    # Ratio sederhana distorsi
    distortion_ratio = (v_total_amp - v_clean_amp) / v_clean_amp 
    
    if distortion_ratio > 0.15: # Ambang batas
        status = "WARNING"
        diagnosis.append("⚠️ **SUPPLY ISSUE:** Tegangan (Oranye) terdistorsi! Genset/PLN bermasalah.")
        
    # 2. Cek Kerusakan Rotor (Sideband di Arus)
    # Cari amplitudo sideband di Arus (sekitar freq - 5Hz)
    target_sb = freq_fund - 5
    idx_sb = np.argmin(np.abs(xf - target_sb))
    # Cari peak lokal di area sideband Arus
    idx_peak_sb_i = idx_sb - 20 + np.argmax(i_db[idx_sb-20 : idx_sb+20])
    sb_height_i = i_db[idx_peak_sb_i]
    fund_height_i = i_db[idx_peak]
    
    diff_i = fund_height_i - sb_height_i
    
    # KUNCI ESA: Cek apakah sideband itu juga ada di Tegangan?
    idx_peak_sb_v = idx_sb - 20 + np.argmax(v_db[idx_sb-20 : idx_sb+20])
    sb_height_v = v_db[idx_peak_sb_v]
    fund_height_v = v_db[idx_peak]
    
    diff_v = fund_height_v - sb_height_v
    
    # Logic: Jika di Arus sidebandnya KUAT, tapi di Tegangan LEMAH -> Motor Rusak
    if diff_i < 30: # Arus ada gangguan
        if diff_v > 50: # Tegangan bersih
            status = "CRITICAL"
            diagnosis.append("⚠️ **MOTOR FAULT:** Broken Rotor Bar detected! (Masalah murni internal motor).")
        else:
            # Tegangan juga ada gangguan serupa (kemungkinan noise ikut dari supply)
            if "SUPPLY ISSUE" not in str(diagnosis):
                 diagnosis.append("ℹ️ **INFO:** Arus kotor, tapi Tegangan juga kotor. Kemungkinan bukan kerusakan motor.")

    if status == "NORMAL":
        diagnosis.append("✅ Sistem Sehat (Source & Load Aman).")
        
    return t, xf, v_db, i_db, status, diagnosis, freq_fund

# ==========================================
# 3. TAMPILAN DASHBOARD
# ==========================================
st.set_page_config(layout="wide", page_title="ESA Live Lab")

st.title("🎛️ ESA Interactive Lab (Source vs Load)")
st.markdown("Simulasi hubungan antara **Tegangan (Genset/PLN)** dan **Arus (Motor)**.")

# --- KOLOM KONTROL (SLIDER) ---
col_ctrl, col_disp = st.columns([1, 3])

with col_ctrl:
    st.header("1. Kontrol Input")
    
    st.subheader("⚡ Sisi Suplai (Genset)")
    st.caption("Mengatur kualitas Tegangan (Voltage)")
    freq_input = st.slider("Frekuensi (Hz)", 45.0, 55.0, 50.0)
    v_distorsi = st.slider("Distorsi Tegangan (Harmonics)", 0.0, 1.0, 0.0)
    
    st.divider()
    
    st.subheader("⚙️ Sisi Motor (Beban)")
    st.caption("Mengatur kondisi kesehatan Motor")
    rotor_fault = st.slider("Kerusakan Rotor (Severity)", 0.0, 5.0, 0.0)
    
    st.info("Geser slider di atas untuk melihat bagaimana grafik merespon.")

# --- PROSES DATA ---
t, v, i = generate_live_signals(freq_input, v_distorsi, rotor_fault)
t_plot, xf, v_db, i_db, status, diags, f_det = analyze_signals(v, i)

# --- TAMPILAN GRAFIK ---
with col_disp:
    # 1. KARTU STATUS
    st.subheader("2. Hasil Diagnosa AI")
    
    s_col1, s_col2 = st.columns([1,3])
    color = "green" if status == "NORMAL" else "red"
    if status == "WARNING": color = "orange"
    
    with s_col1:
        st.markdown(f"""
        <div style="background-color:{color}; padding:10px; border-radius:10px; text-align:center; color:white;">
            <h2 style="margin:0;">{status}</h2>
        </div>
        """, unsafe_allow_html=True)
    with s_col2:
        for d in diags:
            st.markdown(f"**{d}**")
            
    # 2. GRAFIK SPEKTRUM (ANALISA UTAMA)
    st.divider()
    st.subheader("📊 Spektrum ESA (Frequency Domain)")
    st.caption("Membandingkan tanda tangan Arus vs Tegangan.")
    
    fig_spec = go.Figure()
    # Plot Tegangan (Background)
    fig_spec.add_trace(go.Scatter(x=xf, y=v_db, name='Tegangan (Source)', 
                                 line=dict(color='orange', width=2), opacity=0.6))
    # Plot Arus (Foreground)
    fig_spec.add_trace(go.Scatter(x=xf, y=i_db, name='Arus (Motor)', 
                                 line=dict(color='blue', width=2)))
    
    fig_spec.update_layout(height=400, xaxis_title="Frekuensi (Hz)", yaxis_title="dB", 
                          margin=dict(l=0, r=0, t=30, b=0))
    fig_spec.update_xaxes(range=[freq_input-20, freq_input+20]) # Auto Zoom
    st.plotly_chart(fig_spec, use_container_width=True)
    
    # 3. GRAFIK GELOMBANG (TIME DOMAIN)
    st.subheader("📈 Bentuk Gelombang Asli (Time Domain)")
    fig_time = go.Figure()
    # Normalisasi agar tampilannya sebanding
    fig_time.add_trace(go.Scatter(x=t[:200], y=v[:200]/3, name='Tegangan (Scaled)', line=dict(color='orange')))
    fig_time.add_trace(go.Scatter(x=t[:200], y=i[:200], name='Arus', line=dict(color='blue')))
    fig_time.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_time, use_container_width=True)
