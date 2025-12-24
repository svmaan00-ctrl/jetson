import cv2
import os
import time
import re
from datetime import datetime
from flask import Flask, render_template_string, Response, request, jsonify

app = Flask(__name__)

# Pfade für Bilder und Spektren
OUTPUT_DIR = os.path.expanduser('~/inspection_project/data/bilder/')
SPEKTREN_DIR = os.path.expanduser('~/inspection_project/data/spektren/')
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
if not os.path.exists(SPEKTREN_DIR): os.makedirs(SPEKTREN_DIR)

camera = None

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
            if ret and frame is not None and frame.size > 0:
                camera = cap
                return True
            else: cap.release()
    return False

init_camera()

def draw_scale_bar_cv2(image, magnification, factor):
    try:
        mag = float(magnification)
        fact = float(factor)
        if mag <= 0 or fact <= 0: return image
        pixels_per_mm = mag * fact
        if mag < 100: bar_len = 1.0; txt = "1 mm"
        elif mag < 400: bar_len = 0.5; txt = "0.5 mm"
        else: bar_len = 0.1; txt = "0.1 mm"
        px_len = int(pixels_per_mm * bar_len)
        h, w = image.shape[:2]
        x = w - px_len - 50; y = h - 50
        cv2.line(image, (x, y), (x + px_len, y), (0,0,0), 6)
        cv2.line(image, (x, y), (x + px_len, y), (255,255,255), 2)
        cv2.putText(image, txt, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 4)
        cv2.putText(image, txt, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 1)
        return image
    except: return image

