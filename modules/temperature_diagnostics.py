from typing import List, Dict

def analyze_temperature_profile(temps: Dict[str, float], limit_warn: float, noise_type: str, vib_axial_high: bool) -> List[str]:
    diagnosa = []
    overheat = {loc: val for loc, val in temps.items() if val > limit_warn}
    
    for loc, val in overheat.items():
        msg = f"🔥 OVERHEAT {loc} ({val}°C)."
        if noise_type == "Mencicit (Squealing)":
            diagnosa.append(f"{msg} SEBAB: Kurang Grease.")
        elif "DE" in loc and vib_axial_high:
            diagnosa.append(f"{msg} SEBAB: Misalignment.")
        elif noise_type == "Ngorok/Kasar (Growling)":
            diagnosa.append(f"{msg} SEBAB: Bearing Rusak.")
        elif "Pump" in loc and "Seal" in loc:
             diagnosa.append(f"{msg} SEBAB: Gland Packing Kencang/Seal Flush Buntu.")
        else:
            diagnosa.append(f"{msg} ACTION: Cek Fisik.")
    return list(set(diagnosa))
