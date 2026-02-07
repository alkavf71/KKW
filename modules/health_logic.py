# modules/health_logic.py
from typing import List, Dict

def assess_overall_health(
    vib_zone: str,          # Zone A/B/C/D
    elec_status: str,       # Normal / Alarm / Trip
    temp_max: float,        # Suhu Tertinggi
    physical_issues: List[str] # List masalah fisik dari checklist gambar
) -> Dict:
    """
    LOGIC DATABASE: Menentukan Status GOOD/FAIR/BAD
    Gabungan Sensor + Fisik (Sesuai Screenshot User)
    """
    
    # 1. Kumpulkan Skor Keburukan (Severity Score)
    # Semakin tinggi skor, semakin parah (Bad)
    severity_score = 0
    reasons = []

    # --- CEK SENSOR (VIBRASI) ---
    if "ZONE D" in vib_zone:
        severity_score += 3 # Critical
        reasons.append("Sensor: Vibrasi Zona Bahaya (Zone D)")
    elif "ZONE C" in vib_zone:
        severity_score += 1 # Warning
        reasons.append("Sensor: Vibrasi Tinggi (Zone C)")

    # --- CEK SENSOR (ELEKTRIKAL) ---
    if "TRIP" in elec_status:
        severity_score += 3
        reasons.append("Sensor: Elektrikal Trip/Fault")
    elif "ALARM" in elec_status:
        severity_score += 1

    # --- CEK SENSOR (SUHU) ---
    if temp_max > 85.0:
        severity_score += 3
        reasons.append(f"Sensor: Overheat ({temp_max}°C)")
    elif temp_max > 75.0:
        severity_score += 1

    # --- CEK FISIK (SESUAI GAMBAR) ---
    for issue in physical_issues:
        if "MAJOR" in issue.upper() or "NOT COST EFFECTIVE" in issue.upper():
            severity_score += 5 # Ini pasti BAD
            reasons.append(f"Fisik: {issue}")
        elif "MINOR" in issue.upper() or "WELD REPAIRS" in issue.upper():
            severity_score += 1
            reasons.append(f"Fisik: {issue}")

    # 2. TENTUKAN KESIMPULAN (DECISION MATRIX)
    result = {}
    
    if severity_score >= 3:
        result = {
            "status": "BAD",
            "color": "red",
            "desc": "KONDISI KRITIS (Rusak Berat)",
            "action": "❌ STOP OPERASI. Perbaikan mungkin tidak ekonomis (Cost Effective Check). Ganti Unit/Part Utama."
        }
    elif severity_score >= 1:
        result = {
            "status": "FAIR",
            "color": "orange",
            "desc": "KONDISI WARNING (Cukup)",
            "action": "⚠️ PENGAWASAN KHUSUS. Jadwalkan perbaikan minor & lengkapi part yang hilang."
        }
    else:
        result = {
            "status": "GOOD",
            "color": "green",
            "desc": "KONDISI PRIMA (Baik)",
            "action": "✅ LANJUT OPERASI. Tidak ada kerusakan berarti."
        }
        
    result['reasons'] = reasons
    return result
