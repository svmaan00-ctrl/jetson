import os
import logging

# --- PFAD-KONFIGURATION (Fokus: NVMe SSD Härtung) ---
# Alle Daten liegen auf /data (NVMe), um die SD-Karte zu schonen.[1, 2]
DATA_ROOT = "/data"

PATHS = {
    "dropzone": os.path.join(DATA_ROOT, "x200_rohdaten_eingang"),
    "images": os.path.join(DATA_ROOT, "mikroskopbilder"),
    "spectra": os.path.join(DATA_ROOT, "spektren"),
    "climate": os.path.join(DATA_ROOT, "klimadaten"),
    "logs": os.path.join(DATA_ROOT, "logs")
}

# --- BACKEND & SECURITY ---
# Flask-Logging auf ERROR begrenzen (Silent Mode) zur SSD-Schonung.[3]
LOG_LEVEL = logging.ERROR
# Secret Key für Session-Sicherheit.
SECRET_KEY = os.environ.get("LAB_STATION_SECRET_KEY", "jetson_orin_super_8gb_2025")

# --- NAMING SCHEMES (Strikte Validierung via Regex) [4, 5] ---
# Jede Datei muss exakt diesen Mustern entsprechen.
# Mikroskopie: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol_EXT
REGEX_IMAGE = r"^\d{8}_\d{6}__[a-zA-Z0-9-]+_[a-zA-Z0-9-]+__[1]\.(jpg|png)$"

# Spektrum: YYYYMMDD_HHMMSS_TYP_ID_POS_Modus_EXT
# Unterstützt Stellarnet-Endungen:.abs,.trm,.ssm und.csv.
REGEX_SPECTRUM = r"^\d{8}_\d{6}__[a-zA-Z0-9-]+_[a-zA-Z0-9-]+_(ABS|TRANS|SCOPE)\.(abs|trm|ssm|csv)$"

# Klimadaten: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID_EXT
REGEX_CLIMATE = r"^LOG-\d{8}-\d{8}_[a-zA-Z0-9-]+_[a-zA-Z0-9-]+_\d+\.csv$"

# --- UI & GRAFIK STANDARDS ---
# Format für Sensor-Readouts: Exakt zwei Leerzeichen nach dem Doppelpunkt.
SENSOR_FORMAT = "{label}:  {value}"

# Metrologie: Kalibrierungsfaktor (Mikrometer pro Pixel) für den 1mm-Maßstab.
CAL_FACTOR = 1.0