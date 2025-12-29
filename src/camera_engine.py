import cv2
import time

class CameraEngine:
    def __init__(self):
        self.index = 0
        self.cap = None
        self.frozen = False

    def start_stream(self):
        """Initialisierung exakt wie in deinem erfolgreichen check_cam.py"""
        print("--- ENGINE START ---")
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Warmup wie im Test
        time.sleep(1)
        for _ in range(5):
            self.cap.read()
        print("--- ENGINE BEREIT ---")

    def get_frame(self):
        """Liest direkt und gibt Status im Terminal aus"""
        if self.cap is None or not self.cap.isOpened():
            return None

        success, frame = self.cap.read()
        
        if success and frame is not None:
            # Nur für den Test: Kurze Meldung im Terminal (danach löschen wir das wieder)
            # print("DEBUG: BILD GELESEN") 
            
            # Maßstab laut Master-Konfig
            h, w = frame.shape[:2]
            cv2.line(frame, (w-170, h-40), (w-20, h-40), (255, 255, 255), 2)
            cv2.putText(frame, "1mm", (w-120, h-50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # JPEG Kodierung
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                return buffer.tobytes()
        else:
            print("DEBUG: KAMERA-FEHLER BEI READ")
        return None

    def toggle_freeze(self): return False
    def take_snapshot(self, path):
        if self.cap:
            ret, frame = self.cap.read()
            if ret: return cv2.imwrite(path, frame)
        return False