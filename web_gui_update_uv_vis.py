import cv2
import os
import time
import json
import threading
from datetime import datetime
from flask import Flask, render_template_string, Response, request, jsonify

# --- INITIALISIERUNG DER SCHNITTSTELLEN ---
try:
    import serial
    import glob
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

app = Flask(__name__)

# --- PFADE UND ORDNER ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(PROJECT_ROOT, "index.html")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Verzeichnisse für die strukturierte Ablage erstellen
for sub in ['bilder', 'spektren', 'umgebung', 'logs']:
    os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)

# --- GLOBALER STATUS ---
camera = None
state = {
    "freeze": False,      # Status für Standbild-Modus
    "last_frame": None,   # Aktueller Frame für die Anzeige
    "cal_factor": 100,    # Pixel pro Millimeter
    "arduino": { "t1": "-", "h1": "-", "t2": "-", "h2": "-", "gas": "-", "alarm": "Init" }
}

# --- ARDUINO WORKER: Sensordaten im Hintergrund ---
def arduino_worker():
    if not SERIAL_AVAILABLE: return
    while True:
        try:
            ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
            if not ports:
                state["arduino"]["alarm"] = "Kein USB"; time.sleep(2); continue
            with serial.Serial(ports[0], 115200, timeout=1) as ser:
                state["arduino"]["alarm"] = "Bereit"
                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 6:
                            state["arduino"] = {
                                "t1": parts[0], "h1": parts[1], "t2": parts[2], 
                                "h2": parts[3], "gas": parts[4], "alarm": parts[5]
                            }
                    time.sleep(0.05)
        except Exception:
            state["arduino"]["alarm"] = "Fehler"; time.sleep(2)

threading.Thread(target=arduino_worker, daemon=True).start()

# --- KAMERA UND MAẞSTAB ---
def init_camera():
    global camera
    for idx in [0, 1, 2]:
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024)
            camera = cap; return True
    return False

init_camera()

# --- FUNKTION: Maßstab rechts unten zeichnen ---
def draw_scale_bar(image, cal_factor):
    """ Zeichnet den Maßstab permanent rechts unten ins Bild. """
    try:
        f = float(cal_factor)
        h, w = image.shape[:2]
        px_len = int(f) # Länge von 1mm in Pixeln
        
        # Positionierung rechts unten (ca. 50px Abstand vom Rand)
        margin = 50
        x2 = w - margin
        x1 = x2 - px_len
        y = h - 60
        
        # Zeichnung der Doppellinie (Schwarz für Schatten, Weiß für Sichtbarkeit)
        cv2.line(image, (x1, y), (x2, y), (0, 0, 0), 4)
        cv2.line(image, (x1, y), (x2, y), (255, 255, 255), 2)
        cv2.line(image, (x1, y-5), (x1, y+5), (255, 255, 255), 2) # Abschlussstrich links
        cv2.line(image, (x2, y-5), (x2, y+5), (255, 255, 255), 2) # Abschlussstrich rechts
        
        # Text-Zentrierung: Berechnung der Textbreite
        text = "1 mm"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.6
        thickness = 1
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        text_x = x1 + (px_len - text_size[0]) // 2 # Mittige Positionierung über der Linie
        
        cv2.putText(image, text, (text_x, y-15), font, scale, (255, 255, 255), thickness)
        return image
    except Exception as e:
        print(f"Fehler Maßstab: {e}")
        return image

# --- ROUTEN ---
@app.route('/')
def index():
    with open(HTML_FILE, "r", encoding='utf-8') as f:
        return render_template_string(f.read())

@app.route('/get_env_data')
def get_env_data(): return jsonify(state["arduino"])

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if camera and camera.isOpened():
                if not state["freeze"]:
                    success, frame = camera.read()
                    if success: 
                        # Maßstab wird hier permanent in den Live-Stream gezeichnet
                        state["last_frame"] = draw_scale_bar(frame, state["cal_factor"])
                
                if state["last_frame"] is not None:
                    _, buf = cv2.imencode('.jpg', state["last_frame"])
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            time.sleep(0.04)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_freeze', methods=['POST'])
def toggle_freeze():
    state["freeze"] = not state["freeze"]; return jsonify(status="ok")

@app.route('/set_cal', methods=['POST'])
def set_cal():
    state['cal_factor'] = float(request.json['cal']); return jsonify(success=True)

# BILDDATEI SPEICHERN: Inklusive permanentem Maßstab im gespeicherten Bild
@app.route('/snapshot', methods=['POST'])
def snapshot():
    if state["last_frame"] is not None:
        d = request.json
        ts = datetime.now().strftime("%y%m%d_%H%M%S")
        fname = f"{ts}_{d['type']}_{d['name']}_{d['pos']}_{d['light']}_{d['pol']}.jpg"
        # Bild ist bereits mit Maßstab versehen durch den Video-Feed
        cv2.imwrite(os.path.join(DATA_DIR, 'bilder', fname), state["last_frame"])
        return jsonify(filename=fname)
    return jsonify(error="no frame")

# SPEKTRENDATEI SPEICHERN (Ohne Integration im Dateinamen)
@app.route('/save_spectro', methods=['POST'])
def save_spectro():
    d = request.json
    ts = datetime.now().strftime("%y%m%d_%H%M%S")
    fname = f"{ts}_{d['type']}_{d['name']}_{d['mode']}.csv"
    with open(os.path.join(DATA_DIR, 'spektren', fname), "w") as f:
        f.write(f"Wavelength,Intensity\n# Metadata: {json.dumps(d)}")
    return jsonify(filename=fname)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)