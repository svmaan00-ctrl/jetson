import cv2
import os
import time
import re
import json
from datetime import datetime
from flask import Flask, render_template_string, Response, request, jsonify

app = Flask(__name__)

# Pfade
BASE_DIR = os.path.expanduser('~/inspection_project/data/')
OUTPUT_DIR = os.path.join(BASE_DIR, 'bilder/')
LOG_DIR = os.path.join(BASE_DIR, 'logs/')

for d in [OUTPUT_DIR, LOG_DIR]:
    if not os.path.exists(d): os.makedirs(d)

camera = None
state = {"freeze": False, "last_frame": None}

def init_camera():
    global camera
    if camera is not None: camera.release()
    for idx in [0, 1, 2]:
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
    return False

init_camera()

def draw_scale_bar_cv2(image, cal_factor):
    try:
        f = float(cal_factor)
        h, w = image.shape[:2]
        px_len = int(f) 
        if px_len <= 0 or px_len > w: return image
        x1, y = 50, h - 60
        x2 = x1 + px_len
        cv2.line(image, (x1, y), (x2, y), (0, 0, 0), 4)
        cv2.line(image, (x1, y), (x2, y), (255, 255, 255), 2)
        cv2.line(image, (x1, y-5), (x1, y+5), (255, 255, 255), 2)
        cv2.line(image, (x2, y-5), (x2, y+5), (255, 255, 255), 2)
        cv2.putText(image, "1 mm", (x1, y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        return image
    except: return image

html_code = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Jetson Control Center</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            background: #121212; color: #ddd; font-family: 'Segoe UI', sans-serif; 
            margin: 0; padding: 10px; height: 100vh; width: 100vw; overflow: hidden; 
            display: flex; flex-direction: column;
        }
        .status-bar { 
            display: flex; gap: 20px; background: #1e1e1e; padding: 8px 15px; 
            border-bottom: 2px solid #333; margin-bottom: 10px; border-radius: 5px; flex-shrink: 0;
        }
        .led-group { display: flex; align-items: center; gap: 8px; font-size: 11px; }
        .led { width: 12px; height: 12px; border-radius: 50%; background: #333; }
        .orange { background: #ffa500; box-shadow: 0 0 8px #ffa500; }
        .green { background: #28a745; box-shadow: 0 0 8px #28a745; }
        
        .wrapper { display: flex; gap: 15px; flex-grow: 1; min-height: 0; }
        .sidebar { width: 300px; display: flex; flex-direction: column; gap: 10px; flex-shrink: 0; }
        
        .module { background: #1e1e1e; padding: 12px; border-radius: 8px; border: 1px solid #333; }
        .module-fill { flex-grow: 1; } 
        
        h3 { color: #00adb5; font-size: 13px; margin: 0 0 8px 0; border-bottom: 1px dotted #444; padding-bottom: 4px; }
        
        label { display: block; margin-top: 8px; font-size: 10px; color: #888; font-weight: bold; }
        select, input { 
            width: 100%; padding: 6px; margin-top: 2px; background: #2a2a2a; 
            color: white; border: 1px solid #444; border-radius: 4px; box-sizing: border-box; font-size: 12px;
        }
        
        .content { 
            flex-grow: 1; display: flex; justify-content: center; align-items: center; 
            background: #000; border-radius: 8px; overflow: hidden; border: 1px solid #333;
            min-height: 0;
        }
        #live-img { 
            max-width: 100%; max-height: 100%; 
            object-fit: contain; /* Bild wird verkleinert, um exakt in den Rahmen zu passen */
        }
        
        .action-area { margin-top: auto; display: flex; flex-direction: column; gap: 8px; }
        .btn-freeze { background: #444; color: white; border: none; padding: 12px; cursor: pointer; font-weight: bold; border-radius: 4px; width: 100%; }
        .btn-freeze.active { background: #d9534f; }
        .btn-save { background: #28a745; color: white; border: none; padding: 15px; font-size: 16px; font-weight: bold; cursor: pointer; border-radius: 4px; width: 100%; }
        .btn-x200 { background: #007bff; color: white; border: none; padding: 10px; border-radius: 4px; cursor: pointer; margin-top: 8px; width: 100%; }
        
        #status-text { font-size: 10px; color: #00ff00; font-family: monospace; text-align: center; min-height: 12px; margin-bottom: 4px; }
    </style>
</head>
<body>

<div class="status-bar">
    <div class="led-group">MIC: <div id="led-mic" class="led orange"></div></div>
    <div class="led-group">SPEC: <div id="led-x200" class="led orange"></div></div>
    <div class="led-group">SYS: <div id="led-sys" class="led green"></div></div>
</div>

<div class="wrapper">
    <div class="sidebar">
        <div class="module">
            <h3>1. Proben-Identifikation</h3>
            <label>Typ</label>
            <select id="p_type">
                <option value="B">Bohrprobe (B)</option>
                <option value="W">Wischprobe (W)</option>
                <option value="M">Materialprobe (M)</option>
                <option value="R">Referenz (R)</option>
            </select>
            <label>Bezeichnung</label>
            <input type="text" id="p_name" value="Probe_01">
            <label>Ort / Position</label>
            <input type="text" id="p_pos" value="Zentrum">
        </div>

        <div class="module">
            <h3>2. Optik & Kalibrierung</h3>
            <label>Lichtquelle</label>
            <select id="m_light">
                <option value="R">Ring (R)</option><option value="C">Coax (C)</option>
                <option value="S">Side (S)</option><option value="O">AUS (O)</option>
            </select>
            <label>Polarisation</label>
            <select id="m_pol">
                <option value="P0">Off</option><option value="P1">On</option>
            </select>
            <label>Kalibrierung (px/mm)</label>
            <input type="number" id="cal_factor" value="244">
        </div>

        <div class="module">
            <h3>3. Spektrometer</h3>
            <label>Messmodus</label>
            <select id="x_mode">
                <option value="A">Absorbance (A)</option>
                <option value="T">Transmission (T)</option>
                <option value="S">Scope Mode (S)</option>
            </select>
            <button class="btn-x200" onclick="transferX200()">X200 DATEN-TRANSFER</button>
        </div>

        <div class="module-fill"></div>

        <div class="module action-area">
            <div id="status-text">System bereit</div>
            <button id="freeze-btn" class="btn-freeze" onclick="toggleFreeze()">STANDBILD</button>
            <button class="btn-save" onclick="saveSnapshot()">MESSUNG SPEICHERN</button>
        </div>
    </div>

    <div class="content">
        <img id="live-img" src="{{ url_for('video_feed') }}">
    </div>
</div>

<script>
    let frozen = false;
    function toggleFreeze() {
        frozen = !frozen;
        const btn = document.getElementById('freeze-btn');
        btn.classList.toggle('active', frozen);
        btn.innerText = frozen ? "STANDBILD AKTIV" : "STANDBILD";
        fetch('/toggle_freeze', {method: 'POST'});
    }

    function saveSnapshot() {
        const data = {
            type: document.getElementById('p_type').value,
            name: document.getElementById('p_name').value,
            pos: document.getElementById('p_pos').value,
            light: document.getElementById('m_light').value,
            pol: document.getElementById('m_pol').value,
            cal: document.getElementById('cal_factor').value
        };
        document.getElementById('status-text').innerText = "Speichere...";
        fetch('/snapshot', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
        }).then(r => r.json()).then(d => {
            document.getElementById('led-mic').className = 'led green';
            document.getElementById('status-text').innerText = "OK: " + d.filename;
            setTimeout(() => { 
                document.getElementById('led-mic').className = 'led orange'; 
                document.getElementById('status-text').innerText = "Bereit für nächste Messung";
            }, 3000);
        });
    }

    function transferX200() {
        document.getElementById('led-x200').className = 'led orange';
        fetch('/x200_transfer', {method: 'POST'}).then(() => {
            document.getElementById('led-x200').className = 'led green';
        });
    }
</script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(html_code)

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if not state["freeze"]:
                success, frame = camera.read()
                if success: state["last_frame"] = frame.copy()
            
            if state["last_frame"] is not None:
                img_display = state["last_frame"].copy()
                if state["freeze"]:
                    img_display = draw_scale_bar_cv2(img_display, 244)
                
                ret, buffer = cv2.imencode('.jpg', img_display)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.04)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_freeze', methods=['POST'])
def toggle_freeze():
    state["freeze"] = not state["freeze"]
    return jsonify(status="ok")

@app.route('/snapshot', methods=['POST'])
def snapshot():
    if state["last_frame"] is not None:
        d = request.json
        ts = datetime.now().strftime("%y%m%d_%H%M")
        fname = f"{ts}_{d['type']}_{d['name']}_{d['pos']}_{d['light']}_{d['pol']}.jpg"
        img = state["last_frame"].copy()
        img = draw_scale_bar_cv2(img, d['cal'])
        cv2.imwrite(os.path.join(OUTPUT_DIR, fname), img)
        with open(os.path.join(LOG_DIR, fname.replace(".jpg", ".json")), "w") as f:
            json.dump(d, f)
        return jsonify(filename=fname)
    return jsonify(error="no frame")

@app.route('/x200_transfer', methods=['POST'])
def x200_transfer():
    time.sleep(0.5)
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)