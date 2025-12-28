import cv2
import logging
import gc
# Import der Metrologie-Konstanten
from config import CAL_FACTOR

class CameraEngine:
    def __init__(self, device_id=0):
        # Hardware-beschleunigte Pipeline für USB-Kameras auf dem Jetson [13, 14]
        # 1. v4l2src: Greift auf die USB-Kamera zu.
        # 2. nvv4l2decoder: Nutzt die Jetson-Hardware zum Dekodieren von MJPEG.
        # 3. nvvidconv: Konvertiert das Format auf der iGPU in BGRx (OpenCV kompatibel). [12]
        self.pipeline = (
            f"v4l2src device=/dev/video{device_id}! "
            f"image/jpeg,width=1280,height=720,framerate=30/1! "
            f"nvv4l2decoder mjpeg=1! "
            f"nvvidconv! "
            f"video/x-raw,format=BGRx! "
            f"videoconvert! "
            f"video/x-raw,format=BGR! "
            f"appsink drop=1 sync=false"
        )
        self.cap = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)

    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        
        # --- AP 4: 1mm-Maßstab Einblendung ---
        # Berechnung der Linienlänge basierend auf dem Kalibrierungsfaktor.
        line_length_px = int(1000 / CAL_FACTOR)
        h, w = frame.shape[:2]
        
        # Position: Unten rechts (Offset 50px vom Rand)
        pt1 = (w - 50 - line_length_px, h - 50)
        pt2 = (w - 50, h - 50)
        
        # Linie zeichnen
        cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
        
        # Text zentriert über der Linie
        text = "1mm"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 0.5, 1)
        text_x = pt1 + (line_length_px // 2) - (text_size // 2)
        cv2.putText(frame, text, (text_x, pt1[1] - 10), font, 0.5, (0, 255, 0), 1)
        
        return frame

    def __del__(self):
        # Ressourcen sauber freigeben und Speicher bereinigen [15, 16]
        if self.cap.isOpened():
            self.cap.release()
        gc.collect()