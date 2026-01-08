import os
import shutil
import threading
import queue
import json
import time
import logging
import statistics
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Pfade gemäß Master-Konfiguration
BASE_DIR = os.path.expanduser("~/inspection_project/data/")
INBOX = os.path.join(BASE_DIR, "x200_rohdaten_eingang/")
ARCHIVE = os.path.join(BASE_DIR, "archivierte_spektren/")

class DataManager:
    _instance = None
    _lock = threading.Lock()

    def push_event(self, event_str):
        """Verteilt den SSE-String an alle angemeldeten Listener."""
        with self._lock:
            for queue in self.listeners:
                queue.put(event_str)

    def listen(self):
        """Erstellt eine neue Queue für einen Browser-Tab."""
        from queue import Queue
        q = Queue(maxsize=10)
        with self._lock:
            self.listeners.append(q)
        return q

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataManager, cls).__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        # --- Dein Original-Code (Sensoren & SSE) ---
        self.listeners = []
        self.current_values = {"t1": 0.0, "t2": 0.0, "rh1": 0.0, "rh2": 0.0, "gas": 0}
        self.status_leds = {"micro": "red", "spec": "red", "clim": "red"}
        
        # --- KI-Pipeline Erweiterung - # Hinweis: SpectraHandler muss in src/ definiert oder importiert sein
        self._ensure_dirs()
        self.event_handler = SpectraHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, INBOX, recursive=False)
        self.observer.start()

    def _ensure_dirs(self):
        os.makedirs(INBOX, exist_ok=True)
        os.makedirs(ARCHIVE, exist_ok=True)

    # --- SSE & Sensor Methoden (Dein Original) ---
    def listen(self):
        q = queue.Queue(maxsize=10)
        self.listeners.append(q)
        return q

    def announce(self, msg_type, payload):
        msg = json.dumps({"type": msg_type, "payload": payload})
        sse_msg = f"data: {msg}\n\n"
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(sse_msg)
            except queue.Full:
                del self.listeners[i]

    def update_sensors(self, t1, t2, rh1, rh2, gas):
        self.current_values.update({"t1": t1, "t2": t2, "rh1": rh1, "rh2": rh2, "gas": gas})
        self.status_leds["clim"] = "green" if gas < 400 else "red"
        self.announce("climate_update", {"values": self.current_values, "leds": self.status_leds})

    def set_led(self, system, color):
        self.status_leds[system] = color
        self.announce("status_update", {"leds": self.status_leds})

    # --- Neue KI-Pipeline Methoden ---
    def normalize_snv(self, raw_data):
        """ SNV Normalisierung für Random Forest Vergleichbarkeit """
        if not raw_data: return []
        m = statistics.mean(raw_data)
        s = statistics.stdev(raw_data)
        return [(x - m) / s for x in raw_data] if s > 0 else raw_data

    def process_incoming_spectrum(self, file_path):
        filename = os.path.basename(file_path)
        # Validierung Naming Scheme
        parts = filename.replace(".abs", "").split("_")
        if len(parts) < 4:
            logging.error(f"Naming Error: {filename}")
            return

        with self._lock:
            try:
                # 1. Spektrometer-LED auf Orange (Processing)
                self.set_led("spec", "orange")
                
                # 2. Daten laden & normalisieren
                with open(file_path, 'r') as f:
                    raw_values = [float(l.strip()) for l in f if l.strip()]
                
                norm_values = self.normalize_snv(raw_values)
                
                # 3. Archivierung (Nach Normalisierung)
                target = os.path.join(ARCHIVE, filename)
                shutil.move(file_path, target)
                
                # 4. UI Update
                self.set_led("spec", "green")
                self.announce("new_spectrum", {"id": parts[2], "pos": parts[3], "file": filename})
                logging.info(f"KI-Ready: {filename} archiviert.")

            except Exception as e:
                self.set_led("spec", "red")
                logging.error(f"Fehler: {str(e)}")

class SpectraHandler(FileSystemEventHandler):
    def __init__(self, manager):
        self.manager = manager

    def on_closed(self, event):
        if not event.is_directory and event.src_path.endswith(".abs"):
            # Trigger Prozessierung erst wenn Datei sicher auf Disk
            self.manager.process_incoming_spectrum(event.src_path)