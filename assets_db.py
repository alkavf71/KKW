# assets_db.py

# Database statis spesifikasi pompa.
# Disimpan di file Python karena jarang berubah (Static Data).

ASSETS = {
    "P-02 (FT Moutong)": {
        "tag_no": "0459599",
        "name": "Pompa Produk Pertalite",
        "location": "FT Moutong",
        "power_kw": 18.5,        # Masuk Class II (15-300 kW)
        "rpm_design": 2900,
        "mounting": "Rigid",     # Asumsi berdasarkan foto laporan
        "class_iso": "Class II", # Referensi TKI C-04 Lampiran 2
        "coi_expiry": "2026-10-20"
    },
    "733-P-103/00 (FT Luwuk)": {
        "tag_no": "1041535A",
        "name": "Pompa Produk Bio Solar",
        "location": "FT Luwuk",
        "power_kw": 30.0,        # Masuk Class II (15-300 kW)
        "rpm_design": 2900,
        "mounting": "Rigid",
        "class_iso": "Class II",
        "coi_expiry": "2027-06-07"
    },
    "706-P-203/00 (IT Makassar)": {
        "tag_no": "Unknown",
        "name": "Pompa LPG",
        "location": "IT Makassar",
        "power_kw": 45.0,        # Estimasi (Perlu update data riil)
        "rpm_design": 2950,
        "mounting": "Rigid",
        "class_iso": "Class II",
        "coi_expiry": "2027-01-19"
    }
}
