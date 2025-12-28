import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
# Import der Single Source of Truth und der Pfad-Konfiguration
from data_manager import DataManager
from config import PATHS

class WinSCPHandler(FileSystemEventHandler):
    """
    Spezialisierter Event-Handler für die WinSCP-Datenübernahme.
    
    TECHNISCHER HINTERGRUND:
    WinSCP überträgt Dateien standardmäßig mit der Endung '.filepart'. 
    Ein 'on_created' Event würde auslösen, während die Datei noch geschrieben wird.
    Wir reagieren daher NUR auf 'on_moved', was ausgelöst wird, wenn WinSCP
    die Übertragung abschließt und die Datei in den Zielnamen umbenennt.[2, 3]
    """
    def __init__(self):
        # Wir holen uns die Instanz des DataManagers (Singleton)
        self.dm = DataManager()

    def on_moved(self, event):
        """
        Wird aufgerufen, wenn eine Datei im Überwachungsverzeichnis umbenannt wird.
        Das ist unser sicheres Signal: 'Transfer beendet, Datei ist bereit'.
        """
        if event.is_directory:
            return

        # Wir extrahieren den Zielpfad (wohin die Datei verschoben/umbenannt wurde)
        dest_path = event.dest_path
        filename = os.path.basename(dest_path)

        # Schritt 1: Prüfung auf Dateityp basierend auf der Extension
        # Stellarnet nutzt.abs,.trm,.ssm oder.csv für Spektren.[4]
        if filename.lower().endswith(('.abs', '.trm', '.ssm', '.csv')):
            file_type = "spectrum"
        else:
            file_type = "image"

        # Schritt 2: Strikte Validierung des Naming Schemes (AP 4)
        # Wir rufen die Methode im DataManager auf, die gegen die config.REGEX prüft.[5]
        if self.dm.validate_filename(filename, file_type=file_type):
            # Schritt 3: Pfad im Systemzustand registrieren
            # Jetzt wissen Flask und andere Threads, wo die neueste Datei liegt.
            self.dm.set_last_file(dest_path, file_type=file_type)
            logging.info(f"SMART-IMPORT: '{filename}' erfolgreich registriert.")
        else:
            # Fehlerhaft benannte Dateien werden ignoriert, um das Archiv sauber zu halten.
            logging.error(f"SCHEMA-ABWEICHUNG: '{filename}' wurde ignoriert.")

def start_file_monitor():
    """
    Initialisiert den Watchdog-Dienst in einem eigenen Thread.
    Der Pfad liegt auf der NVMe SSD, um die SD-Karte zu entlasten.
    """
    monitor_path = PATHS["dropzone"]
    
    # Sicherstellen, dass die Dropzone existiert
    if not os.path.exists(monitor_path):
        os.makedirs(monitor_path, exist_ok=True)

    event_handler = WinSCPHandler()
    observer = Observer()
    # Wir überwachen nur die Dropzone, nicht rekursiv, um CPU-Last zu sparen.
    observer.schedule(event_handler, monitor_path, recursive=False)
    observer.start()
    
    logging.info(f"WATCHDOG-SERVICE: Aktiv auf {monitor_path}")
    
    try:
        while True:
            # Polling-Intervall von 1s reicht völlig aus und schont die CPU.[6]
            time.sleep(1)
    except Exception as e:
        observer.stop()
        logging.error(f"WATCHDOG-FATAL: Dienst angehalten wegen: {e}")
    
    observer.join()