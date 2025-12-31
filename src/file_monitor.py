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
        # Nur auf Dateien mit passender Endung reagieren 
        if not event.is_directory and event.src_path.lower().endswith(('.abs', '.trm', '.ssm')):
            dm = DataManager()
            try:
                # 1. LED auf Grün setzen (Aktivität signalisieren) 
                dm.set_led("spec", "green")
                
                # 2. Kurze Pause, falls die Datei noch geschrieben wird (SSD I/O)
                time.sleep(0.5) 
                
                # 3. Spektrum verarbeiten
                df = SpectrumProcessor.parse_file(event.src_path)
                if df is not None:
                    # Plot generieren
                    img_data = SpectrumProcessor.plot_to_base64(df, title=os.path.basename(event.src_path))
                    
                    # Daten via SSE an Dashboard senden [cite: 35]
                    dm.announce("spectrum_update", {
                        "image": img_data,
                        "filename": os.path.basename(event.src_path)
                    })
                else:
                    logging.error(f"Dateiformat ungültig: {event.src_path}")

            except Exception as e:
                logging.error(f"Fehler im Watchdog-Prozess: {e}")
            
            finally:
                # 4. KRITISCH: LED nach 2 Sek. IMMER zurücksetzen 
                time.sleep(2) 
                dm.set_led("spec", "red")

def start_watchdog():
    event_handler = IngestHandler()
    observer = Observer()
    # Überwache den korrekten Pfad aus der Konfiguration [cite: 25, 61]
    observer.schedule(event_handler, path=DIRS['INGEST'], recursive=False) 
    observer.start()