from flask import Flask, render_template, Response, request, jsonify
from data_manager import DataManager
from camera_engine import CameraEngine
from file_monitor import start_watchdog
from config import DIRS
import serial
import time
import os
import subprocess  
import cv2
from datetime import datetime
import threading 
from config import GST_PIPELINE, DIRS

# Wichtig: GST_PIPELINE muss definiert sein (z.B. aus config.py oder hier)
GST_GST_PIPELINE = "v4l2src device=/dev/video0 ! videoconvert ! video/x-raw, format=BGR ! appsink"

import cv2
import threading
from config import GST_PIPELINE, DIRS

class VideoCamera:
    def __init__(self):
        # Initialisierung der GStreamer Pipeline für den Jetson
        self.cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
        self.lock = threading.Lock()
        self.is_frozen = False
        self.last_frame = None
        
        if not self.cap.isOpened():
            print("ERROR: Kamera konnte nicht mit GStreamer gestartet werden.")
        else:
            # --- HARDWARE-INIT FÜR DINO-LITE HIER EINFÜGEN ---
            try:
                # Setzt Arbeitshelligkeit (80 ist oft besser als 128 gegen Grieseln)
                subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '-c', 'brightness=80'], check=True)
                # Schärfe leicht anheben
                subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '-c', 'sharpness=5'], check=True)
                # Autofokus aus, damit das Bild stabil bleibt
                subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '-c', 'focus_automatic_continuous=0'], check=True)
                print("--- DINO-LITE HARDWARE PARAMETER GESETZT ---")
            except Exception as e:
                print(f"WARNUNG: Hardware-Parameter konnten nicht gesetzt werden: {e}")
    
    def get_frame(self):
        with self.lock:
            # Falls nicht eingefroren, neuen Frame lesen
            if not self.is_frozen or self.last_frame is None:
                success, frame = self.cap.read()
                if not success:
                    return None
                
                # Overlay direkt auf den Frame zeichnen
                self.last_frame = self._draw_overlay(frame)
            
            # Kodierung für den Flask-Stream
            success, jpeg = cv2.imencode('.jpg', self.last_frame)
            if not success:
                return None
            return jpeg.tobytes()

    def _draw_overlay(self, frame):
        """Zeichnet den 1mm Maßstab fixiert unten rechts."""
        # Parameter: 100px entsprechen 1mm (Kalibrierungswert für AP 8)
        line_width = 100 
        h, w = frame.shape[:2]
        
        # Position: 20px Abstand vom Rand
        x2, y2 = w - 20, h - 20
        x1, y1 = x2 - line_width, y2
        
        # Weiße Linie (2px Dicke)
        cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
        
        # Label: "1mm" exakt zentriert über der Linie
        text = "1mm"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        
        text_x = x1 + (line_width // 2) - (text_size[0] // 2)
        text_y = y1 - 8  # 8px Abstand über der Linie
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
        return frame

    def toggle_freeze(self):
        """Schaltet den Freeze-Modus um und gibt den neuen Status zurück."""
        with self.lock:
            self.is_frozen = not self.is_frozen
            return self.is_frozen

    def take_snapshot(self, filepath):
        """Speichert den aktuellen Frame (inkl. Overlay) auf die Disk."""
        with self.lock:
            if self.last_frame is not None:
                return cv2.imwrite(filepath, self.last_frame)
        return False

    def stop(self):
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()

# Flask Setup
base_path = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(base_path, '..', 'templates')
app = Flask(__name__, template_folder=template_path)

dm = DataManager()
cam = CameraEngine()

# Start Hardware
cam.start_stream()
start_watchdog()

def arduino_bridge():
    """Liest Arduino: T1\\tH1\\tT2\\tH2\\tGasAnalog\\tAlarm"""
    while True:
        try:
            ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
            dm.set_led("clim", "green")
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and "\t" in line:
                    p = line.split("\t")
                    if len(p) >= 5:
                        # Mapping auf DataManager
                        dm.update_sensors(float(p[0]), float(p[2]), float(p[1]), float(p[3]), int(p[4]))
        except:
            dm.set_led("clim", "red")
            time.sleep(5)

threading.Thread(target=arduino_bridge, daemon=True).start()
### End Hardware Setup ###



@app.route('/')
def index(): return render_template('index.html')

@app.route('/stream')
def stream():
    def event_stream():
        q = dm.listen()
        while True: yield q.get()
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            frame_bytes = cam.get_frame()
            if frame_bytes is not None:
                # Hier dürfen keine Prints oder sleeps stehen, die den Stream bremsen
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Falls kein Bild kommt, eine winzige Pause, um CPU-Last zu vermeiden
                time.sleep(0.01)
                
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/freeze', methods=['POST'])
def freeze():
    return jsonify({"frozen": cam.toggle_freeze()})

@app.route('/api/save_data', methods=['POST'])
def save_data():
    data = request.json
    mode = data.get('mode')
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    typ = data.get('typ', 'R')
    id_val = data.get('id', 'ID').replace(" ", "_")
    pos = data.get('pos', 'POS').replace(" ", "_")

    # --- NAMING SCHEME IMPLEMENTATION ---
    if mode == 'micro':
        # YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol_EXT
        fn = f"{ts}_{typ}_{id_val}_{pos}_{data['licht']}_{data['pol']}.jpg"
        path = os.path.join(DIRS['SNAPSHOTS'], fn)
        if cam.take_snapshot(path): return jsonify({"status": "success", "file": fn})
            
    elif mode == 'spec':
        # YYYYMMDD_HHMMSS_TYP_ID_POS_Modus_EXT
        fn = f"{ts}_{typ}_{id_val}_{pos}_{data['spec_mode']}.abs"
        # Hier Ingest-Logik einfügen (Verschieben aus Drop-Zone)
        return jsonify({"status": "success", "file": fn})

    elif mode == 'clim':
        # LOG-Zeitraum_Bezeichnung_Ortsangabe_ID_EXT
        fn = f"LOG-{ts}_{typ}_{pos}_{id_val}.csv"
        path = os.path.join(DIRS['CLIMATE'], fn)
        # Logik zum Schreiben der CSV...
        return jsonify({"status": "success", "file": fn})

    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)