import os
import pandas as pd
import matplotlib
# 1. Agg-Backend erzwingen, um GUI-Ressourcen auf dem Jetson zu sparen
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import gc
import logging
import re

class SpectrumProcessor:
    @staticmethod
    def parse_file(filepath):
        """Liest Stellarnet ASCII-Daten ein und bereitet sie für die Analyse vor."""
        try:
            # 1. Datei mit latin-1 öffnen, um Encoding-Fehler (z.B. bei 'ü') zu vermeiden
            with open(filepath, 'r', encoding='latin-1') as f:
                lines = f.readlines()

            # 2. Dynamisches Header-Skipping: Suche nach der ersten Zeile mit zwei Zahlenwerten
            start_line = 0
            for i, line in enumerate(lines):
                if re.match(r'^\s*\d+\.?\d*\s+\d+\.?\d*', line):
                    start_line = i
                    break
            
            # 3. Daten ab Datenpunkt via Pandas einlesen (flexible Whitespace-Trennung)
            data = pd.read_csv(
                io.StringIO("".join(lines[start_line:])), 
                sep=r'\s+', 
                names=['wavelength', 'value'], 
                decimal='.'
            )
            
            # 4. Rückgabe des DataFrames bei erfolgreicher Validierung
            if data.empty:
                raise ValueError("Keine gültigen Spektraldaten extrahiert.")
            return data
            
        except Exception as e:
            logging.error(f"PARSER-FEHLER bei {os.path.basename(filepath)}: {e}")
            return None

    @staticmethod
    def plot_to_base64(df, title="Spektralanalyse"):
        """Erzeugt eine Base64-Grafik unter Berücksichtigung der NumPy 1.26.4 ABI-Beschränkungen."""
        if df is None: return ""
        try:
            # 1. Konvertierung: Series explizit in NumPy-Arrays umwandeln (Fix für Multi-dimensional indexing Error)
            x_data = df['wavelength'].to_numpy()
            y_data = df['value'].to_numpy()

            # 2. Plot-Vorbereitung: Erstellung der Figure im Dark-Dashboard Style
            plt.figure(figsize=(8, 4))
            plt.plot(x_data, y_data, color='cyan', linewidth=1.5)
            
            # 3. Styling: Hintergrund und Gitter an das Hazion-Design anpassen
            plt.gcf().set_facecolor('#1a1a1a')
            plt.gca().set_facecolor('#1a1a1a')
            plt.tick_params(colors='gray')
            plt.title(title, color='white')
            plt.grid(True, linestyle='--', alpha=0.3)
            
            # 4. Export: Speichern in BytesIO-Buffer zur Schonung der NVMe SSD
            buf = io.BytesIO()
            plt.savefig(buf, format='png', facecolor='#1a1a1a')
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
            
        finally:
            # 5. RAM-Hygiene: Explizites Schließen des Plots und Trigger des GC (Wichtig für 8GB Unified Memory)
            plt.close('all')
            gc.collect()