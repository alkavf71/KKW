import streamlit as st
from modules import mechanical, electrical, visual

# Konfigurasi Halaman
st.set_page_config(page_title="Pertamina Patra Niaga - Inspection App", layout="wide", page_icon="🛢️")

def main():
    # Sidebar dengan Logo dan Navigasi
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/b/b3/Pertamina_Logo.svg", width=150) # Ganti dengan logo PPN jika ada URL publik
        st.title("Sistem Inspeksi Pompa")
        st.caption("Divisi Infrastructure Management & Project")
        
        menu = st.radio(
            "Pilih Modul Inspeksi:",
            ["🏠 Dashboard", "⚙️ Mechanical (Vibrasi)", "⚡ Electrical", "👁️ Visual & Fisik"]
        )

    # Routing Menu
    if menu == "🏠 Dashboard":
        st.title("Dashboard Inspeksi")
        st.info("Selamat datang. Silakan pilih modul inspeksi di menu sebelah kiri.")
        st.markdown("""
        **Fitur Aplikasi:**
        - **Mechanical:** Input data Vibrasi (ISO 10816-3) dengan Auto-Diagnosa.
        - **Electrical:** Input Ampere & Megger (IEEE 43).
        - **Visual:** Checklist fisik (API 686).
        """)
        
    elif menu == "⚙️ Mechanical (Vibrasi)":
        mechanical.app()
        
    elif menu == "⚡ Electrical":
        electrical.app()
        
    elif menu == "👁️ Visual & Fisik":
        visual.app()

if __name__ == "__main__":
    main()
