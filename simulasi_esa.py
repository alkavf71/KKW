# ==============================================================================
# TAB 4: HYDRAULIC PERFORMANCE (SMART DIAGNOSIS UPGRADE)
# ==============================================================================
with tab4:
    st.header("🌊 Hydraulic Performance Monitoring")
    st.caption("Evaluasi kesehatan internal pompa (Impeller/Wear Ring) berdasarkan standar API 610 / ISO 9906.")

    col_h1, col_h2 = st.columns([1, 1.5])

    with col_h1:
        with st.form("hydro_form"):
            st.subheader("Input Data Operasi")
            
            # 1. Data Tekanan
            st.markdown("##### 1. Pressure Gauge Reading")
            p_suction = st.number_input("Suction Pressure (Bar_g)", value=0.5, help="Tekanan di sisi hisap.")
            p_discharge = st.number_input("Discharge Pressure (Bar_g)", value=4.5, help="Tekanan di sisi buang.")
            
            # 2. Data Fluida
            st.markdown("##### 2. Properties Fluida")
            sg_fluid = st.number_input("Specific Gravity (SG)", value=0.74, min_value=0.1, max_value=2.0, help="Pertamax ~0.74, Solar ~0.84, Air=1.0")
            
            # 3. Data Desain
            st.markdown("##### 3. Data Desain (Referensi)")
            design_head = st.number_input("Rated Head (meter)", value=60.0, help="Lihat di Nameplate pompa (H).")
            
            submit_hydro = st.form_submit_button("🔍 ANALISA PERFORMA HYDRAULIC")

    # --- LOGIC PERHITUNGAN & DIAGNOSA CERDAS ---
    if submit_hydro:
        # Rumus Dasar: Head = (P_out - P_in) * 10.197 / SG
        diff_press = p_discharge - p_suction
        actual_head = (diff_press * 10.197) / sg_fluid
        
        # Hitung Deviasi (%)
        deviation = ((actual_head - design_head) / design_head) * 100
        
        # --- LOGIKA DIAGNOSA & REKOMENDASI (Sesuai Standar) ---
        # Standar API 610: Toleransi Head biasanya +/- 3% sampai 5% di Rated Point.
        # Penurunan > 10% dianggap degradasi serius.
        
        if deviation < -20.0:
            # KONDISI: Head Drop Parah (>20%)
            h_status = "CRITICAL / FAILURE"
            h_color = "#e74c3c" # Merah
            h_cause = "Kerusakan Internal Parah (Impeller Habis / Wear Ring Longgar)."
            h_action = "❌ STOP & OVERHAUL: Ganti Impeller & Wear Ring. Cek Celah (Clearance)."
            h_std = "API 610 (Performance Drop)"
            
        elif deviation < -10.0:
            # KONDISI: Head Drop Sedang (10-20%)
            h_status = "DEGRADATION / WARNING"
            h_color = "#e67e22" # Oranye
            h_cause = "Keausan Internal (Wear Ring Gap Melebar) atau RPM Turun."
            h_action = "⚠️ JADWALKAN MAINTENANCE: Cek efisiensi & clearance wear ring saat stop."
            h_std = "ISO 9906 (Head Tolerance)"
            
        elif deviation > 15.0:
            # KONDISI: Head Terlalu Tinggi (Sumbatan)
            h_status = "RESTRICTION / HIGH HEAD"
            h_color = "#f1c40f" # Kuning
            h_cause = "Valve Discharge Kurang Buka atau Pipa Discharge Buntu."
            h_action = "🔧 CEK OPERASIONAL: Pastikan valve discharge terbuka sesuai SOP."
            h_std = "System Curve Analysis"
            
        else:
            # KONDISI: Normal (+/- 10%)
            h_status = "NORMAL / HEALTHY"
            h_color = "#2ecc71" # Hijau
            h_cause = "Performa pompa sesuai kurva desain."
            h_action = "✅ LANJUTKAN OPERASI: Monitor parameter rutin."
            h_std = "API 610 (Rated Point)"

        # --- TAMPILAN HASIL ---
        with col_h2:
            st.markdown(f"### Hasil Analisa")
            
            # Metric Card
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Diff. Pressure", f"{diff_press:.2f} Bar")
            c_m2.metric("Actual Head", f"{actual_head:.1f} m", f"{deviation:.1f}%")
            c_m3.metric("Status", h_status)

            # Visualisasi Gauge
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = actual_head,
                title = {'text': "Total Dynamic Head (m)"},
                delta = {'reference': design_head, 'relative': True, "valueformat": ".1%"},
                gauge = {
                    'axis': {'range': [0, design_head * 1.4]},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, design_head * 0.80], 'color': "#ffcccc"}, # Zona Rusak
                        {'range': [design_head * 0.80, design_head * 0.90], 'color': "#ffe5b4"}, # Zona Warning
                        {'range': [design_head * 0.90, design_head * 1.15], 'color': "#d4edda"}  # Zona Sehat
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': design_head}
                }
            ))
            fig_gauge.update_layout(height=230, margin=dict(t=30,b=20,l=20,r=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

            # KOTAK DIAGNOSA CERDAS
            st.markdown(f"""
            <div style="background-color:{h_color}22; padding:15px; border-left:5px solid {h_color}; border-radius:5px;">
                <h4 style="color:{h_color}; margin:0;">{h_status}</h4>
                <p style="margin-top:10px;"><strong>🔍 Diagnosa Penyebab:</strong><br>{h_cause}</p>
                <p><strong>🛠️ Rekomendasi (Action):</strong><br>{h_action}</p>
                <hr>
                <p style="font-size:12px; color:#666;">📚 Standar Acuan: {h_std}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Expander Rumus
            with st.expander("Lihat Rumus Perhitungan"):
                st.latex(r"H_{actual} = \frac{(P_{out} - P_{in}) \times 10.197}{SG}")
                st.write("Jika deviasi Head > -10%, itu indikasi 'Internal Recirculation' akibat Wear Ring yang aus (Gap melebar).")
