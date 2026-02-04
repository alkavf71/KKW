# iso_logic.py

def get_iso_status(velocity_rms, machine_class="Class II"):
    """
    Menentukan Zona Vibrasi berdasarkan ISO 10816-1 (Referensi TKI C-04 2025).
    """
    # Limit TKI C-04 (2025) Halaman 7 untuk Class II (Medium Machines)
    # Zone A / B / C / D
    limits = [1.12, 2.80, 7.10] 
    
    if velocity_rms <= limits[0]:
        return "GOOD", "success"
    elif velocity_rms <= limits[1]:
        return "SATISFACTORY", "warning"
    elif velocity_rms <= limits[2]:
        return "UNSATISFACTORY", "orange"
    else:
        return "UNACCEPTABLE", "error"

def analyze_root_cause(high_vib_points):
    """
    Menganalisa penyebab kerusakan berdasarkan TITIK vibrasi tertinggi.
    Referensi: TKI C-017 (2018) Tabel 1 - Tabel Pemeriksaan Pompa.
    """
    diagnoses = []
    
    for point, value in high_vib_points.items():
        # Logika Diagnosa TKI C-017 Tabel 1
        if "Motor NDE V" in point: # Motor Outboard Vertical
            diagnoses.append(f"Titik {point}: Indikasi **Paralel Misalignment**.")
        elif "Motor NDE H" in point: # Motor Outboard Horizontal
            diagnoses.append(f"Titik {point}: Indikasi **Bearing Looseness**.")
        elif "Motor DE V" in point: # Motor Inboard Vertical
            diagnoses.append(f"Titik {point}: Indikasi **Misalignment**.")
        elif "Motor DE H" in point: # Motor Inboard Horizontal
            diagnoses.append(f"Titik {point}: Indikasi **Bearing Looseness**.")
        elif "Motor DE A" in point: # Motor Inboard Axial
            diagnoses.append(f"Titik {point}: Indikasi **Misalignment**.")
            
        elif "Pump DE V" in point: # Pump Inboard Vertical (Sisi dekat kopling)
            diagnoses.append(f"Titik {point}: Indikasi **Bearing Looseness**.")
        elif "Pump DE H" in point: # Pump Inboard Horizontal
            diagnoses.append(f"Titik {point}: Indikasi **Kavitasi** atau Kondisi Aman (Cek Flow).")
        elif "Pump DE A" in point: # Pump Inboard Axial
            diagnoses.append(f"Titik {point}: Indikasi **Paralel Misalignment**.")
            
        elif "Pump NDE V" in point: # Pump Outboard Vertical
            diagnoses.append(f"Titik {point}: Indikasi **Unbalance** dan **Looseness**.")
        elif "Pump NDE H" in point: # Pump Outboard Horizontal
            diagnoses.append(f"Titik {point}: Indikasi **Bearing Looseness**.")
            
    if not diagnoses:
        diagnoses.append("Pola vibrasi umum. Lakukan analisa spektrum lanjutan.")
        
    return diagnoses
