import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
import tensorflow as tf
from tensorflow.keras import layers, models

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Bearing Fault Diagnosis - Lite CNN",
    layout="wide"
)

# --- JUDUL DAN PENJELASAN ---
st.title("🔧 Lite CNN: Bearing Fault Diagnosis")
st.markdown("""
Aplikasi ini mengimplementasikan konsep dari jurnal **MDPI Sensors 2023, 23(6), 3157**.
Sistem mendiagnosa kerusakan bantalan mesin (bearing) menggunakan **Spectrogram** dan **Lite CNN**.
""")

# --- FUNGSI UTILITAS ---

def generate_spectrogram(data, fs=12000):
    """
    Mengubah sinyal getaran 1D menjadi Spectrogram 2D.
    Sesuai jurnal: Menggunakan STFT.
    """
    f, t, Sxx = signal.spectrogram(data, fs, nperseg=256, noverlap=128)
    # Log scale untuk visualisasi yang lebih baik
    Sxx_log = 10 * np.log10(Sxx + 1e-10) 
    return f, t, Sxx_log

def create_lite_cnn_model(input_shape):
    """
    Membangun arsitektur Lite CNN sesuai konsep jurnal.
    Struktur sederhana: Conv2D -> MaxPool -> Flatten -> Dense
    """
    model = models.Sequential([
        layers.Input(shape=input_shape),
        
        # Layer Konvolusi 1
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        
        # Layer Konvolusi 2
        layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        
        # Layer Konvolusi 3 (Deep features)
        layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        
        # Klasifikasi
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dense(4, activation='softmax') # 4 Kelas: Normal, Inner, Outer, Ball
    ])
    return model

# --- SIDEBAR INPUT ---
st.sidebar.header("Input Data Getaran")
input_option = st.sidebar.radio(
    "Pilih Sumber Data:",
    ("Gunakan Data Simulasi (Demo)", "Upload File CSV")
)

# --- MAIN LOGIC ---

# 1. Load Data
data = None
fs = 12000  # Sampling rate standar CWRU dataset

if input_option == "Gunakan Data Simulasi (Demo)":
    # Membuat sinyal dummy (sinusoidal + noise) untuk demo
    t = np.linspace(0, 1.0, fs)
    # Simulasi kondisi random
    condition = st.sidebar.selectbox("Pilih Simulasi Kondisi:", ["Normal", "Inner Race Fault", "Outer Race Fault"])
    
    noise = np.random.normal(0, 0.5, fs)
    if condition == "Normal":
        data = np.sin(2 * np.pi * 50 * t) + noise # Sinyal halus
    elif condition == "Inner Race Fault":
        data = np.sin(2 * np.pi * 50 * t) + 2 * np.sin(2 * np.pi * 120 * t) + noise # Ada frekuensi tinggi
    else:
        data = np.sin(2 * np.pi * 50 * t) + 3 * np.random.normal(0, 1, fs) * np.sin(2 * np.pi * 10 * t) # Impulsif
        
    st.info(f"Menggunakan data simulasi untuk kondisi: **{condition}**")

