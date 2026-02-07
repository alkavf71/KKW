# modules/temperature_diagnostics.py
from typing import List, Dict

def analyze_temperature_profile(temps: Dict[str, float], limit_warn: float, 
                              noise_type: str, vib_axial_high: bool) -> List[str]:
    """
    DATABASE DIAGNOSA TEMPERATUR (TKI D.1 & D.2 + API 610/682)
    Input:
        - temps: Dict suhu {'Motor DE': 60, ...}
        - limit_warn: Batas peringatan (misal 75C)
        - noise_type: Input dari form noise (Mencicit/Ngorok)
        - vib_axial_high: Boolean (True jika vibrasi Axial dominan)
    """
    diagnosa = []
    
    # Cari lokasi yang overheat
    overheat_points = {loc: val for loc, val in temps.items() if val > limit_warn}
    
    if not overheat_points:
        return [] # Suhu Normal

    for loc, val in overheat_points.items():
        base_msg = f"🔥 OVERHEAT di {loc} ({val}°C)."
        
        # --- KASUS 1: MASALAH PELUMASAN (TKI 1.b, 1.c) ---
        # Logika: Panas + Suara Mencicit
        if noise_type == "Mencicit (Squealing)":
            diagnosa.append(f"{base_msg} PENYEBAB: Kurang Pelumas/Grease Kering (TKI 1.b). REKOMENDASI: Cek visual grease & Regreasing.")
            
        # --- KASUS 2: MASALAH ALIGNMENT (TKI 1.a) ---
        # Logika: Panas di DE (dekat kopling) + Vibrasi Axial Tinggi
        elif "DE" in loc and vib_axial_high:
            diagnosa.append(f"{base_msg} PENYEBAB: Misalignment Coupling (TKI 1.a). REKOMENDASI: Cek Hot Alignment & Posisi Kopling.")
            
        # --- KASUS 3: KERUSAKAN FISIK BEARING (TKI 1.e) ---
        # Logika: Panas + Suara Ngorok
        elif noise_type == "Ngorok/Kasar (Growling)":
            diagnosa.append(f"{base_msg} PENYEBAB: Bearing Rusak/Cacat (TKI 1.e). REKOMENDASI: Ganti Bearing segera.")

        # --- KASUS 4: MASALAH SEAL / GLAND (TKI 2.a, 2.b) ---
        # Logika: Panas di Pump DE (Area Seal) tapi suara normal/desis
        elif "Pump DE" in loc and "Seal" in loc: # Jika user menamai lokasi seal
             diagnosa.append(f"{base_msg} PENYEBAB: Gland Packing Terlalu Kencang atau Seal Flush Buntu (TKI 2.a/b). REKOMENDASI: Kendurkan Gland Nut atau Cek Piping Plan.")
             
        # --- KASUS 5: AXIAL THRUST / GUIDE VANE (TKI 1.d) ---
        # Logika: Panas di Pump DE tapi tidak ada isu pelumas/alignment
        elif "Pump DE" in loc:
             diagnosa.append(f"{base_msg} PENYEBAB: Beban Axial Tinggi / Posisi Guide Vane Salah (TKI 1.d). REKOMENDASI: Cek setelan impeller & axial play.")

        # --- DEFAULT (Jika tidak ada gejala lain) ---
        else:
            diagnosa.append(f"{base_msg} REKOMENDASI: Stop & Periksa Fisik Sesuai TKI D.1.")

    return list(set(diagnosa))
