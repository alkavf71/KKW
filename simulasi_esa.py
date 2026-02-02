import streamlit as st
import numpy as np

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pump Diagnostic Tool", layout="wide")
st.title("🛡️ Electrical Pump Diagnostic System")
st.markdown("Based on **ISO 10816** (Vibration Severity) & **API 686** (Alignment Standards)")

# --- 2. INPUT PARAMETER (Simulasi Data Sensor) ---
st.sidebar.header("⚙️ Input Parameter Motor")

# Input Spesifikasi Motor
rpm_input = st.sidebar.selectbox("Kecepatan Operasi (RPM)", [1500, 3000], index=1)
power_kw = st.sidebar.number_input("Daya Motor (kW)", value=75, help="Digunakan untuk klasifikasi ISO Class")

st.sidebar.markdown("---")
st.sidebar.header("📡 Input Data Vibrasi (Spectrum)")
st.sidebar.info("Masukkan amplitudo vibrasi (mm/s RMS) dari hasil FFT/Sensor")

# Input Amplitudo (Simulasi pembacaan sensor)
# Radial (Biasanya Horizontal)
rad_1x = st.sidebar.number_input("Radial 1x RPM (mm/s)", value=0.5)
rad_2x = st.sidebar.number_input("Radial 2x RPM (mm/s)", value=0.1)
# Axial
ax_1x = st.sidebar.number_input("Axial 1x RPM (mm/s)", value=0.2)

# Hitung Overall RMS (Estimasi sederhana dari komponen dominan)
# Dalam praktek nyata, ini dihitung dari seluruh spektrum
overall_rms = np.sqrt(rad_1x**2 + rad_2x**2 + ax_1x**2)

# --- 3. LOGIKA DIAGNOSA (THE CORE LOGIC) ---

def get_iso_status(rms, kw):
    """
    Menentukan Zone ISO 10816-3.
    Asumsi: Class II (15kW < P < 300kW) - Umum di Terminal BBM
    """
    # Batas Zone untuk Class II (Medium Machine)
    limit_a = 1.12 # Good
    limit_b = 2.80 # Satisfactory
    limit_c = 7.10 # Unsatisfactory
    
    if rms < limit_a:
        return "ZONE A", "Good (Baru)", "success"
    elif rms < limit_b:
        return "ZONE B", "Satisfactory (Aman Beroperasi)", "info"
    elif rms < limit_c:
        return "ZONE C", "Unsatisfactory (Warning - Jadwalkan Perbaikan)", "warning"
    else:
        return "ZONE D", "Unacceptable (DANGER - Stop Mesin)", "error"

def diagnose_fault(rad1, rad2, ax1):
    """
    Logika Rule-Based untuk deteksi Misalignment
    """
    diagnosis = []
    
    # Rule 1: Parallel Misalignment
    # Ciri: Vibrasi Radial 2x RPM tinggi (biasanya > 50% dari 1x RPM)
    if rad2 >= (0.5 * rad1) and rad2 > 0.5: 
        diagnosis.append("PARALLEL MISALIGNMENT (High 2x RPM Radial)")

    # Rule 2: Angular Misalignment
    # Ciri: Vibrasi Axial tinggi (dominan di 1x RPM)
    if ax1 >= (0.5 * rad1) and ax1 > 0.5:
        diagnosis.append("ANGULAR MISALIGNMENT (High Axial Vibration)")
        
    if not diagnosis and overall_rms > 2.8:
        diagnosis.append("Unbalance / Looseness (Perlu analisa lanjut)")
    elif not diagnosis:
        diagnosis.append("Normal Spectrum Pattern")
        
    return diagnosis

def get_api_limits(rpm):
    """
    Mengambil batas toleransi API 686 berdasarkan RPM
    """
    if rpm >= 3000:
        return {"offset": "0.04 mm", "angular": "0.05 mm/100mm"}
    else:
        return {"offset": "0.09 mm", "angular": "0.07 mm/100mm"}

# Eksekusi Logika
zone, status_text, color_code = get_iso_status(overall_rms, power_kw)
faults = diagnose_fault(rad_1x, rad_2x, ax_1x)
limits = get_api_limits(rpm_input)

# --- 4. TAMPILAN DASHBOARD (UI) ---

# Kolom Atas: Status Utama
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Kondisi Umum (ISO 10816)")
    st.metric(label="Overall Velocity RMS", value=f"{overall_rms:.2f} mm/s")
    
    if color_code == "success":
        st.success(f"**{zone}**: {status_text}")
    elif color_code == "info":
        st.info(f"**{zone}**: {status_text}")
    elif color_code == "warning":
        st.warning(f"**{zone}**: {status_text}")
    else:
        st.error(f"**{zone}**: {status_text}")

with col2:
    st.subheader("🔍 Diagnosa Spesifik")
    for fault in faults:
        if "MISALIGNMENT" in fault:
            st.error(f"⚠️ Terdeteksi: **{fault}**")
        elif "Normal" in fault:
            st.success(f"✅ {fault}")
        else:
            st.warning(f"⚠️ {fault}")

st.markdown("---")

# Kolom Bawah: Rekomendasi API 686
st.subheader("🛠️ Rekomendasi Perbaikan (Standar API 686)")

if "MISALIGNMENT" in str(faults):
    st.markdown(f"""
    Berdasarkan diagnosa di atas, pompa mengalami indikasi **Misalignment**. 
    Sesuai standar **API 686 Chapter 7** untuk motor **{rpm_input} RPM**, 
    lakukan perbaikan dengan target toleransi berikut:
    """)
    
    col_rec1, col_rec2 = st.columns(2)
    with col_rec1:
        st.info(f"**Target Offset (Parallel):**\n### < {limits['offset']}")
        st.caption("Gunakan Dial Indicator/Laser pada posisi jam 9-3 atau 12-6.")
        
    with col_rec2:
        st.info(f"**Target Angular (Sudut):**\n### < {limits['angular']}")
        st.caption("Perbedaan gap per 100mm jarak kopling.")

    with st.expander("Lihat Prosedur Koreksi (API 686)"):
        st.markdown("""
        1. **Soft Foot Check:** Pastikan semua kaki motor menapak sempurna (max 0.05mm gap).
        2. **Rough Alignment:** Lakukan pelurusan visual.
        3. **Laser/Dial Measurement:** Ambil data As-Found.
        4. **Vertical Move:** Tambah/kurang shim sesuai perhitungan.
        5. **Horizontal Move:** Geser motor menggunakan *jack bolts*.
        6. **Final Check:** Pastikan nilai masuk dalam toleransi di atas.
        """)
else:
    st.markdown("Tidak ada indikasi misalignment yang signifikan. Pertahankan jadwal *Preventive Maintenance* rutin.")

# Footer
st.markdown("---")
st.caption("Developed for Improvement Project - Infrastructure Management & Project (PT Pertamina Patra Niaga)")
