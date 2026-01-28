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
    # Hindari log(0)
    amplitude_db = 20 * np.log10(amplitude + 1e-6)
    return xf, amplitude_db

# --- KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="ESA Analyzer - Pertamina Patra Niaga")

# --- HEADER ---
st.title("⚡ ESA Real-time Analyzer Prototype")
st.markdown("**Infrastructure Management - Pertamina Patra Niaga**")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🎛️ Simulasi Konsep", "📂 Analisa File (CSV)", "🔴 Real-time Monitor"])

# =========================================
# TAB 1: MODE SIMULASI (Edukasi - Slider)
# =========================================
with tab1:
    col_control, col_display = st.columns([1, 3])
    with col_control:
        st.subheader("Parameter Manual")
        freq_fund = st.number_input("Frekuensi (Hz)", 50.0, disabled=True, key="f1")
        severity = st.slider("Tingkat Kerusakan", 0.0, 10.0, 0.0, key="s1")
        noise = st.slider("Noise Level", 0.0, 0.5, 0.05, key="n1")
        st.info("Geser slider untuk melihat efek statis.")

    # Generate Data Statis
    fs = 2000
    duration = 1.0
    N = int(fs * duration)
    t = np.linspace(0.0, duration, N, endpoint=False)
    
    sig_pure = 100 * np.sin(2 * np.pi * freq_fund * t)
    sig_fault = (severity * 2) * np.sin(2 * np.pi * (freq_fund-5) * t) + \
                (severity * 2) * np.sin(2 * np.pi * (freq_fund+5) * t)
    sig_total = sig_pure + sig_fault + np.random.normal(0, noise * 10, N)

    xf, y_db = perform_esa_analysis(sig_total, fs)

    with col_display:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xf, y=y_db, name='Spectrum', line=dict(color='#EF553B')))
        fig.update_xaxes(range=[30, 70], title="Frekuensi (Hz)")
        fig.update_yaxes(range=[-40, 60], title="Amplitude (dB)")
        fig.add_vline(x=50, line_dash="dash", line_color="green", annotation_text="50Hz")
        if severity > 2:
            fig.add_vline(x=45, line_dash="dot", line_color="red")
            fig.add_vline(x=55, line_dash="dot", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

# =========================================
# TAB 2: MODE ANALISA (Upload CSV)
# =========================================
with tab2:
    st.write("Upload data rekaman dari alat ukur (Time Series Data).")
    uploaded_file = st.file_uploader("Pilih file CSV", type=["csv", "txt"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, header=None)
            data_signal = df.iloc[:, 0].values
            xf_real, y_db_real = perform_esa_analysis(data_signal, 2000) # Asumsi FS 2000
            
            fig_real = go.Figure()
            fig_real.add_trace(go.Scatter(x=xf_real, y=y_db_real, name='Real Data'))
            fig_real.update_layout(title="Hasil Analisa File", xaxis_title="Hz", yaxis_title="dB")
            fig_real.update_xaxes(range=[0, 100])
            st.plotly_chart(fig_real, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

# =========================================
# TAB 3: REAL-TIME MONITOR (Live Demo)
# =========================================
with tab3:
    st.markdown("### 🔴 Live Monitoring Dashboard")
    st.caption("Mensimulasikan pengambilan data sensor secara terus menerus (Streaming).")
    
    col_live_ctrl, col_live_view = st.columns([1, 4])
    
    with col_live_ctrl:
        # Tombol Start/Stop
        run = st.toggle('Mulai Monitoring', value=False)
        
        st.divider()
        st.markdown("**Status Sensor:**")
        if run:
            st.success("CONNECTED (Data Streaming)")
        else:
            st.warning("DISCONNECTED")
            
        st.markdown("**Inject Fault (Realtime):**")
        # Slider ini bisa digeser SAAT grafik berjalan!
        live_severity = st.slider("Simulasi Kerusakan Tiba-tiba", 0.0, 10.0, 0.0, key="live_sev")
        
    with col_live_view:
        # Placeholder untuk grafik yang akan di-update terus menerus
        chart_placeholder = st.empty()
        metric_placeholder = st.empty()
        
        # Loop Realtime
        if run:
            while True:
                # 1. GENERATE DATA BARU (Disini nanti diganti baca USB Serial)
                # ---------------------------------------------------------
                # Simulasi gelombang berjalan (Phase shift)
                now = time.time()
                t_live = np.linspace(now, now + 1.0, 2000, endpoint=False)
                
                # Sinyal Dasar 50Hz
                live_sig = 100 * np.sin(2 * np.pi * 50 * t_live)
                
                # Sinyal Kerusakan (Dikontrol slider kiri)
                live_fault = (live_severity * 3) * np.sin(2 * np.pi * 45 * t_live) + \
                             (live_severity * 3) * np.sin(2 * np.pi * 55 * t_live)
                
                # Noise random agar terlihat seperti sensor asli
                live_noise = np.random.normal(0, 2.0, 2000)
                
                current_signal = live_sig + live_fault + live_noise
                # ---------------------------------------------------------
                
                # 2. PROSES FFT CEPAT
                xf_live, y_db_live = perform_esa_analysis(current_signal, 2000)
                
                # 3. UPDATE GRAFIK
                with chart_placeholder.container():
                    fig_live = go.Figure()
                    
                    # Grafik Spektrum
                    fig_live.add_trace(go.Scatter(
                        x=xf_live, y=y_db_live, 
                        mode='lines', 
                        line=dict(color='#00CC96', width=1),
                        name='Live Spectrum'
                    ))
                    
                    # Limit area agar grafik tidak loncat-loncat
                    fig_live.update_xaxes(range=[30, 70])
                    fig_live.update_yaxes(range=[-40, 60])
                    fig_live.update_layout(
                        title=f"Live Spectrum Analysis (Last Update: {time.strftime('%H:%M:%S')})",
                        height=450,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    
                    # Indikator Alarm Visual
                    fig_live.add_vline(x=50, line_dash="dash", line_color="gray")
                    if live_severity > 3:
                        fig_live.add_shape(type="rect",
                            x0=44, y0=-40, x1=46, y1=60,
                            fillcolor="red", opacity=0.1, line_width=0,
                        )
                        fig_live.add_shape(type="rect",
                            x0=54, y0=-40, x1=56, y1=60,
                            fillcolor="red", opacity=0.1, line_width=0,
                        )
                        
                    st.plotly_chart(fig_live, use_container_width=True)
                
                # 4. UPDATE METRICS
                with metric_placeholder.container():
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Frequency", "50.01 Hz", "0.01%")
                    c2.metric("RMS Current", f"{98 + np.random.rand():.1f} A", "Normal")
                    status = "CRITICAL" if live_severity > 5 else "NORMAL"
                    c3.metric("Motor Health", status, delta_color="inverse" if status=="CRITICAL" else "normal")

                # Delay agar tidak crash browser (simulasi refresh rate sensor)
                time.sleep(0.5) 
                
                # Logic breaker: Stop loop jika tombol dimatikan
                # (Streamlit akan rerun script saat tombol ditekan, memutus while loop)
        else:
            st.info("Klik tombol 'Mulai Monitoring' untuk mengaktifkan sensor.")
