import cv2
import subprocess
import time
from config import DIRS

class CameraEngine:
    def __init__(self):
        self.cap = None
        self.is_recording = False
        self.pipeline_process = None

    def get_gstreamer_pipeline(self):
        # Orin Nano Pipeline: 
        # ISP -> NVMM -> Resize -> CPU Memory -> Appsink
        return (
            "nvarguscamerasrc! "
            "video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, format=(string)NV12, framerate=(fraction)30/1! "
            "nvvidconv! "
            "video/x-raw, width=(int)960, height=(int)540, format=(string)BGRx! "
            "videoconvert! "
            "video/x-raw, format=(string)BGR! "
            "appsink"
        )

    def start_stream(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.get_gstreamer_pipeline(), cv2.CAP_GSTREAMER)

    def get_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Encode als JPEG für Web-Stream (Software Encoding, aber kleine Auflösung ok)
                ret, buffer = cv2.imencode('.jpg', frame)
                return buffer.tobytes()
        return None

    def take_snapshot(self, filepath):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Speichern in voller Auflösung (hier skaliert durch Pipeline, 
                # für Full-Res müsste man eine separate Pipeline starten oder Snapshot-Mode nutzen)
                cv2.imwrite(filepath, frame)
                return True
        return False

    def start_recording(self, filename):
        """Startet separate GStreamer-Instanz für Recording (High Res)"""
        path = f"{DIRS}/{filename}.mp4"
        # CPU Encoding mit ultrafast Preset für Orin Nano
        cmd = (
            f"gst-launch-1.0 -e nvarguscamerasrc! "
            f"video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1! "
            f"nvvidconv! video/x-raw, format=I420! "
            f"x264enc speed-preset=ultrafast bitrate=8000! "
            f"mp4mux! filesink location={path}"
        )
        self.pipeline_process = subprocess.Popen(cmd.split())
        self.is_recording = True

    def stop_recording(self):
        if self.pipeline_process:
            self.pipeline_process.send_signal(subprocess.signal.SIGINT) # Sende EOS
            self.pipeline_process = None
            self.is_recording = False