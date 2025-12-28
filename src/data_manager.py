import threading
import queue
import json
import time
from datetime import datetime

class DataManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataManager, cls).__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.listeners = []
        self.current_values = {
            "t1": 0.0, "t2": 0.0,
            "rh1": 0.0, "rh2": 0.0,
            "gas": 0, "status": "INIT"
        }
        # Buffer für Status-LEDs
        self.system_status = {
            "micro": "red", # red/green
            "spec": "red",
            "clim": "red"
        }

    def listen(self):
        """Registriert einen neuen SSE-Client (Browser)"""
        q = queue.Queue(maxsize=10)
        self.listeners.append(q)
        return q

    def announce(self, msg_type, payload):
        """Pusht Daten an alle verbundenen Clients"""
        msg = json.dumps({"type": msg_type, "payload": payload, "timestamp": time.time()})
        # Formatierung für SSE Standard: 'data:... \n\n'
        sse_msg = f"data: {msg}\n\n"
        
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(sse_msg)
            except queue.Full:
                del self.listeners[i]

    def update_sensors(self, t1, t2, rh1, rh2, gas):
        """Wird vom Sensor-Thread aufgerufen"""
        self.current_values = {
            "t1": t1, "t2": t2, "rh1": rh1, "rh2": rh2, "gas": gas
        }
        
        # Logik für Klima-LED
        if gas > 200:
            self.system_status["clim"] = "blink" # Alarm
            status_text = "ALARM: GAS"
        elif t1 > 50 or t2 > 50:
            self.system_status["clim"] = "red"
            status_text = "WARN: TEMP"
        else:
            self.system_status["clim"] = "green"
            status_text = "NORMAL"

        self.current_values["status"] = status_text
        
        # Push Update
        self.announce("climate_update", {
            "values": self.current_values,
            "leds": self.system_status
        })

    def set_led(self, system, state):
        """Setzt LED Status manuell (z.B. durch Watchdog)"""
        if system in self.system_status:
            self.system_status[system] = state
            self.announce("led_update", self.system_status)