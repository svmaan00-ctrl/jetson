import cv2
import os
import time
import json
import threading
import logging
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify

# --- WERKZEUG LOGGING STUMMSCHALTEN ---
# Verhindert, dass jeder GET-Request im Terminal angezeigt wird.
# Nur wirkliche Fehler (ERROR) werden noch gemeldet.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- NEU: Konfiguration importieren ---
# Das setzt voraus, dass config.py im selben Ordner liegt
from config import *

# --- INITIALISIERUNG DER SCHNITTSTELLEN ---
try:
    import serial
    import glob
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# --- FLASK SETUP ---
# Wir nutzen die Pfade aus der Config für Templates (HTML) und Static (CSS/JS)
app = Flask(__name__, 
            template_folder=TEMPLATE_FOLDER, 
            static_folder=STATIC_FOLDER)


# --- ORDNER STRUKTUR SICHERSTELLEN ---
required_folders = [
    UPLOAD_FOLDER_RAW, 
    SNAPSHOT_FOLDER,   
    ARCHIVE_FOLDER,    
    LOG_FOLDER         
]

for folder in required_folders:
    os.makedirs(folder, exist_ok=True)
    print(f"[Init] Ordner geprüft/erstellt: {folder}")

# --- GLOBALER STATUS ---
camera = None
state = {
    "freeze": False,      # Status für Standbild-Modus
    "last_frame": None,   # Aktueller Frame für die Anzeige
    "cal_factor": 115.0,  # Standard-Kalibrierung
    "mic_data": {},       # Platzhalter
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
    # Versuche Indizes 0, 1, 2 durchzugehen
    for idx in [0, 1, 2]:
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        if cap.isOpened():
            # WICHTIG: MJPG setzen
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
            # WICHTIG: Exakt 1280x960 anfordern (laut deinem Log), NICHT 1024
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
            
            camera = cap
            print(f"[Kamera] Init erfolgreich auf Index {idx} mit 1280x960 MJPG")
            return True
    print("[Kamera] Fehler: Keine Kamera gefunden.")
    return False

init_camera()

# --- FUNKTION: Maßstab rechts unten zeichnen ---
def draw_scale_bar(image, cal_factor):
    """ Zeichnet den Maßstab permanent rechts unten ins Bild. """
    try:
        f = float(cal_factor)
        h, w = image.shape[:2]
        px_len = int(f) # Länge von 1mm in Pixeln
        
        # Positionierung rechts unten
        margin = 50
        x2 = w - margin
        x1 = x2 - px_len
        y = h - 60
        
        # Grafik-Operationen (Schatten + Linie)
        cv2.line(image, (x1, y), (x2, y), (0, 0, 0), 4)
        cv2.line(image, (x1, y), (x2, y), (255, 255, 255), 2)
        cv2.line(image, (x1, y-5), (x1, y+5), (255, 255, 255), 2)
        cv2.line(image, (x2, y-5), (x2, y+5), (255, 255, 255), 2)
        
        text = "1 mm"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.6
        thickness = 1
        
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        text_x = x1 + (px_len - text_size[0]) // 2
        
        cv2.putText(image, text, (text_x + 1, y - 14), font, scale, (0, 0, 0), thickness + 1)
        cv2.putText(image, text, (text_x, y - 15), font, scale, (255, 255, 255), thickness)
        
        return image
    except Exception as e:
        return image

# --- ROUTEN ---

@app.route('/')
def index():
    # NEU: Nutzt Flask-Standard und sucht im konfigurierten Template-Ordner
    return render_template('index.html')

@app.route('/get_env_data')
def get_env_data(): 
    return jsonify(state["arduino"])

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if camera and camera.isOpened():
                if not state["freeze"]:
                    success, frame = camera.read()
                    if success: 
                        state["last_frame"] = draw_scale_bar(frame, state["cal_factor"])
                
                if state["last_frame"] is not None:
                    _, buf = cv2.imencode('.jpg', state["last_frame"])
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            time.sleep(0.04)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_freeze', methods=['POST'])
def toggle_freeze():
    state["freeze"] = not state["freeze"]
    return jsonify(status="ok")

@app.route('/set_cal', methods=['POST'])
def set_cal():
    try:
        state['cal_factor'] = float(request.json['cal'])
        return jsonify(success=True)
    except:
        return jsonify(success=False)

# --- BILD SPEICHERN (Mit Position, Licht, Pol) ---
@app.route('/snapshot', methods=['POST'])
def snapshot():
    if state["last_frame"] is not None:
        d = request.json
        ts = datetime.now().strftime("%y%m%d_%H%M%S")
        
        # FORMAT: Datum_Typ_ID_Position_Licht_Pol.jpg
        fname = f"{ts}_{d['type']}_{d['name']}_{d['pos']}_{d['light']}_{d['pol']}.jpg"
        
        # Speichern im Snapshot-Ordner
        save_path = os.path.join(SNAPSHOT_FOLDER, fname)
        cv2.imwrite(save_path, state["last_frame"])
        
        print(f"[SNAPSHOT] Bild gespeichert: {fname}")
        return jsonify(filename=fname)
    return jsonify(error="no frame")


# --- SPEKTRUM SPEICHERN (Ohne Position, nur Modus) ---
@app.route('/save_spectro', methods=['POST'])
def save_spectro():
    d = request.json
    ts = datetime.now().strftime("%y%m%d_%H%M%S")
    
    # FORMAT: Datum_Typ_ID_Modus.csv (Unabhängig vom Bild)
    fname = f"{ts}_{d['type']}_{d['name']}_{d['mode']}.csv"
    
    # Speichern im Archiv-Ordner
    save_path = os.path.join(ARCHIVE_FOLDER, fname)
    with open(save_path, "w") as f:
        f.write(f"Wavelength,Intensity\n# Metadata: {json.dumps(d)}")
    
    print(f"[SPEKTRUM] Datei archiviert: {fname}")
    return jsonify(filename=fname)

    # NEU: Nutzt den flexiblen Pfad aus der Config
    save_path = os.path.join(ARCHIVE_FOLDER, fname)
    
    with open(save_path, "w") as f:
        f.write(f"Wavelength,Intensity\n# Metadata: {json.dumps(d)}")
    
    print(f"[Speichern] Spektrum archiviert: {save_path}")
    return jsonify(filename=fname)

if __name__ == '__main__':
    # Dieser Print erzeugt den klickbaren Link, trotz stummem Logger
    print("\n" + "="*40)
    print(" SYSTEM BEREIT - LEISE MODUS")
    print(" Dashboard öffnen: http://localhost:5000")
    print("="*40 + "\n")
    
    # Host 0.0.0.0 macht den Server im ganzen Netzwerk verfügbar
    app.run(host='0.0.0.0', port=5000, threaded=True)