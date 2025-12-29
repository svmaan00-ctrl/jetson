from flask import Flask, render_template, Response, request, jsonify
from data_manager import DataManager
from camera_engine import CameraEngine
from file_monitor import start_watchdog
from config import DIRS
import threading
import serial
import time
import os
from datetime import datetime

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