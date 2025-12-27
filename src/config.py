import os

# --- PFAD-LOGIK ---
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# --- FLASK (Frontend) ---
TEMPLATE_FOLDER = SRC_DIR
STATIC_FOLDER = os.path.join(SRC_DIR, 'static')

# --- DATEN-ORDNER ---
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Unterordner definieren
UPLOAD_FOLDER_RAW = os.path.join(DATA_DIR, 'x200_rohdaten_eingang')
ARCHIVE_FOLDER = os.path.join(DATA_DIR, 'spektren')        # ZIEL für UI/Archiv
SNAPSHOT_FOLDER = os.path.join(DATA_DIR, 'mikroskopbilder') # ZIEL für Kamera
LOG_FOLDER = os.path.join(DATA_DIR, 'logs')

# --- SYSTEM ---
ALLOWED_EXTENSIONS = {'csv', 'txt'}
KAMERA_ID = 0
ARDUINO_PORT = '/dev/ttyACM0'