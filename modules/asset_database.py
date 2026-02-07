# modules/asset_database.py
from dataclasses import dataclass

@dataclass
class AssetSpecs:
    """Struktur Data Spesifikasi Aset"""
    tag: str            # Tag Number (P-02)
    name: str           # Nama Deskriptif
    area: str           # Lokasi
    
    # --- SPEK ELEKTRIKAL (Nameplate) ---
    volt_rated: float   # Tegangan (Volt)
    fla_rated: float    # Full Load Ampere (A)
    phase: int = 3      # Default 3 Phase
    
    # --- SPEK MEKANIKAL (Nameplate) ---
    power_kw: float     # Daya Motor (kW)
    rpm: int            # Putaran (RPM)
    mounting: str = "Rigid" # Rigid / Flexible
    
    # --- BATAS LIMIT KHUSUS (Custom Thresholds) ---
    # Bisa di-override jika mesin ini spesial
    max_temp_bearing: float = 85.0 # Celcius
    vib_limit_warning: float = 2.80 # ISO Zone B/C Boundary
    vib_limit_danger: float = 7.10  # ISO Zone C/D Boundary

# --- DATABASE ASET (EDIT DISINI UNTUK NAMBAH POMPA) ---
ASSET_DB = {
    # ASET 1: Pompa Kecil
    "P-02": AssetSpecs(
        tag="P-02",
        name="Pompa Transfer Pertalite",
        area="FT Moutong",
        volt_rated=380.0,
        fla_rated=35.5,   # Ampere Nameplate
        power_kw=18.5,
        rpm=2900,         # 2 Pole
        vib_limit_warning=2.80 # Class II Rigid
    ),

    # ASET 2: Pompa Sedang
    "733-P-103": AssetSpecs(
        tag="733-P-103",
        name="Pompa Booster Bio Solar",
        area="FT Luwuk",
        volt_rated=400.0,
        fla_rated=54.0,
        power_kw=30.0,
        rpm=2900,
        vib_limit_warning=4.50 # Misal: Class I (Mesin Besar/Flexible)
    ),

    # ASET 3: Pompa LPG
    "706-P-203": AssetSpecs(
        tag="706-P-203",
        name="Pompa Transfer LPG",
        area="IT Makassar",
        volt_rated=380.0,
        fla_rated=28.5,
        power_kw=15.0,
        rpm=2955,
        max_temp_bearing=90.0 # Bearing khusus LPG mungkin tahan panas
    )
}

def get_asset_list():
    """Mengembalikan list semua Tag Number"""
    return list(ASSET_DB.keys())

def get_asset_details(tag):
    """Mengambil object data aset berdasarkan Tag"""
    return ASSET_DB.get(tag)
