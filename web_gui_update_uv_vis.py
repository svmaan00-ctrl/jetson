import cv2
import os
import time
import json
import threading
from datetime import datetime
from flask import Flask, render_template_string, Response, request, jsonify

# --- SICHERER IMPORT (SAFE MODE) ---
try:
    import serial
    import glob
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("ACHTUNG: pyserial fehlt. Arduino-Funktionen deaktiviert.")

app = Flask(__name__)

# --- PFADE ---
BASE_DIR = os.path.expanduser('~/inspection_project/data/')
OUTPUT_DIR_IMG = os.path.join(BASE_DIR, 'bilder/')
OUTPUT_DIR_SPEC = os.path.join(BASE_DIR, 'spektren/')
OUTPUT_DIR_ENV = os.path.join(BASE_DIR, 'umgebung/')
LOG_DIR = os.path.join(BASE_DIR, 'logs/')

for d in [OUTPUT_DIR_IMG, OUTPUT_DIR_SPEC, OUTPUT_DIR_ENV, LOG_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- GLOBALE VARIABLEN ---
camera = None
state = {
    "freeze": False,
    "last_frame": None,
    "cal_factor": 100,
    "arduino": { "t1": "-", "h1": "-", "t2": "-", "h2": "-", "gas": "-", "alarm": "Init" }
}

# --- ARDUINO WORKER ---
def arduino_worker():
    if not SERIAL_AVAILABLE: return
    TARGET_PORT = '/dev/ttyACM0' 
    BAUD_RATE = 115200
    
    while True:
        try:
            ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
            port_to_use = None
            if TARGET_PORT in ports: port_to_use = TARGET_PORT
            elif ports: port_to_use = ports[0]
            
            if not port_to_use:
                state["arduino"]["alarm"] = "Kein USB"
                time.sleep(2)
                continue

            with serial.Serial(port_to_use, BAUD_RATE, timeout=2) as ser:
                state["arduino"]["alarm"] = "Bereit"
                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 6:
                            state["arduino"] = {
                                "t1": parts[0], "h1": parts[1],
                                "t2": parts[2], "h2": parts[3],
                                "gas": parts[4], "alarm": parts[5]
                            }
                    time.sleep(0.05)
        except:
            state["arduino"]["alarm"] = "Fehler"
            time.sleep(2)

threading.Thread(target=arduino_worker, daemon=True).start()

# --- KAMERA INIT ---
def init_camera():
    global camera
    if camera is not None: camera.release()
    for idx in [0, 1, 2, 3]:
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    camera = cap
                    return True
                else: cap.release()
        except: pass
    return False

init_camera()

# --- HELPER ---
def draw_scale_bar_cv2(image, cal_factor):
    try:
        f = float(cal_factor); h, w = image.shape[:2]; px_len = int(f)
        if px_len <= 0: return image 
        x1, y = 50, h - 60; x2 = x1 + px_len
        cv2.line(image, (x1, y), (x2, y), (0, 0, 0), 4)
        cv2.line(image, (x1, y), (x2, y), (255, 255, 255), 2)
        cv2.line(image, (x1, y-5), (x1, y+5), (255, 255, 255), 2)
        cv2.line(image, (x2, y-5), (x2, y+5), (255, 255, 255), 2)
        cv2.putText(image, "1 mm", (x1, y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        return image
    except: return image

# --- HTML CODE ---
html_code = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Jetson Lab Tool</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            background: #121212; color: #e0e0e0; 
            font-family: 'Segoe UI', sans-serif; 
            margin: 0; padding: 5px; 
            height: 100vh; width: 100vw; overflow: hidden; 
            display: flex; 
        }
        
        .wrapper { display: flex; gap: 5px; width: 100%; height: 100%; }
        .sidebar { width: 240px; display: flex; flex-direction: column; gap: 5px; flex-shrink: 0; }
        
        .module { background: #1a1a1a; padding: 6px; border-radius: 4px; border: 1px solid #333; display: flex; flex-direction: column; gap: 3px; }
        .module-fill { flex-grow: 1; }
        
        h3 { color: #00adb5; font-size: 11px; margin: 0 0 4px 0; border-bottom: 1px solid #333; padding-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        label { font-size: 9px; color: #777; margin-top: 1px; }
        
        /* HIER IST DER SCHLÜSSEL: Select und Input sind 20px hoch */
        select, input { 
            width: 100%; background: #252525; color: white; border: 1px solid #3d3d3d; 
            border-radius: 2px; font-size: 11px; height: 20px; padding-left: 4px; 
        }
        .row { display: flex; gap: 4px; }
        .col { flex: 1; min-width: 0; }
        
        /* LED LEISTE */
        .status-grid { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 2px; 
            background: #000; padding: 5px; border-radius: 4px; border: 1px solid #333; margin-bottom: 2px;
        }
        .led-item { 
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-size: 9px; font-weight: bold; color: #aaa; 
        }
        .led { margin-top: 2px; width: 8px; height: 8px; border-radius: 50%; background: #333; box-shadow: inset 0 0 2px #000; }
        
        .orange { background: #ffa500; box-shadow: 0 0 5px #ffa500; }
        .green { background: #28a745; box-shadow: 0 0 5px #28a745; }
        .red { background: #dc3545; box-shadow: 0 0 6px #dc3545; animation: blink 0.5s infinite; }
        @keyframes blink { 50% { opacity: 0.3; } }

        /* SENSOR GRID */
        .sensor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 2px; }
        .sensor-box { background: #252525; padding: 3px; border-radius: 3px; text-align: center; border: 1px solid #333; }
        .sensor-label { font-size: 9px; color: #888; display: block; margin-bottom: 1px; }
        .sensor-val { font-family: 'Consolas', monospace; font-size: 12px; font-weight: bold; color: #fff; }
        .unit { font-size: 9px; color: #666; font-weight: normal; }

        .status-row { 
            margin-top: 4px; display: flex; justify-content: space-between; align-items: center; 
            background: #252525; padding: 3px 5px; border-radius: 3px; border: 1px solid #333;
        }
        .status-label { font-size: 9px; color: #888; }
        .status-val { font-size: 10px; font-weight: bold; padding: 1px 4px; border-radius: 2px; background: #333; color: #ccc;}

        .content { flex-grow: 1; display: flex; justify-content: center; align-items: center; background: #000; border-radius: 4px; overflow: hidden; }
        #live-img { max-width: 100%; max-height: 100%; object-fit: contain; }
        
        /* --- BUTTON DESIGNS --- */
        .action-area { margin-top: auto; padding: 6px; border-top: 1px solid #333; gap: 5px; }
        
        /* BASIS BUTTON STYLE FÜR ALLE (Damit Höhe stimmt) */
        button {
            height: 20px; /* EXAKT WIE INPUTS */
            line-height: 18px; /* Text vertikal zentrieren */
            padding: 0 5px;    /* Nur seitlich Padding */
            border-radius: 2px;
            font-size: 10px; font-weight: bold; width: 100%;
            cursor: pointer; border: none;
        }

        /* FARBEN */
        .btn-grey { background: #666; color: white; }
        .btn-grey:hover { background: #555; }

        .btn-freeze { background: #666; color: white; }
        .btn-freeze.active { background: #dc3545; } 
        
        .btn-green { background: #28a745; color: white; font-size: 11px; }
        .btn-green:hover { background: #218838; }
        
        /* Der große Speichern Button unten darf etwas höher sein */
        .action-area .btn-green { height: 28px; line-height: 28px; }

        #status-text { font-size: 10px; color: #00ff00; font-family: monospace; text-align: center; min-height: 12px; }
    </style>
</head>
<body>

<div class="wrapper">
    <div class="sidebar">
        <div class="status-grid">
            <div class="led-item">MIC <div id="led-mic" class="led orange"></div></div>
            <div class="led-item">SPEC <div id="led-spec" class="led orange"></div></div>
            <div class="led-item">ENV <div id="led-env" class="led orange"></div></div>
            <div class="led-item">SYS <div id="led-sys" class="led green"></div></div>
        </div>

        <div class="module">
            <h3>1. Proben-Identifikation</h3>
            <div class="row">
                <div class="col" style="flex:1">
                    <label>Typ</label>
                    <select id="p_type">
                        <option value="B">Bohrprobe</option>
                        <option value="W">Wischprobe</option>
                        <option value="M">Material</option>
                        <option value="R">Referenz</option>
                    </select>
                </div>
                <div class="col" style="flex:1"><label>ID</label><input type="text" id="p_name" value="P_01"></div>
            </div>
            <label>Position</label><input type="text" id="p_pos" value="Zentrum">
        </div>

        <div class="module">
            <h3>2. Optik & Kalibrierung</h3>
            <div class="row">
                <div class="col"><label>Licht</label><select id="m_light"><option value="R">Ring</option><option value="C">Coax</option><option value="S">Side</option><option value="O">Off</option></select></div>
                <div class="col"><label>Pol</label><select id="m_pol"><option value="P0">Aus</option><option value="P1">Ein</option></select></div>
            </div>
            <label>Cal (px/mm)</label><input type="number" id="cal_factor" value="100" oninput="updateCal()">
        </div>

        <div class="module">
            <h3>3. Umgebungsdaten</h3>
            <div class="sensor-grid">
                <div class="sensor-box"><span class="sensor-label">TEMP 1</span><span id="val-t1" class="sensor-val">--</span><span class="unit">°C</span></div>
                <div class="sensor-box"><span class="sensor-label">FEUCHT 1</span><span id="val-h1" class="sensor-val">--</span><span class="unit">%</span></div>
                <div class="sensor-box"><span class="sensor-label">TEMP 2</span><span id="val-t2" class="sensor-val">--</span><span class="unit">°C</span></div>
                <div class="sensor-box"><span class="sensor-label">FEUCHT 2</span><span id="val-h2" class="sensor-val">--</span><span class="unit">%</span></div>
            </div>
            <div class="status-row">
                <span class="status-label">GAS LEVEL</span>
                <span id="val-gas" style="font-family:monospace; color:white;">--</span>
            </div>
            <div class="status-row">
                <span class="status-label">STATUS</span><span id="val-alarm" class="status-val">INIT</span>
            </div>
            <button class="btn-grey" style="margin-top:5px;" onclick="saveEnv()">LOG DATEN</button>
        </div>

        <div class="module">
            <h3>4. Spektrometer</h3>
            <div class="row" style="align-items: flex-end;">
                <div class="col" style="flex:1;">
                    <label>Modus</label>
                    <select id="x_mode">
                        <option value="A">Absorption</option>
                        <option value="T">Transmission</option>
                        <option value="S">Scope</option>
                    </select>
                </div>
                <div class="col" style="flex:1;">
                    <label>&nbsp;</label>
                    <button class="btn-green" onclick="saveSpec()">MESSUNG</button>
                </div>
            </div>
        </div>

        <div class="module-fill"></div>

        <div class="module action-area">
            <div id="status-text">Bereit</div>
            <div class="row">
                 <button id="freeze-btn" class="btn-freeze" onclick="toggleFreeze()">STANDBILD</button>
            </div>
            <button class="btn-green" onclick="saveSnapshot()">BILD SPEICHERN</button>
        </div>
    </div>
    <div class="content"><img id="live-img" src="{{ url_for('video_feed') }}"></div>
</div>

<script>
    let frozen = false;

    // --- SENSOR POLLING ---
    function fetchSensorData() {
        fetch('/get_env_data').then(r => r.json()).then(data => {
            document.getElementById('val-t1').innerText = data.t1;
            document.getElementById('val-h1').innerText = data.h1;
            document.getElementById('val-t2').innerText = data.t2;
            document.getElementById('val-h2').innerText = data.h2;
            document.getElementById('val-gas').innerText = data.gas; 
            
            const a = document.getElementById('val-alarm');
            const l = document.getElementById('led-env');
            a.innerText = data.alarm;
            
            if(data.alarm === "ALARM") { 
                a.style.background = "#d9534f"; a.style.color = "white"; l.className = "led red"; 
            } else if (data.alarm === "Normal" || data.alarm === "Bereit") { 
                a.style.background = "#28a745"; a.style.color = "white"; l.className = "led green"; 
            } else { 
                a.style.background = "#444"; a.style.color = "#ccc"; l.className = "led orange"; 
            }
        }).catch(e => console.log(e));
    }
    setInterval(fetchSensorData, 1000);

    // --- KALIBRIERUNG & FREEZE ---
    function updateCal() { fetch('/set_cal', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({cal: document.getElementById('cal_factor').value}) }); }
    function toggleFreeze() { 
        frozen = !frozen; 
        const btn = document.getElementById('freeze-btn'); 
        btn.classList.toggle('active', frozen); 
        btn.innerText = frozen ? "BILD EINGEFROREN" : "STANDBILD";
        fetch('/toggle_freeze', {method: 'POST'}); 
    }

    // --- 1. MIKROSKOP SPEICHERN ---
    function saveSnapshot() {
        const data = {
            type: document.getElementById('p_type').value, 
            name: document.getElementById('p_name').value,
            pos: document.getElementById('p_pos').value, 
            light: document.getElementById('m_light').value,
            pol: document.getElementById('m_pol').value, 
            cal: document.getElementById('cal_factor').value
        };
        setStatus("Speichere Bild...", "orange");
        fetch('/snapshot', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
        .then(r => r.json()).then(d => {
            flashLed('led-mic');
            setStatus("Bild OK: " + d.filename, "green");
        });
    }

    // --- 2. SPEKTROMETER SPEICHERN ---
    function saveSpec() {
        const data = {
            type: document.getElementById('p_type').value, 
            name: document.getElementById('p_name').value,
            mode: document.getElementById('x_mode').value
        };
        setStatus("Speichere Spektrum...", "orange");
        fetch('/save_spectro', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
        .then(r => r.json()).then(d => {
            flashLed('led-spec');
            setStatus("Spec OK: " + d.filename, "green");
        });
    }

    // --- 3. UMGEBUNG SPEICHERN ---
    function saveEnv() {
        setStatus("Logge Umgebung...", "orange");
        fetch('/save_env', { method: 'POST' })
        .then(r => r.json()).then(d => {
            flashLed('led-env');
            setStatus("Log OK: " + d.filename, "green");
        });
    }

    // --- HELPER UI ---
    function setStatus(txt, color) {
        const s = document.getElementById('status-text');
        s.innerText = txt;
        s.style.color = (color === "green") ? "#00ff00" : (color === "red" ? "#ff0000" : "#ffa500");
    }
    function flashLed(id) {
        document.getElementById(id).className = 'led green';
        setTimeout(() => { document.getElementById(id).className = 'led orange'; }, 2000);
    }
</script>
</body>
</html>
"""

# --- ROUTEN ---
@app.route('/')
def index(): return render_template_string(html_code)

@app.route('/get_env_data')
def get_env_data(): return jsonify(state["arduino"])

@app.route('/set_cal', methods=['POST'])
def set_cal():
    try: state['cal_factor'] = float(request.json['cal']); return jsonify(success=True)
    except: return jsonify(success=False)

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if camera is None or not camera.isOpened():
                time.sleep(1); continue
            if not state["freeze"]:
                success, frame = camera.read()
                if success: state["last_frame"] = frame.copy()
            if state["last_frame"] is not None:
                img = state["last_frame"].copy()
                if state["freeze"]: img = draw_scale_bar_cv2(img, state["cal_factor"])
                ret, buf = cv2.imencode('.jpg', img)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            time.sleep(0.04)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_freeze', methods=['POST'])
def toggle_freeze(): state["freeze"] = not state["freeze"]; return jsonify(status="ok")

# --- SPEICHERFUNKTION 1: MIKROSKOP (BILD + JSON) ---
@app.route('/snapshot', methods=['POST'])
def snapshot():
    if state["last_frame"] is not None:
        d = request.json
        ts = datetime.now().strftime("%y%m%d_%H%M%S")
        # Format: Zeit_Typ_ID_Pos_Licht_Pol.jpg
        fname = f"{ts}_{d['type']}_{d['name']}_{d['pos']}_{d['light']}_{d['pol']}.jpg"
        
        img = state["last_frame"].copy()
        img = draw_scale_bar_cv2(img, d['cal'])
        d['env_data'] = state['arduino']
        
        cv2.imwrite(os.path.join(OUTPUT_DIR_IMG, fname), img)
        with open(os.path.join(LOG_DIR, fname.replace(".jpg", ".json")), "w") as f: json.dump(d, f)
        
        return jsonify(filename=fname)
    return jsonify(error="no frame")

# --- SPEICHERFUNKTION 2: SPEKTROMETER (CSV) ---
@app.route('/save_spectro', methods=['POST'])
def save_spectro():
    d = request.json
    ts = datetime.now().strftime("%y%m%d_%H%M%S")
    # Format: Zeit_Typ_ID_Mode.csv
    fname = f"{ts}_{d['type']}_{d['name']}_{d['mode']}.csv"
    path = os.path.join(OUTPUT_DIR_SPEC, fname)
    
    # Simuliere Spektren-Daten
    with open(path, "w") as f:
        f.write("Wavelength,Intensity\n")
        f.write("400,0.1\n401,0.2\n402,0.5\n") # Dummy Daten
        f.write(f"# Metadata: {json.dumps(d)}")
        
    return jsonify(filename=fname)

# --- SPEICHERFUNKTION 3: UMGEBUNG (TXT) ---
@app.route('/save_env', methods=['POST'])
def save_env():
    ts = datetime.now().strftime("%y%m%d_%H%M%S")
    fname = f"{ts}_RaumLog.txt"
    path = os.path.join(OUTPUT_DIR_ENV, fname)
    
    env = state["arduino"]
    # Erstelle eine saubere Textdatei mit den Werten
    content = f"""ZEITSTEMPEL: {ts}
TEMP 1:   {env['t1']} °C
FEUCHTE 1:{env['h1']} %
TEMP 2:   {env['t2']} °C
FEUCHTE 2:{env['h2']} %
GAS:      {env['gas']}
ALARM:    {env['alarm']}
"""
    with open(path, "w") as f:
        f.write(content)
        
    return jsonify(filename=fname)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)