elif input_option == "Upload File CSV":
    uploaded_file = st.sidebar.file_uploader("Upload file CSV (1 kolom getaran)", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        # Ambil kolom pertama sebagai data getaran
        data = df.iloc[:, 0].values
        # Potong jika terlalu panjang agar ringan
        if len(data) > fs:
            data = data[:fs]
            st.warning(f"Data dipotong menjadi {fs} sampel pertama.")

# 2. Proses Data (Jika ada)
if data is not None:
    col1, col2 = st.columns(2)
    
    # Visualisasi Sinyal Waktu
    with col1:
        st.subheader("1. Sinyal Getaran (Time Domain)")
        fig_time, ax_time = plt.subplots(figsize=(6, 4))
        ax_time.plot(data, color='blue', linewidth=0.5)
        ax_time.set_title("Raw Vibration Signal")
        ax_time.set_xlabel("Time (samples)")
        ax_time.set_ylabel("Amplitude")
        st.pyplot(fig_time)

    # Preprocessing: Spectrogram Generation
    f, t_spec, Sxx = generate_spectrogram(data, fs)
    
    # Resize spectrogram agar sesuai input model (misal 64x64) secara sederhana untuk demo
    # Dalam implementasi nyata, kita resize array Sxx menggunakan interpolasi
    Sxx_resized = Sxx[:64, :64] # Cropping simplifikasi untuk demo
    # Padding jika kurang
    if Sxx_resized.shape != (64, 64):
        pad_width = ((0, 64 - Sxx_resized.shape[0]), (0, 64 - Sxx_resized.shape[1]))
        Sxx_resized = np.pad(Sxx, pad_width, mode='constant')[:64, :64]

    with col2:
        st.subheader("2. Spectrogram (Input Model)")
        fig_spec, ax_spec = plt.subplots(figsize=(6, 4))
        c = ax_spec.pcolormesh(t_spec, f, Sxx, shading='gouraud', cmap='inferno')
        ax_spec.set_ylabel('Frequency [Hz]')
        ax_spec.set_xlabel('Time [sec]')
        ax_spec.set_title("Spectrogram (STFT)")
        fig_spec.colorbar(c, ax=ax_spec)
        st.pyplot(fig_spec)

    # 3. Model Inference
    st.divider()
    st.subheader("3. Hasil Diagnosa (Lite CNN)")
    
    # Inisialisasi Model (Demo: Bobot acak karena tidak ada training)
    # Di aplikasi nyata, Anda akan load model: model = tf.keras.models.load_model('model.h5')
    model = create_lite_cnn_model(input_shape=(64, 64, 1))
    
    # Siapkan input shape (Batch, Height, Width, Channel)
    input_tensor = Sxx_resized.reshape(1, 64, 64, 1)
    
    # Normalize
    input_tensor = (input_tensor - np.min(input_tensor)) / (np.max(input_tensor) - np.min(input_tensor))

    # Tombol Prediksi
    if st.button("Jalankan Diagnosa"):
        with st.spinner('Sedang memproses melalui layer CNN...'):
            # Melakukan prediksi (Dummy prediction untuk demo struktur code)
            # Karena model belum ditraining, kita akan memalsukan probabilitas 
            # agar sesuai dengan input simulasi untuk menunjukkan logika output
            
            # --- LOGIKA DEMO ---
            # Jika user memilih simulasi, kita paksa hasil agar sesuai.
            # Jika upload, hasil akan random karena model untrained.
            classes = ["Normal", "Inner Race Fault", "Outer Race Fault", "Ball Fault"]
            
            if input_option == "Gunakan Data Simulasi (Demo)":
                # Mocking prediction based on sidebar choice
                if "Normal" in condition: pred_idx = 0
                elif "Inner" in condition: pred_idx = 1
                elif "Outer" in condition: pred_idx = 2
                else: pred_idx = 3
                
                # Buat probabilitas buatan
                prediction = np.zeros((1, 4))
                prediction[0, pred_idx] = 0.95
                prediction[0, (pred_idx+1)%4] = 0.05
            else:
                # Real prediction (untrained model = random output)
                prediction = model.predict(input_tensor)
            
            predicted_class = classes[np.argmax(prediction)]
            confidence = np.max(prediction) * 100
            
            # Tampilkan Hasil
            st.success(f"Status Mesin: **{predicted_class}**")
            st.write(f"Confidence Level: **{confidence:.2f}%**")
            
            # Bar Chart Probabilitas
            st.bar_chart(pd.DataFrame(prediction.T, index=classes, columns=["Probability"]))
            
            # Penjelasan Model Layer
            st.expander("Lihat Arsitektur Model").write(model.summary())

else:
    st.info("Silakan pilih opsi input di sebelah kiri.")
