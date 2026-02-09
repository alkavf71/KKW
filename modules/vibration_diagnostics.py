import pandas as pd

# --- STANDAR REFERENSI ---
# ISO 20816-3: Mechanical vibration - Measurement and evaluation (Group 2 Machines)
# API 610: Centrifugal Pumps (Vibration Limits)

class VibrationAnalyzer:
    def __init__(self, limit_warn=4.5, limit_trip=7.1, is_new_machine=False):
        """
        Inisialisasi Analyzer dengan Limit Standar Perusahaan.
        Default: ISO 20816 Class II (Medium Machine).
        """
        self.limit_warn = limit_warn
        self.limit_trip = limit_trip
        
        # Penentuan Batas Zone A (New Machine)
        # Sesuai API 610/ISO 20816, kondisi 'New' biasanya 50-60% dari batas Warning
        # Atau bisa diset manual jika ada data commissioning (misal 2.3 mm/s)
        self.limit_zone_a = 2.30 if limit_warn >= 4.0 else (limit_warn * 0.6)

    def determine_zone(self, value):
        """
        Menentukan Zone (A/B/C/D) sesuai ISO 20816
        """
        if value < self.limit_zone_a:
            return "ZONE A: New machine condition"
        elif value < self.limit_warn:
            return "ZONE B: Unlimited long-term operation"
        elif value < self.limit_trip:
            return "ZONE C: Short-term operation allowable"
        else:
            return "ZONE D: Vibration causes damage"

    def calculate_average(self, val1, val2):
        """Hitung Rata-rata 2 titik (DE & NDE) per sumbu"""
        return (val1 + val2) / 2

    def diagnose_root_cause(self, df_report):
        """
        Logika Diagnosa Cerdas (Heuristic) berdasarkan Pola Vibrasi.
        Input: DataFrame hasil olahan.
        Output: List kemungkinan penyebab.
        """
        causes = []
        max_val = df_report['Avr'].max()
        
        # Jika vibrasi masih aman (Zone A/B), tidak perlu diagnosa
        if max_val < self.limit_warn:
            return []

        # Ambil nilai rata-rata per sumbu untuk logika
        # Filter berdasarkan Unit (Driver/Driven) dan Axis
        try:
            m_h = df_report[(df_report['Unit']=='Driver') & (df_report['Axis']=='H')]['Avr'].values[0]
            m_v = df_report[(df_report['Unit']=='Driver') & (df_report['Axis']=='V')]['Avr'].values[0]
            m_a = df_report[(df_report['Unit']=='Driver') & (df_report['Axis']=='A')]['Avr'].values[0]
            
            p_h = df_report[(df_report['Unit']=='Driven') & (df_report['Axis']=='H')]['Avr'].values[0]
            p_v = df_report[(df_report['Unit']=='Driven') & (df_report['Axis']=='V')]['Avr'].values[0]
            p_a = df_report[(df_report['Unit']=='Driven') & (df_report['Axis']=='A')]['Avr'].values[0]
        except:
            return ["Data tidak lengkap untuk diagnosa otomatis"]

        # --- LOGIC MATRIX (ISO 13373-1) ---
        
        # 1. MISALIGNMENT (Dominan Axial & 2X RPM)
        # Jika Axial > 50% dari vibrasi tertinggi radial
        max_radial = max(m_h, m_v, p_h, p_v)
        if (m_a > self.limit_warn or p_a > self.limit_warn) and (max(m_a, p_a) > 0.5 * max_radial):
            causes.append("MISALIGNMENT: Vibrasi Axial Dominan. Cek Kopling & Alignment.")

        # 2. UNBALANCE (Dominan Radial 1X RPM, biasanya Horizontal)
        # Jika Horizontal tinggi, tapi Axial rendah
        if (m_h > self.limit_warn or p_h > self.limit_warn) and (max(m_a, p_a) < self.limit_warn):
            causes.append("UNBALANCE: Vibrasi Radial (Horiz) Dominan. Cek Kotoran di Kipas/Impeller.")

        # 3. MECHANICAL LOOSENESS / SOFT FOOT (Dominan Vertical)
        # Jika Vertical jauh lebih tinggi dari Horizontal (pada mesin horizontal)
        if (m_v > 1.5 * m_h) and (m_v > self.limit_warn):
            causes.append("LOOSENESS / SOFT FOOT: Vibrasi Vertical Dominan. Cek Baut Pondasi.")
        
        # 4. BENT SHAFT (Axial tinggi dengan beda fase 180 - sulit deteksi tanpa phase, tapi indikasi mirip misalignment)
        if (m_a > self.limit_trip) and (p_a > self.limit_trip):
             causes.append("BENT SHAFT (Indikasi): Vibrasi Axial Tinggi di kedua sisi.")

        return causes

    def generate_full_report(self, inputs):
        """
        Fungsi Utama untuk generate Data Laporan.
        inputs: Dictionary berisi m_de_h, m_nde_h, dst.
        """
        # 1. Hitung Rata-rata per Sumbu (Driver)
        avr_m_h = self.calculate_average(inputs['m_de_h'], inputs['m_nde_h'])
        avr_m_v = self.calculate_average(inputs['m_de_v'], inputs['m_nde_v'])
        avr_m_a = self.calculate_average(inputs['m_de_a'], inputs['m_nde_a'])

        # 2. Hitung Rata-rata per Sumbu (Driven)
        avr_p_h = self.calculate_average(inputs['p_de_h'], inputs['p_nde_h'])
        avr_p_v = self.calculate_average(inputs['p_de_v'], inputs['p_nde_v'])
        avr_p_a = self.calculate_average(inputs['p_de_a'], inputs['p_nde_a'])

        # 3. Buat Data Table (Sesuai Format Laporan Perusahaan)
        data = [
            ["Driver", "H", inputs['m_de_h'], inputs['m_nde_h'], avr_m_h, self.limit_warn, self.determine_zone(avr_m_h)],
            ["Driver", "V", inputs['m_de_v'], inputs['m_nde_v'], avr_m_v, self.limit_warn, self.determine_zone(avr_m_v)],
            ["Driver", "A", inputs['m_de_a'], inputs['m_nde_a'], avr_m_a, self.limit_warn, self.determine_zone(avr_m_a)],
            ["Driven", "H", inputs['p_de_h'], inputs['p_nde_h'], avr_p_h, self.limit_warn, self.determine_zone(avr_p_h)],
            ["Driven", "V", inputs['p_de_v'], inputs['p_nde_v'], avr_p_v, self.limit_warn, self.determine_zone(avr_p_v)],
            ["Driven", "A", inputs['p_de_a'], inputs['p_nde_a'], avr_p_a, self.limit_warn, self.determine_zone(avr_p_a)],
        ]
        
        df = pd.DataFrame(data, columns=["Unit", "Axis", "DE", "NDE", "Avr", "Limit", "Remark"])

        # 4. Generate Diagnosa & Status Global
        causes = self.diagnose_root_cause(df)
        max_val = max(avr_m_h, avr_m_v, avr_m_a, avr_p_h, avr_p_v, avr_p_a)
        
        # Tentukan Status Global (Untuk Gauge & Header)
        status_global = "ZONE B: Unlimited"
        remark_list = df['Remark'].tolist()
        
        if any("ZONE D" in x for x in remark_list): status_global = "ZONE D: DAMAGE"
        elif any("ZONE C" in x for x in remark_list): status_global = "ZONE C: WARNING"
        elif any("ZONE A" in x for x in remark_list): status_global = "ZONE A: NEW CONDITION" # Priority if mostly good

        # Tentukan Warna Global
        color_global = "#a3e048" # Zone B
        if "ZONE D" in status_global: color_global = "#e74c3c"
        if "ZONE C" in status_global: color_global = "#f1c40f"
        if "ZONE A" in status_global: color_global = "#2ecc71"

        return {
            "dataframe": df,
            "max_value": max_val,
            "global_status": status_global,
            "global_color": color_global,
            "causes": causes
        }
