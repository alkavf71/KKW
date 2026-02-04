# iso_logic.py

def get_vibration_status(velocity_rms, machine_class="Class II"):
    """
    Menentukan Zona Vibrasi berdasarkan ISO 10816-1 (Sesuai TKI C-04).
    Fokus pada Class II (Medium Machines 15kW - 300kW).
    """
    
    # Limit diambil dari Tabel TKI C-04 Halaman 7
    limits = {
        "Class I":  [0.71, 1.80, 4.50],  # Small Machines
        "Class II": [1.12, 2.80, 7.10],  # Medium Machines (FT Moutong & Luwuk masuk sini)
        "Class III":[1.80, 4.50, 11.20], # Large Rigid
        "Class IV": [2.80, 7.10, 18.00]  # Large Soft
    }
    
    lim = limits.get(machine_class, limits["Class II"])
    
    # Logika Penentuan Zona
    if velocity_rms <= lim[0]:
        return "GOOD", "success", "Zona A (Hijau): Operasi Normal. Lanjutkan pemantauan rutin."
    
    elif velocity_rms <= lim[1]:
        return "SATISFACTORY", "warning", "Zona B (Kuning): Operasi jangka panjang diperbolehkan. Cek parameter lain."
    
    elif velocity_rms <= lim[2]:
        return "UNSATISFACTORY", "orange", "Zona C (Oranye): Operasi terbatas. Jadwalkan perbaikan (Alignment/Bearing)."
        # Warna orange di streamlit diganti string hex atau label khusus nanti
        
    else:
        return "UNACCEPTABLE", "error", "Zona D (Merah): BAHAYA! Vibrasi merusak. Stop operasi & panggil teknisi."

def check_visual_anomaly(visual_data):
    """
    Mengecek apakah ada temuan visual dari checklist Harian/Bulanan.
    """
    issues = []
    if visual_data.get("baut_kendor"):
        issues.append("Lakukan pengencangan ulang baut & mur (Ref: TKI C-04 Poin 6).")
    if visual_data.get("kebocoran"):
        issues.append("Investigasi sumber kebocoran (Seal/Pipa) (Ref: TKI C-05 Poin 2).")
    if visual_data.get("suara_abnormal"):
        issues.append("Cek fisik bearing atau kavitasi (Ref: TKI C-05 Poin 9).")
        
    return issues
