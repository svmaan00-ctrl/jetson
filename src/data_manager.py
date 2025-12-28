import threading
import re
import logging
from config import REGEX_IMAGE, REGEX_SPECTRUM, SENSOR_FORMAT

class DataManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Thread-safe Singleton Pattern [3]
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DataManager, cls).__new__(cls)
                cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.lock = threading.Lock()
        # Initialer Systemzustand
        self.state = {
            "temperature": 0.0,
            "humidity": 0.0,
            "last_image_path": None,
            "last_spectrum_path": None,
            "system_ready": True
        }

    # --- SENSOR LOGIK ---
    def update_sensors(self, temp, hum):
        with self.lock:
            self.state["temperature"] = temp
            self.state["humidity"] = hum

    def get_formatted_temp(self):
        # UI-Standard: Exakt zwei Leerzeichen nach dem Doppelpunkt
        return SENSOR_FORMAT.format(label="Temperatur", value=f"{self.state['temperature']:.1f}°C")

    # --- DATEI VALIDIERUNG (Naming Scheme) ---
    def validate_filename(self, filename, file_type="image"):
        """Prüft, ob der Dateiname dem strikten 2025er Schema entspricht ."""
        pattern = REGEX_IMAGE if file_type == "image" else REGEX_SPECTRUM
        if re.match(pattern, filename):
            return True
        logging.error(f"Naming Scheme Failure: {filename}")
        return False

    # --- STATE MANAGEMENT ---
    def set_last_file(self, file_path, file_type="image"):
        with self.lock:
            if file_type == "image":
                self.state["last_image_path"] = file_path
            else:
                self.state["last_spectrum_path"] = file_path

    def get_current_state(self):
        with self.lock:
            # Rückgabe einer Kopie zur Vermeidung von Race Conditions
            return self.state.copy()