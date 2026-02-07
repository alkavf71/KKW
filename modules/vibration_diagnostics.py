from typing import List

class VibPoint:
    def __init__(self, loc, axis, val):
        self.location = loc # Konsisten
        self.axis = axis
        self.value = val    # Konsisten

def analyze_vibration_matrix(readings: List[VibPoint], limit_warn: float) -> List[str]:
    diagnosa = []
    high_vib = [r for r in readings if r.value > limit_warn]
    
    if not high_vib: return []

    def get_val(loc_search, axis_search):
        found = [r.value for r in readings if loc_search in r.location and axis_search in r.axis]
        return max(found) if found else 0.0

    # Logic Matrix
    m_de_a = get_val("Motor DE", "Axial")
    m_de_h = get_val("Motor DE", "Horizontal")
    p_de_a = get_val("Pump DE", "Axial")
    
    if (m_de_a > limit_warn and m_de_a > 0.5 * m_de_h) or (p_de_a > limit_warn):
        diagnosa.append("🔴 MISALIGNMENT (Angular): Dominan Axial di Kopling.")

    max_h = max([r.value for r in high_vib if "Horizontal" in r.axis], default=0)
    max_v = max([r.value for r in high_vib if "Vertical" in r.axis], default=0)
    max_a = max([r.value for r in high_vib if "Axial" in r.axis], default=0)

    if max_h > limit_warn and max_h > max_v and max_h > max_a:
         diagnosa.append("🟠 UNBALANCE: Dominan Horizontal. Cek Impeller/Fan.")

    if max_v > limit_warn and max_v > max_h:
        diagnosa.append("🔧 MECHANICAL LOOSENESS: Dominan Vertikal. Cek Baut.")

    m_nde_a = get_val("Motor NDE", "Axial")
    if m_nde_a > limit_warn and m_nde_a > m_de_a:
        diagnosa.append("⚠️ BENT SHAFT: Axial tinggi di Motor NDE.")

    vib_motor = [r.value for r in readings if "Motor" in r.location]
    vib_pump = [r.value for r in readings if "Pump" in r.location]
    if vib_motor and vib_pump:
        avg_m = sum(vib_motor)/len(vib_motor)
        avg_p = sum(vib_pump)/len(vib_pump)
        if avg_p > limit_warn and avg_p > (avg_m * 1.5):
             diagnosa.append("🌊 PIPE STRAIN / HYDRAULIC: Vibrasi Pompa dominan.")

    return list(set(diagnosa))
