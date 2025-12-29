### 1. Die neue Video-Engine (src/camera_engine.py)
## Änderung:** Ersetzt `nvarguscamerasrc` (CSI) durch `v4l2src` (USB) mit MJPEG-Hardware-Decoding. Dies löst das Latenz-Problem.

python
import cv2
import time
import logging
import subprocess

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CameraEngine")

class CameraEngine:
    def __init__(self):
        self.cap = None
        # Auflösung für Dino-Lite (MJPEG High Speed)
        # 1280x960 ist oft der Sweetspot für 30FPS bei Dino-Lite Edge Modellen
        self.width = 1280
        self.height = 960
        self.fps = 30

    def get_gstreamer_pipeline(self):
        """
        Erstellt die optimierte Pipeline für Jetson Orin Nano + USB Mikroskop.
        Nutzung von nvv4l2decoder (mjpeg=1) entlastet die CPU massiv.
        """
        return (
            f"v4l2src device=/dev/video0! "
            f"image/jpeg, width=(int){self.width}, height=(int){self.height}, framerate=(fraction){self.fps}/1! "
            f"nvv4l2decoder mjpeg=1! "
            f"nvvidconv! "
            f"video/x-raw, format=(string)BGRx! "
            f"videoconvert! "
            f"video/x-raw, format=(string)BGR! "
            f"appsink drop=1 max-buffers=1"
        )

    def start_stream(self):
        """Startet den Video-Capture Prozess."""
        if self.cap is not None and self.cap.isOpened():
            return

        pipeline = self.get_gstreamer_pipeline()
        logger.info(f"Starte Pipeline: {pipeline}")
        
        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if not self.cap.isOpened():
            logger.error("Fehler: Konnte Videoquelle nicht öffnen. Ist das Mikroskop an USB0?")
            # Fallback für Debugging (ohne GStreamer, langsam aber bildgebend)
            self.cap = cv2.VideoCapture(0)

    def get_frame(self):
        """Liefert den aktuellen Frame als JPEG-Bytes für den Webstream."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Encoding für Web-Transfer (Quality 80 spart Bandbreite)
                ret, buffer = cv2.imencode('.jpg', frame,)
                return buffer.tobytes()
        return None

    def take_snapshot(self, filepath):
        """Speichert ein Standbild in voller Qualität."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                cv2.imwrite(filepath, frame)
                logger.info(f"Snapshot gespeichert: {filepath}")
                return True
        return False

    def release(self):
        if self.cap:
            self.cap.release()
