from typing import List

def analyze_noise_profile(noise_type: str, noise_loc: str, valve_test: str) -> List[str]:
    diagnosa = []
    if noise_type == "Ngorok/Kasar (Growling)":
        diagnosa.append("🔊 BEARING DEFECT: Suara ngorok. Ganti Bearing.")
    elif noise_type == "Mencicit (Squealing)":
        diagnosa.append("🔊 LUBRICATION ISSUE: Kurang pelumas. Regreasing.")
    elif noise_type == "Gesekan Logam (Scraping)":
        diagnosa.append("🔊 RUBBING: Gesekan poros.")
    
    if noise_type == "Suara Kerikil/Letupan (Popping)" or "Casing" in noise_loc:
        diagnosa.append("🔊 KAVITASI: Suara kerikil. Cek Strainer/Level Tangki.")

    if valve_test == "Suara Berubah Drastis (Recirculation)" or noise_type == "Gemuruh (Rumbling)":
        diagnosa.append("🌊 FLOW RECIRCULATION: Flow minimum. Buka valve discharge.")
    
    return diagnosa
