# modules/noise_diagnostics.py
from typing import List

def analyze_noise_profile(noise_type: str, noise_loc: str, valve_test: str) -> List[str]:
    """
    DATABASE DIAGNOSA NOISE
    Referensi: ISO 18436-2, API 610, TKI C-017
    """
    diagnosa = []
    
    # --- 1. SHAFT NOISE (Bearing & Rubbing) - ISO 18436-2 ---
    if noise_type == "Ngorok/Kasar (Growling)":
        diagnosa.append("🔊 BEARING DEFECT (Ref: ISO 18436-2): Suara ngorok indikasi kerusakan lintasan bearing (Spalling). REKOMENDASI: Ganti Bearing.")
    
    elif noise_type == "Mencicit (Squealing)":
        diagnosa.append("🔊 LUBRICATION ISSUE (Ref: ISO 18436-2): Suara mencicit indikasi kurang pelumas/grease. REKOMENDASI: Lakukan Regreasing segera.")
    
    elif noise_type == "Gesekan Logam (Scraping)":
        diagnosa.append("🔊 RUBBING/MISALIGNMENT (Ref: API 686): Poros bergesek. REKOMENDASI: Cek Alignment & Run-out Poros.")

    # --- 2. CAVITATION (Hydraulic) - API 610 ---
    if noise_type == "Suara Kerikil/Letupan (Popping)" or "Pump Casing" in noise_loc:
        diagnosa.append("🔊 KAVITASI (Ref: API 610): Suara 'kerikil' akibat gelembung pecah. REKOMENDASI: Cek Strainer Buntu / Level Tangki Rendah.")

    # --- 3. FLOW NOISE (Valve Test) - API 610 / TKI C-017 ---
    if valve_test == "Suara Berubah Drastis (Recirculation/Kavitasi Hilang)":
        diagnosa.append("🌊 FLOW RECIRCULATION (Ref: API 610): Operasi di luar titik efisien (BEP). REKOMENDASI: Atur bukaan valve agar flow masuk range aman.")
        
    # --- 4. LOOSENESS - API 686 ---
    if noise_type == "Gemuruh (Rumbling)" and "Motor" in noise_loc:
        diagnosa.append("🔊 MECHANICAL LOOSENESS (Ref: API 686): Suara gemuruh/klotak. REKOMENDASI: Cek kekencangan Baut Pondasi (Anchor Bolt).")

    return diagnosa
