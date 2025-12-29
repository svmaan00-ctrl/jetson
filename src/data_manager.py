import threading
import queue
import json
import time

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
            "t1": 0.0, "t2": 0.0, "rh1": 0.0, "rh2": 0.0, "gas": 0
        }
        self.status_leds = {"micro": "red", "spec": "red", "clim": "red"}

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
        self.current_values.update({
            "t1": t1, "t2": t2, "rh1": rh1, "rh2": rh2, "gas": gas
        })
        self.status_leds["clim"] = "green" if gas < 400 else "red"
        self.announce("climate_update", {"values": self.current_values, "leds": self.status_leds})

    def set_led(self, system, color):
        self.status_leds[system] = color
        self.announce("status_update", {"leds": self.status_leds})