# modules/electrical_diagnostics.py
from typing import List, Tuple
import numpy as np

def calculate_unbalance(values: List[float]) -> float:
    """Rumus NEMA: (Max Deviation from Avg / Avg) * 100"""
    avg = np.mean(values)
    if avg == 0: return 0.0
    max_dev = max(abs(v - avg) for v in values)
    return (max_dev / avg) * 100

def analyze_electrical_health(
    v_in: List[float],    # [R, S, T] Voltage
    i_in: List[float],    # [R, S, T] Current
    i_g: float,           # Ground Current
    rated_v: float,       # Rated Voltage (e.g. 380V)
    flc: float            # Full Load Current (Ampere di Nameplate)
) -> Tuple[List[str], float, float]:
    
    diagnosa = []
    
    # 1. Hitung Statistik Dasar
    avg_v = np.mean(v_in)
    avg_i = np.mean(i_in)
    max_i = max(i_in)
    
    # 2. Hitung Unbalance (NEMA MG-1)
    v_unbal = calculate_unbalance(v_in)
    i_unbal = calculate_unbalance(i_in)
    
    # --- A. ANALISA TEGANGAN (VOLTAGE) ---
    # ANSI 27: Undervoltage (< 90%)
    if avg_v < (rated_v * 0.90):
        diagnosa.append(f"⚡ ANSI 27 - UNDERVOLTAGE ({avg_v:.1f}V): Supply drop >10%. REKOMENDASI: Cek Trafo & Kabel Supply.")
        
    # ANSI 59: Overvoltage (> 110%)
    elif avg_v > (rated_v * 1.10):
        diagnosa.append(f"⚡ ANSI 59 - OVERVOLTAGE ({avg_v:.1f}V): Supply surge >10%. REKOMENDASI: Cek AVR Genset/Trafo.")

    # ANSI 47: Voltage Unbalance (> 3% NEMA)
    if v_unbal > 3.0:
        diagnosa.append(f"⚡ ANSI 47 - PHASE BALANCE ({v_unbal:.1f}%): Ketimpangan Tegangan Tinggi. REKOMENDASI: Cek Sekering Putus / Koneksi Trafo.")

    # --- B. ANALISA ARUS (CURRENT) ---
    # ANSI 37: Undercurrent / Dry Run (< 40% Load)
    if avg_i < (flc * 0.40) and avg_i > 1.0: # >1.0 memastikan motor tidak mati
        diagnosa.append(f"💧 ANSI 37 - DRY RUN / LOW LOAD ({avg_i:.1f}A): Ampere terlalu kecil. REKOMENDASI: Cek Tangki Kosong / Kopling Putus.")

    # ANSI 51: Overload (> 110% FLC)
    if max_i > (flc * 1.10):
        diagnosa.append(f"🔥 ANSI 51 - OVERLOAD ({max_i:.1f}A): Ampere > 110% Nameplate. REKOMENDASI: Cek Valve Discharge, Bearing Macet, atau Winding.")

    # ANSI 46: Current Unbalance (> 10%)
    if i_unbal > 10.0:
        diagnosa.append(f"⚖️ ANSI 46 - CURRENT UNBALANCE ({i_unbal:.1f}%): Ketimpangan Ampere > 10%. REKOMENDASI: Cek Koneksi Kabel (Hotspot) & Tahanan Gulungan.")

    # --- C. ANALISA GROUND ---
    # ANSI 50G: Ground Fault
    if i_g > 0.5:
        diagnosa.append(f"⚠️ ANSI 50G - GROUND FAULT ({i_g}A): Bocor arus ke tanah. REKOMENDASI: Stop & Megger Kabel/Motor.")

    return diagnosa, v_unbal, i_unbal
