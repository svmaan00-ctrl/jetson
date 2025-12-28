import os
import pandas as pd
import matplotlib
# Wir erzwingen das Agg-Backend, um keine GUI-Ressourcen auf dem Jetson zu verschwenden
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import gc
import logging

class SpectrumProcessor:
    """
    Spezialisierter Dienst zum Parsen und Visualisieren von Stellarnet-Spektren.
    Unterstützt.abs (Absorbance),.trm/.trans (Transmission) und.ssm/.scope (Scope).[1]
    """

    @staticmethod
    def parse_file(filepath):
        """
        Liest die ASCII-Daten der Stellarnet-Datei ein.
        Diese Dateien sind in der Regel Text-basiert und enthalten Wavelength vs. Intensity.[2, 3]
        """
        try:
            # Wir überspringen potenzielle Header-Zeilen (typisch 2-4 Zeilen bei SpectraWiz)
            # und nutzen flexible Delimiter (Tab oder Leerzeichen) [2]
            data = pd.read_csv(filepath, sep=r'\s+', skiprows=2, names=['wavelength', 'value'], decimal='.')
            
            # Validierung: Haben wir gültige numerische Daten erhalten?
            if data.empty or data['wavelength'].isnull().all():
                raise ValueError("Datei enthält keine gültigen Spektraldaten.")
                
            return data
        except Exception as e:
            logging.error(f"PARSER-FEHLER bei {os.path.basename(filepath)}: {e}")
            return None

    @staticmethod
    def plot_to_base64(df, title="Spektralanalyse"):
        """
        Erzeugt einen Plot und gibt ihn als Base64-String für das Flask-Frontend zurück.
        Implementiert strikte Memory-Hygiene für den 24/7-Betrieb.[4, 5]
        """
        if df is None: return ""

        try:
            # Erstellung der Figure ohne GUI-Fenster
            plt.figure(figsize=(8, 4))
            plt.plot(df['wavelength'], df['value'], color='cyan', linewidth=1.5)
            plt.title(title, color='white')
            plt.xlabel("Wellenlänge (nm)", color='gray')
            plt.ylabel("Intensität", color='gray')
            plt.grid(True, linestyle='--', alpha=0.3)
            
            # Styling für das dunkle Dashboard
            plt.gcf().set_facecolor('#1a1a1a')
            plt.gca().set_facecolor('#1a1a1a')
            plt.tick_params(colors='gray')

            # Plot in einen Buffer speichern, statt auf die SSD (schont die NVMe)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', facecolor='#1a1a1a')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            
            return img_base64

        finally:
            # KRITISCH: Memory-Hygiene für den Jetson Orin Nano
            # Wir schließen alle Plots und triggern den Garbage Collector manuell.[5, 6]
            plt.close('all')
            gc.collect()