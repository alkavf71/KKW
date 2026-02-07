from enum import Enum

class ISOZone(Enum):
    """
    ISO 10816-3 Vibration Severity Zones
    Deskripsi Standar Internasional
    """
    A = "ZONE A: New machine condition"
    B = "ZONE B: Unlimited long-term operation allowable"
    C = "ZONE C: Short-term operation allowable"
    D = "ZONE D: Vibration causes damage"

class Limits:
    """
    Database Limit Standar (Bisa di-override oleh database aset)
    """
    # Electrical Limits (NEMA/ANSI)
    VOLT_UNBALANCE_LIMIT = 3.0
    CURR_UNBALANCE_LIMIT = 10.0
    
    # Mechanical Limits Default (ISO 10816 Rigid)
    VIB_WARN_DEFAULT = 2.80  # Batas Zone B ke C
    VIB_TRIP_DEFAULT = 7.10  # Batas Zone C ke D
    
    # Temperature Limits
    TEMP_BEARING_STD = 85.0
