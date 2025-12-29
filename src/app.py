from flask import Flask, render_template, Response, request, jsonify
from config import DIRS, ARDUINO_PORT, BAUDRATE
from data_manager import DataManager
from camera_engine import CameraEngine
from file_monitor import start_watchdog
import threading
import serial
import time
import os
from datetime import datetime

app = Flask(__name__, template_folder='../templates')
dm = DataManager()
cam = CameraEngine()

def arduino_bridge():
    """Liest Arduino-Daten (Tab-getrennt)"""
    while True:
        try:
            ser = serial.Serial(ARDUINO_PORT, BAUDRATE, timeout=1)
            dm.set_led("clim", "green")
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 5:
                        vals = [float(p) for p in parts[:5]]
                        dm.update_sensors(*vals)
        except Exception as e:
            dm.set_led("clim", "red")
            time.sleep(5)

# Threads starten
threading.Thread(target=arduino_bridge, daemon=True).start()
start_watchdog() # Monitor für x200_rohdaten_eingang
cam.start_stream()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    def event_stream():
        q = dm.listen()
        while True:
            yield q.get()
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            frame = cam.get_frame()
            if frame:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.04)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/freeze', methods=['POST'])
def toggle_freeze():
    state = cam.toggle_freeze()
    return jsonify({"frozen": state})

@app.route('/api/save_data', methods=['POST'])
def save_data():
    data = request.json
    mode = data.get('mode')
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Naming Scheme Engine
    if mode == 'micro':
        filename = f"{ts}_{data['typ']}_{data['id']}_{data['pos']}_{data['licht']}_{data['pol']}.jpg"
        path = os.path.join(DIRS['SNAPSHOTS'], filename)
        if cam.take_snapshot(path):
            return jsonify({"status": "success", "file": filename})
            
    elif mode == 'spec':
        filename = f"{ts}_{data['typ']}_{data['id']}_{data['pos']}_{data['spec_mode']}.csv"
        # Hier würde die Logik zum Verschieben aus dem Ingest-Ordner greifen
        return jsonify({"status": "success", "file": filename})

    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)