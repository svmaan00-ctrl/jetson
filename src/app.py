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

@app.route('/api/save_image', methods=['POST'])
def save_image():
    data = request.json
    # Naming Scheme Validierung
    name_parts = [data.get(k) for k in ['typ', 'id', 'pos', 'licht', 'pol']]
    
    # Prüfe auf illegale Zeichen in ID und POS
    if not re.match(VALID_NAME_REGEX, data['id']) or not re.match(VALID_NAME_REGEX, data['pos']):
        return jsonify({"status": "error", "msg": "Invalid Characters"}), 400

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{'_'.join(name_parts)}.jpg"
    filepath = os.path.join(DIRS, filename)
    
    if cam.take_snapshot(filepath):
        return jsonify({"status": "success", "file": filename})
    return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    # WICHTIG: threaded=True für SSE
    app.run(host='0.0.0.0', port=5000, threaded=True)