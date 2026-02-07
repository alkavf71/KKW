from enum import Enum

class ISOZone(Enum):
    A = "ZONE A: New machine condition (Kondisi Prima)"
    B = "ZONE B: Unlimited long-term operation allowable (Operasi Normal)"
    C = "ZONE C: Short-term operation allowable (WARNING: Operasi Terbatas)"
    D = "ZONE D: Vibration causes damage (DANGER: Kerusakan Fisik)"

class Limits:
    VOLT_UNBALANCE_LIMIT = 3.0
    CURR_UNBALANCE_LIMIT = 10.0
    VIB_WARN_DEFAULT = 2.80
    VIB_TRIP_DEFAULT = 7.10
    TEMP_BEARING_STD = 85.0
