import time
import threading
import logging
import os
import csv
import gc
from datetime import datetime
# Import der zentralen Instanzen
from data_manager import DataManager
from config import PATHS, REGEX_CLIMATE

def read_hardware_sensors():
    """
    PLATZHALTER FÜR HARDWARE-ABFRAGE (I2C oder Arduino).
    Hier implementierst du später den Aufruf für deinen Sensor (z.B. BME280 via I2C).
    Aktuell liefert die Funktion Mock-Daten für den Systemtest.
    """
    # Beispielhafte Rückgabewerte (Hier käme deine smbus2 oder serial Logik rein)
    temp = 24.5 
    hum = 45.2
    return temp, hum

def sensor_bridge_loop():
    """
    Hauptschleife der Sensor-Bridge.
    Läuft in einem eigenen Thread und pollt die Sensordaten alle 2 Sekunden.
    """
    dm = DataManager()
    logging.info("SENSOR-BRIDGE: Hardware-Polling gestartet (Intervall: 2s).")
    
    # Vorbereitung des Log-Pfads auf der NVMe SSD zur SD-Karten-Schonung.[2, 3]
    log_dir = PATHS["climate"]
    os.makedirs(log_dir, exist_ok=True)

    try:
        while True:
            # 1. Daten von der Hardware lesen
            temp, hum = read_hardware_sensors()
            
            # 2. DataManager (Singleton) aktualisieren
            # Durch den Thread-Lock im DataManager ist dieser Zugriff sicher.
            dm.update_sensors(temp, hum)
            
            # 3. Environment Logging (AP 2): Speichern in CSV
            # Naming Scheme: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID_EXT
            datestamp = datetime.now().strftime("%Y%m%d")
            log_filename = f"LOG-{datestamp}-{datestamp}_Umwelt_Labor_01.csv"
            log_path = os.path.join(log_dir, log_filename)
            
            # Wir hängen die Daten an die CSV an (Append Mode)
            with open(log_path, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().isoformat(), temp, hum])

            # 4. Memory-Hygiene für 24/7 Betrieb.
            # Da wir kontinuierlich schreiben, triggern wir gelegentlich den GC,
            # um den Unified Memory des Jetsons sauber zu halten.
            if int(time.time()) % 60 == 0: # Alle 60 Sekunden
                gc.collect()

            # 5. Intervall einhalten
            time.sleep(2)
            
    except Exception as e:
        logging.error(f"SENSOR-BRIDGE CRASH: {e}")

def start_sensor_bridge():
    """Startet die Bridge in einem Daemon-Thread."""
    bridge_thread = threading.Thread(target=sensor_bridge_loop, daemon=True)
    bridge_thread.start()