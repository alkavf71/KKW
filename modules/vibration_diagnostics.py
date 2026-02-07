from typing import List, Dict

# --- STRUKTUR DATA (Perbaikan: ubah self.val jadi self.value) ---
class VibPoint:
    def __init__(self, loc, axis, val):
        self.location = loc # Samakan dengan logika pemanggilan (location)
        self.axis = axis
        self.value = val    # <--- DULU self.val, SEKARANG self.value

def analyze_vibration_matrix(readings: List[object], limit_warn: float) -> List[str]:
    """
    Menganalisa pola H/V/A pada DE/NDE sesuai Database ISO 18436-2.
    """
    diagnosa = []
    
    # 1. FILTER DATA (Sekarang r.value sudah dikenali)
    high_vib = [r for r in readings if r.value > limit_warn]
    
    if not high_vib:
        return [] # Normal

    # Helper: Fungsi untuk mengambil nilai spesifik
    def get_val(loc_search, axis_search):
        # Cari nilai vib pada lokasi dan sumbu tertentu
        # Perhatikan kita pakai 'r.location' dan 'r.axis'
        found = [r.value for r in readings if loc_search in r.location and axis_search in r.axis]
        return max(found) if found else 0.0

    # --- KASUS 1 & 2: MISALIGNMENT (Fokus di KOPLING / DE) ---
    m_de_a = get_val("Motor DE", "Axial")
    p_de_a = get_val("Pump DE", "Axial")
    m_de_h = get_val("Motor DE", "Horizontal")
    
    # Angular Misalignment (Axial Dominan di Kopling)
    if (m_de_a > limit_warn and m_de_a > 0.5 * m_de_h) or (p_de_a > limit_warn):
        diagnosa.append("🔴 MISALIGNMENT (Angular) [Ref: ISO 18436]: Vibrasi Axial dominan di area Kopling (DE). REKOMENDASI: Cek Alignment & Shims.")

    # --- KASUS 3: UNBALANCE (Fokus Horizontal Dominan) ---
    max_h = max([r.value for r in high_vib if "Horizontal" in r.axis], default=0)
    max_v = max([r.value for r in high_vib if "Vertical" in r.axis], default=0)
    max_a = max([r.value for r in high_vib if "Axial" in r.axis], default=0)

    if max_h > limit_warn and max_h > max_v and max_h > max_a:
         diagnosa.append("🟠 UNBALANCE [Ref: ISO 10816]: Vibrasi Horizontal Dominan. REKOMENDASI: Cek kotoran di Impeller/Fan & Balancing Rotor.")

    # --- KASUS 4: LOOSENESS (Fokus Vertical Dominan) ---
    if max_v > limit_warn and max_v > max_h:
        diagnosa.append("🔧 MECHANICAL LOOSENESS [Ref: API 686]: Vibrasi Vertikal Dominan. REKOMENDASI: Kencangkan Baut Pondasi & Cek Soft Foot.")

    # --- KASUS 5: BENT SHAFT (Fokus Motor NDE Axial) ---
    m_nde_a = get_val("Motor NDE", "Axial")
    if m_nde_a > limit_warn and m_nde_a > m_de_a:
        diagnosa.append("⚠️ BENT SHAFT [Ref: ISO 18436]: Axial tinggi di Motor NDE. REKOMENDASI: Cek Run-out poros motor.")

    # --- KASUS 6: OVERHUNG LOAD / FAN (Fokus Motor NDE Radial) ---
    m_nde_h = get_val("Motor NDE", "Horizontal")
    m_nde_v = get_val("Motor NDE", "Vertical")
    # Bandingkan NDE vs DE
    m_de_h_val = get_val("Motor DE", "Horizontal") 
    
    if (m_nde_h > limit_warn or m_nde_v > limit_warn) and (m_nde_h > m_de_h_val):
        diagnosa.append("💨 FAN / OVERHUNG [Ref: ISO 18436]: Vibrasi tinggi di Motor NDE. REKOMENDASI: Cek kondisi kipas pendingin motor.")

    # --- KASUS 7: HYDRAULIC / PIPE STRAIN (Pump > Motor) ---
    vib_motor = [r.value for r in readings if "Motor" in r.location]
    vib_pump = [r.value for r in readings if "Pump" in r.location]
    
    if vib_motor and vib_pump:
        avg_m = sum(vib_motor)/len(vib_motor)
        avg_p = sum(vib_pump)/len(vib_pump)
        
        if avg_p > limit_warn and avg_p > (avg_m * 1.5):
             diagnosa.append("🌊 PIPE STRAIN / HYDRAULIC [Ref: API 610]: Vibrasi Pompa dominan. REKOMENDASI: Cek support pipa & tegangan pada flange pompa.")

    return list(set(diagnosa))
