from typing import List, Dict

def assess_overall_health(vib_status: str, elec_status: str, temp_max: float, physical_issues: List[str], tech_diagnoses: List[str]) -> Dict:
    
    severity = 0
    reasons = []
    recommendations = []
    standards_used = set() 

    # --- 1. KAMUS REKOMENDASI & STANDAR (UPDATED SESUAI STANDAR PERUSAHAAN) ---
    knowledge_base = {
        # MEKANIKAL (PUMP & VIBRATION)
        "Misalignment": ("Lakukan Laser Alignment ulang. Cek shimming & Soft Foot.", "API 686 / ISO 13709"),
        "Unbalance": ("Lakukan Balancing Impeller (Grade G2.5/G6.3).", "ISO 21940 (Balancing)"),
        "Soft Foot": ("Cek kekencangan baut kaki motor. Perbaiki shim.", "API 686 Ch. 5"),
        "Bearing": ("Jadwalkan penggantian Bearing. Cek clearance.", "ISO 13709 (API 610)"),
        "Looseness": ("Kencangkan baut pondasi/baseplate.", "ISO 13709 / API 686"),
        "Bent Shaft": ("Cek run-out poros (Max 0.05mm).", "ISO 13709 (API 610)"),
        "Kavitasi": ("Cek NPSH Available & Strainer Suction.", "ISO 13709 (API 610)"),
        "Flow": ("Atur valve discharge ke range BEP (Best Efficiency Point).", "ISO 13709 (API 610)"),
        
        # SUHU & ELEKTRIKAL (IEC STANDARD)
        "Overheat": ("Cek sistem pendingin (Fan/Sirip) & Beban.", "IEC 60034-1 (Thermal Class)"),
        "Volt": ("Cek tegangan input. Pastikan variasi < 10%.", "IEC 60034-1 (Rating & Performance)"),
        "Curr": ("Cek beban motor (Overload) & Keseimbangan Fasa.", "IEC 60034-1"),
        
        # FISIK & SAFETY
        "Seal": ("Ganti Mechanical Seal. Cek flushing system.", "API 682 / ISO 21049"),
        "Guard": ("Pasang Coupling Guard (Safety Hazard).", "OSHA 1910 / ISO 45001"),
        "Ground": ("Perbaiki kabel Grounding (Electrical Safety).", "OSHA 1910 / PUIL")
    }

    # --- 2. ANALISA VIBRASI (GANTI KE ISO 20816) ---
    if "ZONE D" in vib_status: 
        severity += 3
        reasons.append(f"Vibrasi KRITIS ({vib_status})")
        standards_used.add("ISO 20816 (Vibration Severity)") # Updated dari 10816
    elif "ZONE C" in vib_status: 
        severity += 1
        reasons.append(f"Vibrasi TINGGI ({vib_status})")
        standards_used.add("ISO 20816 (Vibration Severity)") # Updated dari 10816
    elif "ZONE A" in vib_status:
        standards_used.add("ISO 20816 (New Machine)") # Updated dari 10816

    # --- 3. ANALISA DIAGNOSA TEKNIS ---
    for diag in tech_diagnoses:
        reasons.append(diag)
        for keyword, (action, std) in knowledge_base.items():
            if keyword.upper() in diag.upper():
                if action not in recommendations: recommendations.append(action)
                standards_used.add(std)

    # --- 4. ANALISA FISIK ---
    if "TRIP" in elec_status: 
        severity += 3
        reasons.append("Elektrikal TRIP")
        recommendations.append("Cek Panel & Isolasi Motor.")
    
    if temp_max > 85.0: 
        severity += 3
        
    for issue in physical_issues:
        if "MAJOR" in issue.upper() or "CRITICAL" in issue.upper():
            severity += 5
            reasons.append(f"Fisik: {issue}")
        elif "MINOR" in issue.upper():
            severity += 1
            reasons.append(f"Fisik: {issue}")
        
        # Mapping manual standar fisik
        if "Seal" in issue: standards_used.add("API 682")
        if "Guard" in issue: standards_used.add("ISO 45001 (Safety)")
        if "Oli" in issue: standards_used.add("ISO 12922 (Lubricants)")

    # --- 5. KESIMPULAN FINAL ---
    if severity >= 3:
        status = "BAD / DANGER"
        color = "#e74c3c"
        desc = "KONDISI KRITIS - STOP OPERASI"
        final_action = "❌ SEGERA LAKUKAN PERBAIKAN (Lihat Rekomendasi)"
    elif severity >= 1:
        status = "FAIR / WARNING"
        color = "#f1c40f"
        desc = "PERLU MONITORING KETAT"
        final_action = "⚠️ JADWALKAN MAINTENANCE (Planned WO)"
    else:
        status = "GOOD / PRIMA"
        color = "#2ecc71"
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
