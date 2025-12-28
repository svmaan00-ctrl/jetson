from flask import Flask, render_template, Response, request, jsonify
from data_manager import DataManager
from camera_engine import CameraEngine
from file_monitor import start_watchdog
from config import DIRS, VALID_NAME_REGEX
import threading
import time
import re
import os
from flask import Flask, render_template, Response, request, jsonify

# 1. Absoluten Pfad zum Verzeichnis von app.py ermitteln (das ist /src)
base_path = os.path.dirname(os.path.abspath(__file__))

# 2. Den Pfad zum templates-Ordner eine Ebene höher definieren
template_path = os.path.join(base_path, '..', 'templates')

# 3. Flask mit dem expliziten absoluten Pfad initialisieren
app = Flask(__name__, template_folder=template_path)

dm = DataManager()
cam = CameraEngine()

# Start Background Threads
start_watchdog()
cam.start_stream()

# Mock Sensor Thread (Ersetzen durch echten Serial Code)
def sensor_loop():
    while True:
        # Hier Serial.readline() implementieren
        # Beispiel Daten:
        dm.update_sensors(24.5, 25.1, 45.0, 42.0, 150) 
        time.sleep(1)

threading.Thread(target=sensor_loop, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    def event_stream():
        messages = dm.listen()
        while True:
            msg = messages.get()
            yield msg
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            frame = cam.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

from werkzeug.utils import secure_filename

@app.route('/api/save_data', methods=['POST'])
def save_data():
    data = request.json
    mode = data.get('mode')  # 'micro', 'spec' oder 'clim'
    
    # Basis-Validierung der ML-relevanten Felder 
    for key in ['id', 'pos']:
        val = data.get(key, "")
        if not re.match(VALID_NAME_REGEX, val):
            return jsonify({"status": "error", "msg": f"Ungültige Zeichen in {key}"}), 400

    # Zeitstempel generieren
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    typ = data.get('typ', 'R') # B, W, M, R [cite: 371]
    id_val = secure_filename(data.get('id'))
    pos_val = secure_filename(data.get('pos'))

    # --- 1. Mikroskopie Modus --- [cite: 369]
    if mode == 'micro':
        licht = data.get('licht', 'O') # R, C, S, O [cite: 374]
        pol = data.get('pol', 'Off')   # On, Off [cite: 375]
        # Schema: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol_EXT
        filename = f"{timestamp}_{typ}_{id_val}_{pos_val}_{licht}_{pol}.jpg"
        filepath = os.path.join(DIRS['SNAPSHOTS'], filename)
        
        if cam.take_snapshot(filepath):
            return jsonify({"status": "success", "file": filename})

    # --- 2. Spektrum Modus --- 
    elif mode == 'spec':
        # Schema: YYYYMMDD_HHMMSS_TYP_ID_POS_Modus_EXT
        filename = f"{timestamp}_{typ}_{id_val}_{pos_val}_Spec.csv"
        filepath = os.path.join(DIRS['SPECTRA'], filename)
        
        # Logik zum Verschieben/Speichern der Spektrumsdatei hier einfügen
        return jsonify({"status": "success", "file": filename})

    # --- 3. Klimadaten Modus --- 
    elif mode == 'clim':
        # Schema: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID_EXT
        # Wir nutzen TYP als Bezeichnung und POS als Ortsangabe
        filename = f"LOG-{timestamp}_{typ}_{pos_val}_{id_val}.csv"
        filepath = os.path.join(DIRS['CLIMATE'], filename)
        
        v = dm.current_values # Aktuelle Sensordaten aus DataManager
        with open(filepath, 'w') as f:
            f.write("Timestamp,T1,T2,RH1,RH2,Gas\n")
            f.write(f"{timestamp},{v['t1']},{v['t2']},{v['rh1']},{v['rh2']},{v['gas']}\n")
        
        return jsonify({"status": "success", "file": filename})

    return jsonify({"status": "error", "msg": "Unbekannter Modus"}), 500

if __name__ == '__main__':
    # WICHTIG: threaded=True für SSE
    app.run(host='0.0.0.0', port=5000, threaded=True)