import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq

# ==========================================
# 1. ALGORITMA CERDAS (VSD SUPPORT)
# ==========================================
def analyze_and_diagnose(signal_data, fs):
    # A. Lakukan FFT
    N = len(signal_data)
    yf = fft(signal_data)
    xf = fftfreq(N, 1 / fs)
    
    # Ambil sisi positif
    xf = xf[:N//2]
    amplitude = 2.0/N * np.abs(yf[0:N//2])
    amplitude_db = 20 * np.log10(amplitude + 1e-9)
    
    # B. SMART TRACKING (Cari Frekuensi VSD)
    # Alih-alih mencari fix di 50Hz, kita scan area operasi wajar (20Hz - 70Hz)
    # Ini kuncinya agar support VSD!
    scan_min_hz = 20
    scan_max_hz = 70
    
    # Buat mask untuk area scan
    mask_scan = (xf >= scan_min_hz) & (xf <= scan_max_hz)
    idx_scan = np.where(mask_scan)[0]
    
    if len(idx_scan) > 0:
        # Cari puncak tertinggi di dalam area scan tersebut
        idx_peak_local = np.argmax(amplitude_db[idx_scan])
        idx_peak = idx_scan[idx_peak_local] # Index global
        freq_fund = xf[idx_peak]
        amp_fund = amplitude_db[idx_peak]
    else:
        # Fallback jika sinyal aneh/mati
        freq_fund = 50.0
        amp_fund = -100
        idx_peak = np.argmin(np.abs(xf - 50))

    # C. Cek Sidebands (Dynamic Tracking)
    # Sideband selalu relatif terhadap freq_fund yang ditemukan
    # Asumsi slip frequency sekitar 2.5 Hz (Sideband distance +/- 5Hz dari Slip x 2)
    # Kita cari sideband kiri di jarak 5Hz dari fundamental
    target_sb_left = freq_fund - 5 
    idx_sb_left = np.argmin(np.abs(xf - target_sb_left))
    
    # Cari puncak tertinggi di area radius kecil sekitar target sideband
    search_width = 50 # points
    idx_peak_sb = idx_sb_left - search_width + np.argmax(amplitude_db[idx_sb_left-search_width : idx_sb_left+search_width])
    amp_sb = amplitude_db[idx_peak_sb]
    freq_sb = xf[idx_peak_sb]
    
    # D. Cek Harmonisa (Dynamic Tracking)
    # Harmonisa ke-3 selalu 3x dari freq_fund
    target_h3 = freq_fund * 3
    idx_h3 = np.argmin(np.abs(xf - target_h3))
    # Cari peak lokal harmonisa
    idx_peak_h3 = idx_h3 - search_width + np.argmax(amplitude_db[idx_h3-search_width : idx_h3+search_width])
    amp_h3 = amplitude_db[idx_peak_h3]

    # --- LOGIKA KEPUTUSAN (RULE BASED) ---
    diagnosis = []
    status = "NORMAL"
    
    # Rule 1: Rotor Bar Check
    diff_rotor = amp_fund - amp_sb
    if diff_rotor < 30: # Threshold 30dB
        status = "CRITICAL"
        diagnosis.append(f"⚠️ **BROKEN ROTOR BAR** terdeteksi! (Sideband di {freq_sb:.1f} Hz terlalu tinggi)")
    
    # Rule 2: Power Quality / Harmonics Check
    diff_harm = amp_fund - amp_h3
    if diff_harm < 50:
        if status != "CRITICAL": status = "WARNING"
        diagnosis.append(f"⚠️ **POWER QUALITY ISSUE** (Harmonisa ke-3 tinggi)")

    if status == "NORMAL":
        diagnosis.append(f"✅ Motor Beroperasi Normal pada {freq_fund:.1f} Hz.")

    return xf, amplitude_db, status, diagnosis, freq_fund

# ==========================================
# 2. GENERATOR CSV (VSD CAPABLE)
# ==========================================
def create_vsd_csv(condition, frequency):
    fs = 2000
    duration = 2.0
    t = np.linspace(0.0, duration, int(fs*duration), endpoint=False)
    
    # Sinyal Dasar (Mengikuti input frekuensi VSD)
    sig = 100 * np.sin(2 * np.pi * frequency * t)
    
    filename = f"VSD_{int(frequency)}Hz_Sehat.csv"
    
    if condition == "Rusak (Rotor)":
        # Sidebands mengikuti frekuensi utama (freq +/- 5Hz)
        sig += 4.5 * np.sin(2 * np.pi * (frequency - 5) * t)
        sig += 4.5 * np.sin(2 * np.pi * (frequency + 5) * t)
        sig += np.random.normal(0, 0.3, len(t)) # Noise sedang
        filename = f"VSD_{int(frequency)}Hz_Rusak.csv"
    else:
        # Sehat - Noise kecil
        sig += np.random.normal(0, 0.1, len(t))
        
    df = pd.DataFrame(sig)
    return df.to_csv(index=False, header=False), filename

# ==========================================
# 3. USER INTERFACE (STREAMLIT)
# ==========================================
st.set_page_config(layout="wide", page_title="ESA VSD Analyzer")

# Header Area
col_logo, col_title = st.columns([1, 5])
with col_title:
    st.title("⚡ ESA Analyzer Pro (VSD Ready)")
    st.markdown("**Infrastructure Management - Pertamina Patra Niaga**")
    st.caption("Support Direct Online (50Hz) & Variable Speed Drive (20-60Hz)")

st.divider()

# --- TAB SETUP ---
tab1, tab2 = st.tabs(["🎛️ Simulasi VSD Live", "📂 Analisa File (Upload)"])

# TAB 1: SIMULASI LIVE VSD
with tab1:
    col_sim_ctrl, col_sim_view = st.columns([1, 3])
    
    with col_sim_ctrl:
        st.subheader("Panel Kontrol VSD")
        st.info("Atur frekuensi output VSD untuk melihat kemampuan 'Tracking' alat ini.")
        
        # Slider Frekuensi VSD
        vsd_freq = st.slider("Frekuensi VSD (Hz)", 20.0, 60.0, 50.0, step=0.5)
        
        # Slider Kerusakan
        st.markdown("---")
        sim_fault = st.checkbox("Inject Kerusakan Rotor")
        sim_noise = st.slider("Level Noise", 0.0, 1.0, 0.1)
        
    with col_sim_view:
        # Generate Data On-the-fly
        fs_sim = 2000
        t_sim = np.linspace(0, 1.0, fs_sim, endpoint=False)
        sig_sim = 100 * np.sin(2 * np.pi * vsd_freq * t_sim)
        
        if sim_fault:
            # Sidebands dinamis mengikuti slider VSD
            sig_sim += 5 * np.sin(2 * np.pi * (vsd_freq - 5) * t_sim)
            sig_sim += 5 * np.sin(2 * np.pi * (vsd_freq + 5) * t_sim)
        
        sig_sim += np.random.normal(0, sim_noise, len(t_sim))
        
        # Analisa
        xf_sim, y_db_sim, stat_sim, _, detected_freq = analyze_and_diagnose(sig_sim, fs_sim)
        
        # Plotting
        st.subheader(f"Monitoring Real-time (Detected: {detected_freq:.2f} Hz)")
        
        fig_sim = go.Figure()
        fig_sim.add_trace(go.Scatter(x=xf_sim, y=y_db_sim, name='Spectrum', line=dict(color='#00CC96')))
        
        # Marker Frekuensi Utama
        fig_sim.add_vline(x=detected_freq, line_dash="dash", line_color="white", annotation_text=f"Fund: {detected_freq:.1f}Hz")
        
        # Marker Sideband (Visualisasi)
        if sim_fault:
            fig_sim.add_vline(x=detected_freq-5, line_dash="dot", line_color="red", annotation_text="SB")
            fig_sim.add_vline(x=detected_freq+5, line_dash="dot", line_color="red", annotation_text="SB")
            st.error("⚠️ CRITICAL: Broken Rotor Bar Pattern Detected")
        else:
            st.success("✅ NORMAL OPERATION")
            
        fig_sim.update_layout(xaxis_title="Frekuensi (Hz)", yaxis_title="dB", height=450)
        # Auto Zoom mengikuti frekuensi VSD (+/- 20Hz dari fundamental)
        fig_sim.update_xaxes(range=[vsd_freq-20, vsd_freq+20])
        st.plotly_chart(fig_sim, use_container_width=True)

# TAB 2: UPLOAD & ANALISA
with tab2:
    st.sidebar.header("📥 Generator Data CSV")
    st.sidebar.markdown("Buat data dummy untuk tes upload:")
    
    # Input generator di sidebar
    gen_freq = st.sidebar.number_input("Set Frekuensi Data (Hz)", 20, 60, 42)
    
    # Tombol Download
    csv_vsd_sehat, n_sehat = create_vsd_csv("Sehat", gen_freq)
    st.sidebar.download_button(f"⬇️ Download Sehat ({gen_freq}Hz)", csv_vsd_sehat, n_sehat, "text/csv")
    
    csv_vsd_rusak, n_rusak = create_vsd_csv("Rusak (Rotor)", gen_freq)
    st.sidebar.download_button(f"⬇️ Download Rusak ({gen_freq}Hz)", csv_vsd_rusak, n_rusak, "text/csv")
    
    st.markdown("### Upload Data Lapangan (Support VSD)")
    st.caption("Sistem akan otomatis mendeteksi frekuensi kerja motor, tidak harus 50Hz.")
    
    uploaded_file = st.file_uploader("Pilih File CSV", type=["csv", "txt"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, header=None)
            data_signal = df.iloc[:, 0].values
            
            # PROSES DIAGNOSA
            xf, y_db, status, diagnosis_list, freq_fund = analyze_and_diagnose(data_signal, 2000)
            
            # Tampilan Status
            st.divider()
            col_res1, col_res2 = st.columns([1,3])
            
            with col_res1:
                color = "green" if status == "NORMAL" else "red"
                st.markdown(f"""
                <div style="border: 2px solid {color}; padding: 15px; border-radius: 10px; text-align: center;">
                    <h1 style="color:{color}; margin:0;">{freq_fund:.1f} Hz</h1>
                    <p>Detected Frequency</p>
                    <h3 style="color:{color};">{status}</h3>
                </div>
                """, unsafe_allow_html=True)
                
            with col_res2:
                st.markdown("#### Detail Diagnosa:")
                for d in diagnosis_list:
                    if "⚠️" in d: st.error(d)
                    else: st.success(d)
            
            # Grafik
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=xf, y=y_db, name='Spectrum'))
            fig.add_vline(x=freq_fund, line_dash="dash", line_color="green", annotation_text="Detected")
            
            # Threshold Line visual
            peak = np.max(y_db)
            fig.add_hline(y=peak-30, line_dash="dot", line_color="red", annotation_text="Threshold (-30dB)")
            
            fig.update_layout(height=500, xaxis_title="Frekuensi (Hz)", yaxis_title="dB")
            fig.update_xaxes(range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error: {e}")