html_code = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Jetson Inspection Center</title>
    <style>
        body { background-color: #121212; color: #ddd; font-family: sans-serif; padding: 10px; }
        .main { display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }
        .video-box { border: 2px solid #444; position: relative; flex: 1; min-width: 600px; }
        .controls { 
            background: #1e1e1e; padding: 15px; border-radius: 8px; width: 320px; 
            border: 1px solid #333;
        }
        .status-panel {
            background: #111; padding: 10px; margin-top: 15px; border-radius: 6px; border: 1px solid #444;
        }
        .status-item { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; }
        .led { width: 10px; height: 10px; border-radius: 50%; display: inline-block; background: #333; }
        .led-green { background: #28a745; box-shadow: 0 0 5px #28a745; }
        .led-yellow { background: #ffc107; box-shadow: 0 0 5px #ffc107; }
        
        h2 { border-bottom: 1px solid #555; padding-bottom: 5px; margin: 15px 0 10px 0; color: #fff; font-size: 16px;}
        h2:first-child { margin-top: 0; }
        label { display: block; margin-top: 8px; color: #aaa; font-size: 11px; font-weight: bold; }
        select, input[type="text"], input[type="number"] { 
            width: 100%; padding: 6px; margin-top: 2px; background: #333; color: white; border: 1px solid #555; box-sizing: border-box; font-size: 13px;
        }
        .radio-box { background: #2a2a2a; padding: 8px; margin-top: 4px; border-radius: 4px; font-size: 12px; border: 1px solid #444; }
        .btn-save { width: 100%; padding: 12px; margin-top: 15px; background: #28a745; color: white; border: none; font-size: 16px; font-weight: bold; cursor: pointer; border-radius: 6px; }
        #status { margin-top: 10px; font-family: monospace; color: #0f0; font-size: 11px; }
    </style>
</head>
<body>
    <div class="main">
        <div class="controls">
            <h2>1. System Status</h2>
            <div class="status-panel">
                <div class="status-item"><span>Mikroskop (USB)</span> <div class="led led-green"></div></div>
                <div class="status-item"><span>SSH Tunnel</span> <div class="led led-green"></div></div>
                <div class="status-item"><span>X200 UV-Vis</span> <div id="led-x200" class="led"></div></div>
            </div>

            <h2>2. Proben-Info</h2>
            <label>Bezeichnung:</label>
            <input type="text" id="sample_name" value="Probe_01">
            <label>Ort / Position:</label>
            <input type="text" id="location" value="Zentrum">
            <label>Probenart:</label>
            <select id="sample_type">
                <option value="B">Bohrprobe (B)</option>
                <option value="W">Wischprobe (W)</option>
                <option value="M">Material (M)</option>
                <option value="Ref">Referenz</option>
            </select>

            <h2>3. Mikroskop</h2>
            <label style="color: #ffc107;">Zoom (Rädchen):</label>
            <input type="number" id="zoom" value="50">
            <div class="radio-box">
                Licht: <label><input type="radio" name="light" value="R" checked> R</label> 
                       <label><input type="radio" name="light" value="C"> C</label> 
                       <label><input type="radio" name="light" value="S"> S</label> | 
                Pol: <label><input type="radio" name="pol" value="P0" checked> Off</label> 
                     <label><input type="radio" name="pol" value="P1"> On</label>
            </div>

            <h2>4. Spektrometer (X200)</h2>
            <div class="radio-box">
                Modus: <label><input type="radio" name="mode" value="AU" checked> AU</label> 
                       <label><input type="radio" name="mode" value="TR"> %T:R</label> 
                       <label><input type="radio" name="mode" value="Scope"> Scope</label>
            </div>

            <button class="btn-save" onclick="snap()">MESSUNG SPEICHERN</button>
            <div id="status">Bereit.</div>
        </div>

        <div class="video-box">
            <img id="live-img" src="{{ url_for('video_feed') }}" width="100%">
        </div>
    </div>

    <script>
        function snap() {
            let data = {
                type: document.getElementById('sample_type').value,
                name: document.getElementById('sample_name').value,
                loc: document.getElementById('location').value,
                zoom: document.getElementById('zoom').value,
                pol: document.querySelector('input[name="pol"]:checked').value,
                light: document.querySelector('input[name="light"]:checked').value,
                mode: document.querySelector('input[name="mode"]:checked').value,
                factor: 2.44
            };

            document.getElementById('led-x200').className = 'led led-yellow';
            
            fetch('/snapshot', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
            })
            .then(r => r.json()).then(d => { 
                document.getElementById('status').innerText = "Gespeichert: " + d.filename;
                setTimeout(() => { document.getElementById('led-x200').className = 'led'; }, 3000);
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
    def generate_frames():
        global camera
        while True:
            if camera is None or not camera.isOpened(): time.sleep(2); init_camera()
            if camera and camera.isOpened():
                success, frame = camera.read()
                if success:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/snapshot', methods=['POST'])
def snapshot():
    global camera
    if camera and camera.isOpened():
        ret, frame = camera.read()
        if ret:
            d = request.json
            s_name = re.sub(r'[^a-zA-Z0-9_-]', '', d['name'])
            s_loc = re.sub(r'[^a-zA-Z0-9_-]', '', d['loc'])
            ts = datetime.now().strftime("%y%m%d_%H%M%S")
            
            # Bild Name (MIT ZOOM)
            img_file = f"{ts}_{d['type']}_{s_name}_{s_loc}_{d['zoom']}x_{d['pol']}_{d['light']}.jpg"
            # Spektrum Name (OHNE ZOOM)
            spec_ref = f"{ts}_{d['type']}_{s_name}_{s_loc}_{d['mode']}.txt"
            
            frame_with_scale = draw_scale_bar_cv2(frame, d['zoom'], d.get('factor', 2.44))
            cv2.imwrite(os.path.join(OUTPUT_DIR, img_file), frame_with_scale)
            
            # Erstellt eine leere Info-Datei für die Spektren-Zuordnung
            with open(os.path.join(SPEKTREN_DIR, spec_ref), "w") as f:
                f.write(f"Warte auf X200 Datei für: {img_file}")

            return jsonify(filename=img_file)
    return jsonify(error="Error")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)