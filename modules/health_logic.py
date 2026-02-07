from typing import List, Dict

def assess_overall_health(vib_status: str, elec_status: str, temp_max: float, physical_issues: List[str], tech_diagnoses: List[str]) -> Dict:
    """
    Fungsi ini sekarang menerima 'tech_diagnoses' (Daftar penyebab teknis)
    untuk menghasilkan rekomendasi spesifik dan standar referensi.
    """
    
    severity = 0
    reasons = []
    recommendations = []
    standards_used = set() # Pakai set agar tidak duplikat

    # --- 1. KAMUS REKOMENDASI & STANDAR (KNOWLEDGE BASE) ---
    # Format: "Kata Kunci": ("Saran Perbaikan", "Standar Referensi")
    knowledge_base = {
        "Misalignment": ("Lakukan Laser Alignment ulang (Toleransi 0.05mm). Cek shimming.", "API 686 Ch. 4 (Alignment)"),
        "Unbalance": ("Lakukan Balancing Impeller/Rotor di workshop (Grade G6.3/G2.5).", "ISO 1940-1 (Balancing)"),
        "Soft Foot": ("Cek kekencangan baut kaki motor. Perbaiki shim jika ada celah >0.05mm.", "API 686 Ch. 5 (Mounting)"),
        "Bearing": ("Jadwalkan penggantian Bearing (DE/NDE). Cek housing fit.", "SKF General Catalogue / OEM"),
        "Looseness": ("Kencangkan seluruh baut pondasi & baseplate. Cek keretakan grouting.", "API 686 Ch. 5"),
        "Bent Shaft": ("Cek run-out poros dengan Dial Indicator (Max 0.05mm).", "API 610 (Pump Shaft Runout)"),
        "Kavitasi": ("Cek NPSH Available. Pastikan valve suction terbuka 100%. Cek strainer buntu.", "API 610 (Centrifugal Pumps)"),
        "Flow": ("Atur bukaan valve discharge agar masuk ke range operasional (BEP).", "API 610 (Operating Region)"),
        "Overheat": ("Cek sistem pendingin (Fan/Sirip). Pastikan tidak Overload.", "NEMA MG-1 / IEEE 1415"),
        "Seal": ("Ganti Mechanical Seal. Cek sistem flushing.", "API 682 (Sealing Systems)"),
        "Guard": ("Pasang kembali Coupling Guard sesuai standar safety.", "OSHA / Safety Regulation"),
        "Volt": ("Cek tegangan input dari panel/PLN. Pastikan unbalance < 3%.", "NEMA MG-1 / ANSI C84.1"),
        "Curr": ("Cek beban motor. Pastikan tidak melebihi FLA.", "NEMA MG-1")
    }

    # --- 2. ANALISA VIBRASI (ZONA ISO) ---
    if "ZONE D" in vib_status: 
        severity += 3
        reasons.append(f"Vibrasi KRITIS ({vib_status})")
        standards_used.add("ISO 10816-3 (Vibration Severity)")
    elif "ZONE C" in vib_status: 
        severity += 1
        reasons.append(f"Vibrasi TINGGI ({vib_status})")
        standards_used.add("ISO 10816-3 (Vibration Severity)")
    elif "ZONE A" in vib_status:
        standards_used.add("ISO 10816-3 (New Machine Condition)")

    # --- 3. ANALISA DIAGNOSA TEKNIS (AUTO-MAPPING) ---
    # Loop setiap diagnosa yang ditemukan (misal: "Misalignment", "Overheat")
    for diag in tech_diagnoses:
        reasons.append(diag) # Tambahkan ke daftar masalah
        
        # Cari rekomendasi yang cocok dari knowledge_base
        for keyword, (action, std) in knowledge_base.items():
            if keyword.upper() in diag.upper():
                if action not in recommendations: recommendations.append(action)
                standards_used.add(std)

    # --- 4. ANALISA FISIK & LAINNYA ---
    if "TRIP" in elec_status: 
        severity += 3
        reasons.append("Elektrikal TRIP")
        recommendations.append("Cek Panel Elektrikal & Kabel Power.")
    
    if temp_max > 85.0: 
        severity += 3
        # (Recommendation sudah dicover oleh logic "Overheat" di atas)

    for issue in physical_issues:
        if "MAJOR" in issue.upper() or "CRITICAL" in issue.upper():
            severity += 5
            reasons.append(f"Fisik: {issue}")
        elif "MINOR" in issue.upper():
            severity += 1
            reasons.append(f"Fisik: {issue}")
        
        # Mapping manual untuk fisik
        if "Seal" in issue: standards_used.add("API 682")
        if "Guard" in issue: standards_used.add("OSHA Safety")

    # --- 5. KESIMPULAN FINAL ---
    if severity >= 3:
        status = "BAD / DANGER"
        color = "#e74c3c" # Merah
        desc = "KONDISI KRITIS - STOP OPERASI"
        final_action = "❌ SEGERA LAKUKAN PERBAIKAN (Lihat Rekomendasi di Bawah)"
    elif severity >= 1:
        status = "FAIR / WARNING"
        color = "#f1c40f" # Kuning
        desc = "PERLU MONITORING KETAT"
        final_action = "⚠️ JADWALKAN MAINTENANCE (Planned Work Order)"
    else:
        status = "GOOD / PRIMA"
        color = "#2ecc71" # Hijau
        desc = "SIAP OPERASI"
        final_action = "✅ LANJUTKAN OPERASI RUTIN"
        if not recommendations: recommendations.append("Pertahankan kondisi operasi.")

    return {
        "status": status,
        "color": color,
        "desc": desc,
        "action": final_action,
        "reasons": reasons,
        "recommendations": recommendations,
        "standards": list(standards_used)
    }
