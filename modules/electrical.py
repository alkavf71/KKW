import streamlit as st

def app():
    st.header("⚡ Inspeksi Elektrikal")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Data Arus (Ampere)")
        r_amp = st.number_input("Phase R (A)", min_value=0.0)
        s_amp = st.number_input("Phase S (A)", min_value=0.0)
        t_amp = st.number_input("Phase T (A)", min_value=0.0)
        
        if r_amp > 0:
            avg_amp = (r_amp + s_amp + t_amp) / 3
            unbalance = max(abs(r_amp-avg_amp), abs(s_amp-avg_amp), abs(t_amp-avg_amp)) / avg_amp * 100
            st.metric("Unbalance Arus", f"{unbalance:.2f}%")
            if unbalance > 10:
                st.error("Unbalance Tinggi (>10%)! Cek koneksi atau lilitan.")
            else:
                st.success("Balance Arus OK")

    with col2:
        st.subheader("Insulation Resistance (Megger)")
        ir_val = st.number_input("Nilai IR (MΩ)", min_value=0.0)
        if ir_val > 0:
            if ir_val < 2.0: # Asumsi motor LV
                st.error("⚠️ IR Rendah / Winding Basah (IEEE 43)")
            else:
                st.success("Isolasi Winding Baik")
