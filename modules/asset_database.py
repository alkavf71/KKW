from dataclasses import dataclass

@dataclass
class AssetSpecs:
    # 1. Wajib diisi (Non-default)
    tag: str
    name: str
    area: str
    volt_rated: float
    fla_rated: float
    power_kw: float
    rpm: int
    
    # 2. Opsional (Default)
    phase: int = 3
    mounting: str = "Rigid"
    max_temp_bearing: float = 85.0
    vib_limit_warning: float = 2.80

# DATABASE ASET
ASSET_DB = {
    "P-02": AssetSpecs("P-02", "Pompa Transfer Pertalite", "FT Moutong", 380.0, 35.5, 18.5, 2900, vib_limit_warning=2.80),
    "733-P-103": AssetSpecs("733-P-103", "Pompa Booster Bio Solar", "FT Luwuk", 400.0, 54.0, 30.0, 2900, vib_limit_warning=4.50),
    "706-P-203": AssetSpecs("706-P-203", "Pompa Transfer LPG", "IT Makassar", 380.0, 28.5, 15.0, 2955, max_temp_bearing=90.0)
}

def get_asset_list(): return list(ASSET_DB.keys())
def get_asset_details(tag): return ASSET_DB.get(tag)
