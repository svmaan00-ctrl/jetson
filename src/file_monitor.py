import time
import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import DIRS
from data_manager import DataManager
from spectrum_processor import SpectrumProcessor

class IngestHandler(FileSystemEventHandler):
    def on_created(self, event):
        # 1. Filter: Nur auf Spektren-Dateien reagieren, temporäre Files ignorieren
        if not event.is_directory and event.src_path.lower().endswith(('.abs', '.trm', '.ssm')):
            dm = DataManager()
            try:
                # [cite_start]2. LED auf Grün: Signalisiert laufendes Parsing an den User [cite: 60]
                dm.set_led("spec", "green")
                
                # 3. Kurze Pause für SSD-Sync (Vermeidung von 'File not found' Fehlern)
                time.sleep(0.5)
                
                # 4. Spektrum parsen und Visualisierung generieren
                df = SpectrumProcessor.parse_file(event.src_path)
                if df is not None:
                    img_b64 = SpectrumProcessor.plot_to_base64(df, os.path.basename(event.src_path))
                    
                    # [cite_start]5. Daten via SSE an das Dashboard pushen (Auto-Update) [cite: 35]
                    dm.announce("spectrum_update", {
                        "image": img_b64,
                        "filename": os.path.basename(event.src_path)
                    })
                
                # 6. Status nach Abschluss zurücksetzen
                time.sleep(2.0)
                dm.set_led("spec", "red")
            except Exception as e:
                logging.error(f"INGEST-CRASH: {e}")
                dm.set_led("spec", "red")

def start_watchdog():
    event_handler = IngestHandler()
    observer = Observer()
    # Überwache den korrekten Pfad aus der Konfiguration [cite: 25, 61]
    observer.schedule(event_handler, path=DIRS['INGEST'], recursive=False) 
    observer.start()