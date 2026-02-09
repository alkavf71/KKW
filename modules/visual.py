import streamlit as st

def app():
    st.header("👁️ Inspeksi Visual & Fisik (API 686)")
    st.info("Checklist kondisi fisik pompa dan motor sebelum pengujian running.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Kondisi Umum")
        check_1 = st.checkbox("Kebersihan Area (Housekeeping)")
        check_2 = st.checkbox("Kondisi Baseplate (Tidak Retak/Kropos)")
        check_3 = st.checkbox("Grouting (Padat/Tidak Bunyi saat diketok)")
        check_4 = st.checkbox("Baut Pondasi (Anchor Bolt) Kencang")

    with col2:
        st.subheader("Kondisi Mekanikal & Safety")
        check_5 = st.checkbox("Seal/Gland Packing (Tidak Bocor Berlebih)")
        check_6 = st.checkbox("Safety Guard Kopling Terpasang")
        check_7 = st.checkbox("Level Oli / Grease Cukup")
        check_8 = st.checkbox("Grounding Cable Terpasang")

    st.divider()
    
    # Hitung Skor Kesehatan Visual
    checklist = [check_1, check_2, check_3, check_4, check_5, check_6, check_7, check_8]
    score = sum(checklist)
    total = len(checklist)
    
    st.metric("Skor Visual", f"{score}/{total}")
    
    if score == total:
        st.success("Visual Inspection: PASSED")
    else:
        st.warning(f"Visual Inspection: {total - score} Temuan (Harap Catat di Remark)")
        st.text_area("Catatan Temuan (Remark)", placeholder="Contoh: Baut pondasi sisi DE kendor...")
