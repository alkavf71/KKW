from typing import List, Tuple
import numpy as np
from .standards import Limits

def analyze_electrical_health(v_in, i_in, i_g, rated_v, flc):
    diagnosa = []
    avg_v = np.mean(v_in)
    avg_i = np.mean(i_in)
    
    def calc_unb(vals):
        avg = np.mean(vals)
        return (max(abs(v - avg) for v in vals) / avg * 100) if avg > 0 else 0.0

    v_unbal = calc_unb(v_in)
    i_unbal = calc_unb(i_in)

    if avg_v < (rated_v * 0.90): diagnosa.append(f"⚡ ANSI 27 - UNDERVOLTAGE ({avg_v:.0f}V)")
    if avg_v > (rated_v * 1.10): diagnosa.append(f"⚡ ANSI 59 - OVERVOLTAGE ({avg_v:.0f}V)")
    if v_unbal > Limits.VOLT_UNBALANCE_LIMIT: diagnosa.append(f"⚡ ANSI 47 - VOLT UNBALANCE ({v_unbal:.1f}%)")
    
    if avg_i < (flc * 0.40) and avg_i > 1.0: diagnosa.append(f"💧 ANSI 37 - DRY RUN ({avg_i:.1f}A)")
    if max(i_in) > (flc * 1.10): diagnosa.append(f"🔥 ANSI 51 - OVERLOAD ({max(i_in):.1f}A)")
    if i_unbal > Limits.CURR_UNBALANCE_LIMIT: diagnosa.append(f"⚖️ ANSI 46 - CURR UNBALANCE ({i_unbal:.1f}%)")
    if i_g > 0.5: diagnosa.append(f"⚠️ ANSI 50G - GROUND FAULT ({i_g}A)")

    return diagnosa, v_unbal, i_unbal
