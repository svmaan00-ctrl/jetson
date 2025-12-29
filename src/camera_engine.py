import cv2
import threading
import logging

class CameraEngine:
    def __init__(self, device_id=0):
        self.device_id = device_id
        self.cap = None
        self.lock = threading.Lock()
        self.is_frozen = False
        self.frozen_frame = None

    def start_stream(self):
        """Startet die Kamera mit den funktionierenden V4L2-Parametern."""
        with self.lock:
            if self.cap is None or not self.cap.isOpened():
                # Wir nutzen CAP_V4L2, da dies im Test erfolgreich war
                self.cap = cv2.VideoCapture(self.device_id, cv2.CAP_V4L2)
                
                # Dino-Lite Optimierung
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
                self.cap.set(cv2.CAP_PROP_FPS, 30)

                if not self.cap.isOpened():
                    logging.error("CameraEngine: V4L2-Zugriff fehlgeschlagen.")

    def get_frame(self):
        """Gibt JPEG-Bytes für das Dashboard zurück."""
        if self.is_frozen and self.frozen_frame is not None:
            return self.frozen_frame

        with self.lock:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    # Umwandlung für den Browser
                    _, buffer = cv2.imencode('.jpg', frame)
                    self.frozen_frame = buffer.tobytes()
                    return self.frozen_frame
        return None

    def toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        return self.is_frozen

    def take_snapshot(self, filepath):
        with self.lock:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    return cv2.imwrite(filepath, frame)
        return False