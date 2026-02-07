# modules/noise_diagnostics.py
from typing import List

def analyze_noise_profile(noise_type: str, noise_loc: str, valve_test: str) -> List[str]:
    """
    DATABASE DIAGNOSA NOISE LENGKAP (FULL VERSION)
    Referensi: ISO 18436-2, API 610, TKI C-017
    Sesuai Spreadsheet: LOGIC_NOISE
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
        diagnosa.append("🔊 KAVITASI (Ref: API 610): Suara 'kerikil' akibat gelembung pecah. REKOMENDASI: Cek Strainer Buntu / Level Tangki Rendah / NPSH.")

    # --- 3. FLOW NOISE (Valve Test) - API 610 ---
    # Case A: Recirculation (Low Flow)
    if valve_test == "Suara Berubah Drastis (Recirculation/Kavitasi Hilang)" or noise_type == "Gemuruh (Rumbling)":
        diagnosa.append("🌊 FLOW RECIRCULATION (Ref: API 610): Operasi di bawah Flow Minimum (Low Flow). REKOMENDASI: Buka valve discharge atau jalur min-flow.")
    
    # Case B: High Flow Turbulence (Baru Ditambahkan sesuai Spreadsheet)
    if noise_type == "Desis Keras (Hissing/Roaring)":
         diagnosa.append("🌊 HIGH FLOW TURBULENCE (Ref: API 610): Operasi di atas kapasitas (Over Flow). REKOMENDASI: Cek bukaan valve, kembalikan ke titik BEP.")

    # --- 4. GENERAL NOISE (Looseness & Electrical) ---
    # Case C: Mechanical Looseness
    if noise_type == "Klotak-klotak (Rattling)":
        diagnosa.append("🔧 MECHANICAL LOOSENESS (Ref: API 686): Suara klotak/logam longgar. REKOMENDASI: Cek kekencangan Baut Pondasi (Anchor Bolt) & Soft Foot.")

    # Case D: Electrical Fault (Baru Ditambahkan sesuai Spreadsheet)
    if noise_type == "Dengung Kuat (Loud Humming)" and "Motor" in noise_loc:
        diagnosa.append("⚡ ELECTRICAL FAULT (Ref: IEEE 112): Dengung kuat indikasi Single Phasing atau Air Gap tidak rata. REKOMENDASI: Cek Panel Listrik & Fisik Motor.")

    # Case E: Rotor Unbalance
    if noise_type == "Dengung Berirama (Rhythmic Wow-wow)":
        diagnosa.append("🟠 ROTOR UNBALANCE (Ref: ISO 10816): Suara dengung berirama putaran. REKOMENDASI: Cek kebersihan kipas/impeller & Balancing.")

    return diagnosa
