import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import DIRS
from data_manager import DataManager

class IngestHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            dm = DataManager()
            dm.set_led("spec", "green")
            # Nach 2 Sekunden zurücksetzen
            time.sleep(2) 
            dm.set_led("spec", "red")

def start_watchdog():
    event_handler = IngestHandler()
    observer = Observer()
    # Greifen Sie gezielt auf den 'INGEST'-Pfad im Dictionary zu
    observer.schedule(event_handler, path=DIRS['INGEST'], recursive=False) 
    observer.start()