from typing import List, Dict

def assess_overall_health(vib_zone: str, elec_status: str, temp_max: float, physical_issues: List[str]) -> Dict:
    severity = 0
    reasons = []

    if "ZONE D" in vib_zone: 
        severity += 3
        reasons.append("Vibrasi DANGER (Zone D)")
    elif "ZONE C" in vib_zone: 
        severity += 1
        reasons.append("Vibrasi WARNING (Zone C)")

    if "TRIP" in elec_status: 
        severity += 3
        reasons.append("Elektrikal TRIP")
    
    if temp_max > 85.0: 
        severity += 3
        reasons.append(f"Overheat ({temp_max}°C)")

    for issue in physical_issues:
        if "MAJOR" in issue.upper() or "CRITICAL" in issue.upper():
            severity += 5
            reasons.append(f"Fisik: {issue}")
        elif "MINOR" in issue.upper():
            severity += 1
            reasons.append(f"Fisik: {issue}")

    if severity >= 3:
        return {"status": "BAD", "color": "#e74c3c", "desc": "RUSAK BERAT", "action": "❌ STOP OPERASI. Perbaikan Major.", "reasons": reasons}
    elif severity >= 1:
        return {"status": "FAIR", "color": "#f1c40f", "desc": "WARNING", "action": "⚠️ PENGAWASAN KHUSUS.", "reasons": reasons}
    else:
        return {"status": "GOOD", "color": "#2ecc71", "desc": "PRIMA", "action": "✅ LANJUT OPERASI.", "reasons": reasons}
