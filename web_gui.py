import cv2
import os
import time
import re
from datetime import datetime
from flask import Flask, render_template_string, Response, request, jsonify

app = Flask(__name__)

OUTPUT_DIR = os.path.expanduser('~/inspection_project/data/bilder/')
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

# --- LEGENDE ---
readme_content = """ANLEITUNG
Befehle: 'mikroskop' (Start), 'bilder' (Ansehen)

MASSSTAB & KALIBRIERUNG:
1. Zoom-Wert vom Rädchen ins Feld 'Zoom' eintragen.
2. Faktor 2.44 ist Standard.
   -> Falls der Balken nicht stimmt: Faktor im Feld anpassen, bis es passt.

ABKUERZUNGEN:
TYP: B=Bohr, W=Wisch, M=Mat, Ref=Ref
POL: P0=Aus, P1=An
LICHT: R=Ring, C=Coax, S=Side
"""
with open(os.path.join(OUTPUT_DIR, "LEGENDE.txt"), "w") as f: f.write(readme_content)

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

# --- PYTHON MASSSTAB (Variabler Faktor) ---
def draw_scale_bar_cv2(image, magnification, factor):
    try:
        mag = float(magnification)
        fact = float(factor)
        if mag <= 0 or fact <= 0: return image
        
        # Berechnung mit dem variablen Faktor
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
    <title>Datenerfassung</title>
    <style>
        body { background-color: #121212; color: #ddd; font-family: sans-serif; padding: 10px; }
        .main { display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }
        .video-box { border: 2px solid #444; position: relative; max-width: 100%; }
        .controls { 
            background: #1e1e1e; padding: 15px; border-radius: 8px; width: 300px; 
            position: sticky; top: 10px; height: fit-content; border: 1px solid #333;
        }
        h2 { border-bottom: 1px solid #555; padding-bottom: 5px; margin: 0 0 10px 0; color: #fff; font-size: 18px;}
        label { display: block; margin-top: 8px; color: #aaa; font-size: 12px; font-weight: bold; }
        select, input[type="text"], input[type="number"] { 
            width: 100%; padding: 6px; margin-top: 2px; background: #333; color: white; border: 1px solid #555; box-sizing: border-box; font-size: 14px;
        }
        .radio-box { background: #2a2a2a; padding: 5px; margin-top: 2px; border-radius: 4px; font-size: 12px;}
        .radio-box label { margin-right: 8px; cursor: pointer; color: #fff; font-weight: normal; }
        .btn-save { width: 100%; padding: 12px; margin-top: 15px; background: #28a745; color: white; border: none; font-size: 16px; font-weight: bold; cursor: pointer; border-radius: 6px; }
        .btn-save:hover { background: #218838; }
        .btn-freeze { width: 100%; padding: 8px; margin-top: 10px; background: #ffc107; color: #000; border: none; font-size: 12px; font-weight: bold; cursor: pointer; border-radius: 6px; }
        #status { margin-top: 10px; font-family: monospace; color: #0f0; word-break: break-all; font-size: 11px; }
        #freeze-canvas { display: none; width: 100%; }
        .important-input { border: 2px solid #ffc107 !important; background: #222 !important; }
        .calib-input { border: 1px solid #555 !important; background: #111 !important; color: #888 !important; }
    </style>
</head>
<body>
    <div class="main">
        <div class="controls">
            <h2>Steuerung</h2>
            
            <label style="color: #ffc107;">1. Zoom-Faktor (Massstab):</label>
            <input type="number" id="zoom" value="50" class="important-input" placeholder="Wert vom Rädchen">

            <label>Kalibrier-Faktor (Setup):</label>
            <input type="number" step="0.01" id="calib_factor" value="2.44" class="calib-input">

            <label>2. Bezeichnung:</label>
            <input type="text" id="sample_name" value="Probe1">
            <label>3. Ort / Position:</label>
            <input type="text" id="location" value="Pos1">
            <label>4. Probenart:</label>
            <select id="sample_type">
                <option value="B">Bohrprobe (B)</option>
                <option value="W">Wischprobe (W)</option>
                <option value="M">Material (M)</option>
                <option value="Ref">Referenz</option>
            </select>
            <label>5. Settings:</label>
            <div class="radio-box">
                Pol: <label><input type="radio" name="pol" value="P0" checked> Aus</label> <label><input type="radio" name="pol" value="P1"> An</label><br>
                Licht: <label><input type="radio" name="light" value="R" checked> Ring</label> <label><input type="radio" name="light" value="C"> Coax</label> <label><input type="radio" name="light" value="S"> Side</label>
            </div>

            <button class="btn-freeze" id="btn-freeze" onclick="toggleFreeze()">STANDBILD (Vorschau)</button>
            <button class="btn-save" onclick="snap()">SPEICHERN</button>
            <div id="status">Bereit.</div>
        </div>
        <div class="video-box">
            <img id="live-img" src="{{ url_for('video_feed') }}" width="100%">
            <canvas id="freeze-canvas"></canvas>
        </div>
    </div>
    <script>
        let isFrozen = false;
        
        function drawScaleBarJS(ctx, width, height) {
            let zoomVal = parseFloat(document.getElementById('zoom').value);
            let currentFactor = parseFloat(document.getElementById('calib_factor').value);
            
            if(!zoomVal || zoomVal <= 0) return;
            if(!currentFactor || currentFactor <= 0) currentFactor = 2.44;

            let pixelsPerMM = zoomVal * currentFactor;
            let barLenMM = 1.0; let label = "1 mm";
            
            if (zoomVal < 100) { barLenMM = 1.0; label = "1 mm"; }
            else if (zoomVal < 400) { barLenMM = 0.5; label = "0.5 mm"; }
            else { barLenMM = 0.1; label = "0.1 mm"; }

            let barPx = pixelsPerMM * barLenMM;
            let x = width - barPx - 50;
            let y = height - 50;

            ctx.lineCap = "square";
            ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + barPx, y);
            ctx.lineWidth = 6; ctx.strokeStyle = "black"; ctx.stroke();
            ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + barPx, y);
            ctx.lineWidth = 2; ctx.strokeStyle = "white"; ctx.stroke();

            ctx.font = "bold 24px sans-serif";
            ctx.fillStyle = "black"; ctx.fillText(label, x, y - 15);
            ctx.fillStyle = "white"; ctx.fillText(label, x, y - 15);
        }

        function toggleFreeze() {
            let img = document.getElementById('live-img');
            let cvs = document.getElementById('freeze-canvas');
            let btn = document.getElementById('btn-freeze');
            let ctx = cvs.getContext('2d');

            if (!isFrozen) {
                cvs.width = img.width; cvs.height = img.height;
                ctx.drawImage(img, 0, 0, cvs.width, cvs.height);
                drawScaleBarJS(ctx, cvs.width, cvs.height);
                img.style.display = 'none'; cvs.style.display = 'block';
                btn.innerText = "WEITER (LIVE)"; btn.style.background = "#fff";
                isFrozen = true;
            } else {
                img.style.display = 'block'; cvs.style.display = 'none';
                btn.innerText = "STANDBILD (Vorschau)"; btn.style.background = "#ffc107";
                isFrozen = false;
            }
        }

        function snap() {
            let btn = document.querySelector('.btn-save');
            btn.style.background = "white"; setTimeout(() => btn.style.background = "#28a745", 150);
            
            let data = {
                type: document.getElementById('sample_type').value,
                name: document.getElementById('sample_name').value,
                loc: document.getElementById('location').value,
                zoom: document.getElementById('zoom').value,
                factor: document.getElementById('calib_factor').value,
                pol: document.querySelector('input[name="pol"]:checked').value,
                light: document.querySelector('input[name="light"]:checked').value
            };
            if(data.name.trim() === "") { alert("Bezeichnung fehlt!"); return; }
            if(!data.zoom || data.zoom == 0) { alert("Zoom fehlt!"); return; }

            fetch('/snapshot', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
            })
            .then(r => r.json()).then(d => { document.getElementById('status').innerText = "OK: " + d.filename; })
            .catch(e => { document.getElementById('status').innerText = "Fehler!"; });
        }
    </script>
</body>
</html>
"""

# --- DIESEN TEIL HATTE ICH VERGESSEN: ---

def generate_frames():
    global camera
    while True:
        if camera is None or not camera.isOpened(): time.sleep(2); init_camera()
        if camera and camera.isOpened():
            success, frame = camera.read()
            if success:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else: camera.release()

@app.route('/')
def index(): return render_template_string(html_code)

@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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
            filename = f"{ts}_{d['type']}_{s_name}_{s_loc}_{d['pol']}_{d['light']}.jpg"
            
            # Hier nutzen wir jetzt den Faktor, der aus der Webseite kommt
            calib_factor = d.get('factor', 2.44)
            
            frame_with_scale = draw_scale_bar_cv2(frame, d['zoom'], calib_factor)
            
            cv2.imwrite(os.path.join(OUTPUT_DIR, filename), frame_with_scale)
            print(f"Saved: {filename}")
            return jsonify(filename=filename)
    return jsonify(error="Error")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
