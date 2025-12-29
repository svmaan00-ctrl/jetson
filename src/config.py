import os

# --- Absolute Pfade auf der NVMe SSD ---
BASE_DIR = "/home/jetson/inspection_project"
DATA_DIR = os.path.join(BASE_DIR, "data")

DIRS = {
    'SNAPSHOTS': os.path.join(DATA_DIR, 'mikroskopbilder'),
    'SPECTRA': os.path.join(DATA_DIR, 'spektren'),
    'CLIMATE': os.path.join(DATA_DIR, 'klimadaten'),
    'INGEST': os.path.join(DATA_DIR, 'x200_rohdaten_eingang'),
    'LOGS': os.path.join(DATA_DIR, 'logs')
}

# Verzeichnisse automatisch anlegen
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# --- Hardware ---
CAMERA_ID = 0          # Dino-Lite USB
ARDUINO_PORT = '/dev/ttyACM0'
BAUDRATE = 115200

# --- Metrologie ---
# Pixel pro 1mm (Muss kalibriert werden, 250 ist ein Standard-Startwert)
CAL_FACTOR = 250.0