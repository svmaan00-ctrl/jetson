import os

# Root-Verzeichnis berechnen
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Verzeichnisstruktur (Ergänzt um 'INGEST' für den Watchdog)
DIRS = {
    "INGEST": os.path.join(BASE_DIR, "data/x200_rohdaten_eingang/"),
    "RAW_DATA": os.path.join(BASE_DIR, "data/x200_rohdaten_eingang/"),
    "SPECTRA": os.path.join(BASE_DIR, "data/archivierte_spektren/"),
    "SNAPSHOTS": os.path.join(BASE_DIR, "data/archivierte_mikroskopbilder/"),
    "LOGS": os.path.join(BASE_DIR, "data/logs/"),
    "CLIMATE": os.path.join(BASE_DIR, "data/sensordaten/")
}

# Sicherstellen, dass alle Ordner existieren
for path in DIRS.values():
    os.makedirs(path, exist_ok=True)

# Hardware Config für Dino-Lite (USB)
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

# GStreamer Pipeline für Dino-Lite AM7815MZT
# Spezialisierte Pipeline für Dino-Lite AM7815MZT
GST_PIPELINE = (
    "v4l2src device=/dev/video1 ! "
    "image/jpeg, width=1280, height=720, framerate=30/1 ! "
    "jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true"
)