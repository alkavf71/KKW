from dataclasses import dataclass

@dataclass
class AssetSpecs:
    """Struktur Data Spesifikasi Aset"""
    # --- 1. WAJIB DIISI (Non-Default Arguments) ---
    # Taruh semua yang tidak ada tanda '=' di bagian atas
    tag: str            
    name: str           
    area: str           
    volt_rated: float   
    fla_rated: float    
    power_kw: float     
    rpm: int            

    # --- 2. OPSIONAL (Default Arguments) ---
    # Taruh semua yang ada tanda '=' di bagian bawah
    phase: int = 3              # Pindahkan ke bawah sini
    mounting: str = "Rigid"     
    max_temp_bearing: float = 85.0 
    vib_limit_warning: float = 2.80 
    vib_limit_danger: float = 7.10  

# --- DATABASE ASET ---
# (Isinya tetap sama, karena kita pakai keyword arguments saat inisialisasi)
ASSET_DB = {
    "P-02": AssetSpecs(
        tag="P-02",
        name="Pompa Transfer Pertalite",
        area="FT Moutong",
        volt_rated=380.0,
        fla_rated=35.5,
        power_kw=18.5,
        rpm=2900,
        vib_limit_warning=2.80
    ),

    "733-P-103": AssetSpecs(
        tag="733-P-103",
        name="Pompa Booster Bio Solar",
        area="FT Luwuk",
        volt_rated=400.0,
        fla_rated=54.0,
        power_kw=30.0,
        rpm=2900,
        vib_limit_warning=4.50
    ),

    "706-P-203": AssetSpecs(
        tag="706-P-203",
        name="Pompa Transfer LPG",
        area="IT Makassar",
        volt_rated=380.0,
        fla_rated=28.5,
        power_kw=15.0,
        rpm=2955,
        max_temp_bearing=90.0
    )
}

def get_asset_list():
    """Mengembalikan list semua Tag Number"""
    return list(ASSET_DB.keys())

def get_asset_details(tag):
    """Mengambil object data aset berdasarkan Tag"""
    return ASSET_DB.get(tag)
