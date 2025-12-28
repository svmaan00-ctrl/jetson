import os

# --- System Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

DIRS = {
    'SNAPSHOTS': os.path.join(DATA_DIR, 'mikroskopbilder'),
    'SPECTRA': os.path.join(DATA_DIR, 'spektren'),
    'CLIMATE': os.path.join(DATA_DIR, 'klimadaten'),
    'INGEST': os.path.join(DATA_DIR, 'x200_rohdaten_eingang'),
    'LOGS': os.path.join(DATA_DIR, 'logs')
}

# Ensure directories exist
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# --- Hardware Config ---
CAMERA_ID = 0
ARDUINO_PORT = '/dev/ttyACM0'
BAUDRATE = 115200

# --- Naming Scheme Regex ---
# Erlaubt: Alphanumerisch, Bindestriche, Unterstriche. Keine Leerzeichen.
VALID_NAME_REGEX = r'^[a-zA-Z0-9_-]+$'

# --- Calibration Defaults (px/mm) ---
# Muss initial kalibriert werden
CALIBRATION = {
    "Micro_4x": 125.0,
    "Micro_10x": 312.5,
    "Micro_40x": 1250.0,
    "Macro": 10.0
}