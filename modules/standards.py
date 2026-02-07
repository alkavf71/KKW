from enum import Enum  # <--- INI YANG KURANG SEBELUMNYA

class ISOZone(Enum):
    """
    ISO 10816-3 Vibration Severity Zones
    Deskripsi lengkap sesuai standar untuk mempermudah operator.
    """
    A = "ZONE A: New machine condition (Kondisi Prima/Baru)"
    B = "ZONE B: Unlimited long-term operation allowable (Operasi Normal Jangka Panjang)"
    C = "ZONE C: Short-term operation allowable (Peringatan: Operasi Terbatas)"
    D = "ZONE D: Vibration causes damage (BAHAYA: Kerusakan Fisik Terjadi)"

class Limits:
    """
    Kumpulan Batas Aman (Thresholds) standar.
    Bisa di-override oleh database aset jika perlu.
    """
    # --- ELECTRICAL ---
    VOLTAGE_UNBALANCE_TRIP = 3.0  # NEMA MG-1
    CURRENT_UNBALANCE_ALARM = 5.0
    CURRENT_UNBALANCE_TRIP = 10.0
    
    # --- MECHANICAL (ISO 10816-3 Group 2 Rigid - Default) ---
    VIB_WARN = 2.80  # Batas Zone B ke C
    VIB_TRIP = 7.10  # Batas Zone C ke D
    ISO_CLASS_II = [1.12, 2.80, 7.10] 
    
    # --- COMMISSIONING (API 686) ---
    MAX_SOFT_FOOT = 0.05       # mm
    ALIGNMENT_TOLERANCE = 0.05 # mm
