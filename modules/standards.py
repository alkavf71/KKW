class ISOZone(Enum):
    """
    ISO 10816-3 Vibration Severity Zones
    Deskripsi lengkap sesuai standar untuk mempermudah operator.
    """
    A = "ZONE A: New machine condition (Kondisi Prima/Baru)"
    B = "ZONE B: Unlimited long-term operation allowable (Operasi Normal Jangka Panjang)"
    C = "ZONE C: Short-term operation allowable (Peringatan: Operasi Terbatas)"
    D = "ZONE D: Vibration causes damage (BAHAYA: Kerusakan Fisik Terjadi)"
