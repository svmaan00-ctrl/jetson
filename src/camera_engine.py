import cv2
import subprocess
import os
import time

class CameraEngine:
    def __init__(self, device_id=0):
        self.cap = None
        self.device_id = device_id
        self.is_frozen = False
        self.frozen_frame = None

    def _control_leds(self, state=1):
        """Steuert Dino-Lite LEDs (0=Aus, 1=An)"""
        try:
            # Dino-Lite nutzt oft 'illumination' Control
            subprocess.run(["v4l2-ctl", "-d", f"/dev/video{self.device_id}", f"--set-ctrl=illumination={state}"], check=False)
        except:
            pass

    def get_gstreamer_pipeline(self):
        """Hardware-beschleunigte Pipeline für USB MJPEG auf Jetson Orin Nano"""
        return (
            f"v4l2src device=/dev/video{self.device_id} ! "
            "image/jpeg, width=1280, height=720, framerate=30/1 ! "
            "nvv4l2decoder mjpeg=1 ! "
            "nvvidconv ! "
            "video/x-raw, format=BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=BGR ! "
            "appsink drop=true max-buffers=1"
        )

    def start_stream(self):
        self._control_leds(1)
        if self.cap is None or not self.cap.isOpened():
            # Erst GStreamer versuchen, dann Standard-V4L2 Fallback
            self.cap = cv2.VideoCapture(self.get_gstreamer_pipeline(), cv2.CAP_GSTREAMER)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.device_id)

    def get_frame(self):
        if self.is_frozen and self.frozen_frame is not None:
            return self.frozen_frame

        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                self.frozen_frame = frame_bytes
                return frame_bytes
        return None

    def toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        return self.is_frozen

    def take_snapshot(self, filepath):
        """Speichert aktuellen Frame in voller Qualität"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return cv2.imwrite(filepath, frame)
        return False 