import cv2  # OpenCV: Bibliothek für Bildverarbeitung (Kamera lesen, Linien zeichnen)
import os   # OS: Betriebssystem-Funktionen (Ordner erstellen, Pfade finden)
import time # Time: Für Pausen (Sleep) und Zeitmessung
import re   # Regex: Reguläre Ausdrücke (hier aktuell ungenutzt, aber oft für Textanalyse)
import json # JSON: Zum Speichern der Metadaten (Text-Dateien für Messwerte)
from datetime import datetime # Datetime: Um Zeitstempel für Dateinamen zu erzeugen
from flask import Flask, render_template_string, Response, request, jsonify # Flask: Der Webserver

# Initialisierung der Flask-App
app = Flask(__name__)

# --- KONFIGURATION DER PFADE ---
# Wir nutzen expanduser, damit das Home-Verzeichnis (~) automatisch gefunden wird
BASE_DIR = os.path.expanduser('~/inspection_project/data/')
OUTPUT_DIR = os.path.join(BASE_DIR, 'bilder/') # Hier landen die JPGs
LOG_DIR = os.path.join(BASE_DIR, 'logs/')     # Hier landen die JSON-Daten

# Prüfen, ob Ordner existieren. Wenn nicht, werden sie erstellt.
for d in [OUTPUT_DIR, LOG_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- GLOBALE VARIABLEN ---
camera = None

# Der "State" speichert den Zustand der App, auf den alle Funktionen zugreifen können.
# Das ist wichtig, damit Webserver und Kamera-Schleife Daten austauschen können.
state = {
    "freeze": False,        # Ist das Bild gerade eingefroren?
    "last_frame": None,     # Speichert das letzte gelesene Bild (für Snapshots/Freeze)
    "cal_factor": 244       # Kalibrierfaktor (Pixel pro 1 mm). Startwert: 244
}

# --- KAMERA INITIALISIERUNG ---
def init_camera():
    global camera
    # Falls schon eine Kamera offen ist, schließen wir sie zuerst
    if camera is not None: camera.release()
    
    # Wir probieren die Kamera-Indizes 0, 1 und 2 durch (manchmal steckt USB an Port 1)
    for idx in [0, 1, 2]:
        # V4L2 ist der Videotreiber für Linux
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        
        # Einstellungen für bessere Performance (MJPG ist schneller als Raw)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Auflösung Breite
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024) # Auflösung Höhe
        
        # Testen, ob die Kamera wirklich ein Bild liefert
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                camera = cap
                return True # Erfolgreich verbunden
            else: 
                cap.release() # Wenn kein Bild, Kamera wieder freigeben
    return False

# Kamera beim Start sofort initialisieren
init_camera()

# --- HILFSFUNKTION: MASSSTABSBALKEN ZEICHNEN ---
def draw_scale_bar_cv2(image, cal_factor):
    """
    Zeichnet eine Linie, die genau 1mm entspricht, basierend auf dem cal_factor.
    Wird nur aufgerufen, wenn das Bild eingefroren ist.
    """
    try:
        f = float(cal_factor)
        h, w = image.shape[:2] # Höhe und Breite des Bildes ermitteln
        px_len = int(f)        # Der Faktor entspricht genau der Pixelanzahl für 1mm
        
        # Fehlerabfang: Wenn Länge unsinnig ist, nichts tun
        if px_len <= 0: return image 
        
        # Koordinaten für den Strich (Unten Links)
        x1, y = 50, h - 60  # Startpunkt
        x2 = x1 + px_len    # Endpunkt (Start + Länge)
        
        # 1. Dicke schwarze Linie (als Hintergrund/Rand)
        cv2.line(image, (x1, y), (x2, y), (0, 0, 0), 4)
        # 2. Dünnere weiße Linie (darüber)
        cv2.line(image, (x1, y), (x2, y), (255, 255, 255), 2)
        
        # Kleine vertikale Striche am Anfang und Ende (Begrenzer)
        cv2.line(image, (x1, y-5), (x1, y+5), (255, 255, 255), 2)
        cv2.line(image, (x2, y-5), (x2, y+5), (255, 255, 255), 2)
        
        # Text "1 mm" darüber schreiben
        cv2.putText(image, "1 mm", (x1, y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        
        return image
    except: 
        # Falls irgendwas schief geht, gib das Originalbild zurück, damit das Programm nicht abstürzt
        return image

# --- HTML & GUI ---
# Das HTML ist direkt hier als String hinterlegt.
html_code = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Jetson Control Center</title>
    <style>
        /* --- CSS STYLING --- */
        /* 'border-box' sorgt dafür, dass Padding die Box nicht vergrößert */
        * { box-sizing: border-box; }
        
        body { 
            background: #121212; /* Dunkler Hintergrund */
            color: #ddd;         /* Helle Schrift */
            font-family: 'Segoe UI', sans-serif; 
            margin: 0; padding: 5px; 
            height: 100vh; width: 100vw; 
            overflow: hidden;    /* Scrollbalken verhindern */
            display: flex; flex-direction: column; /* Alles untereinander anordnen */
        }

        /* Obere Leiste für Status-LEDs */
        .status-bar { 
            display: flex; gap: 15px; 
            background: #1e1e1e; 
            padding: 4px 10px; 
            border-bottom: 2px solid #333; 
            margin-bottom: 5px; border-radius: 5px; 
            flex-shrink: 0; /* Darf nicht kleiner gedrückt werden */
            height: 30px; align-items: center;
        }

        /* LED Stile */
        .led-group { display: flex; align-items: center; gap: 6px; font-size: 10px; }
        .led { width: 10px; height: 10px; border-radius: 50%; background: #333; }
        .orange { background: #ffa500; box-shadow: 0 0 6px #ffa500; }
        .green { background: #28a745; box-shadow: 0 0 6px #28a745; }
        
        /* Hauptbereich: Links Sidebar, Rechts Bild */
        .wrapper { display: flex; gap: 8px; flex-grow: 1; min-height: 0; }
        
        /* --- SEITENLEISTE --- */
        /* Breite fest auf 280px eingestellt */
        .sidebar { width: 280px; display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
        
        /* Module sind die grauen Boxen in der Sidebar */
        .module { background: #1e1e1e; padding: 10px; border-radius: 6px; border: 1px solid #333; }
        .module-fill { flex-grow: 1; } /* Füllt den leeren Platz auf */
        
        h3 { color: #00adb5; font-size: 14px; margin: 0 0 6px 0; border-bottom: 1px dotted #444; padding-bottom: 2px; }
        
        /* Eingabefelder Styling */
        label { display: block; margin-top: 6px; font-size: 11px; color: #888; font-weight: bold; }
        select, input { 
            width: 100%; padding: 4px; margin-top: 2px; background: #2a2a2a; 
            color: white; border: 1px solid #444; border-radius: 3px; 
            box-sizing: border-box; font-size: 12px; height: 26px;
        }
        
        /* --- BILD BEREICH --- */
        .content { 
            flex-grow: 1; display: flex; justify-content: center; align-items: center; 
            background: #121212; /* Gleiche Farbe wie Body -> Keine schwarzen Ränder sichtbar */
            border-radius: 6px; overflow: hidden; border: none;
            min-height: 0;
        }
        
        /* Das eigentliche Videobild */
        #live-img { 
            max-width: 100%; max-height: 100%; 
            object-fit: contain; /* Bild behält Seitenverhältnis */
            display: block;
        }
        
        /* Buttons */
        .action-area { margin-top: auto; display: flex; flex-direction: column; gap: 5px; }
        .btn-freeze { background: #444; color: white; border: none; padding: 10px; cursor: pointer; font-weight: bold; border-radius: 4px; width: 100%; font-size: 12px; }
        .btn-freeze.active { background: #d9534f; } /* Rot wenn aktiv */
        .btn-save { background: #28a745; color: white; border: none; padding: 12px; font-size: 14px; font-weight: bold; cursor: pointer; border-radius: 4px; width: 100%; }
        .btn-x200 { background: #007bff; color: white; border: none; padding: 8px; border-radius: 4px; cursor: pointer; margin-top: 5px; width: 100%; font-size: 11px; }
        
        #status-text { font-size: 11px; color: #00ff00; font-family: monospace; text-align: center; min-height: 14px; margin-bottom: 2px; }
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
            
            <label>Kalibrierung (px pro 1 mm)</label>
            <input type="number" id="cal_factor" value="244" oninput="updateCal()">
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
    // JavaScript Code (Läuft im Browser)
    
    let frozen = false;
    
    // Funktion: Kalibrierwert sofort an Python senden
    function updateCal() {
        const val = document.getElementById('cal_factor').value;
        fetch('/set_cal', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cal: val})
        });
    }

    // Funktion: Standbild ein/ausschalten
    function toggleFreeze() {
        frozen = !frozen;
        const btn = document.getElementById('freeze-btn');
        btn.classList.toggle('active', frozen); // Macht Button rot
        btn.innerText = frozen ? "STANDBILD AKTIV" : "STANDBILD";
        fetch('/toggle_freeze', {method: 'POST'}); // Python informieren
    }

    // Funktion: Bild und Daten speichern
    function saveSnapshot() {
        // Alle Daten aus den Eingabefeldern sammeln
        const data = {
            type: document.getElementById('p_type').value,
            name: document.getElementById('p_name').value,
            pos: document.getElementById('p_pos').value,
            light: document.getElementById('m_light').value,
            pol: document.getElementById('m_pol').value,
            cal: document.getElementById('cal_factor').value
        };
        
        document.getElementById('status-text').innerText = "Speichere...";
        
        // Senden an Python Route '/snapshot'
        fetch('/snapshot', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
        }).then(r => r.json()).then(d => {
            // Erfolg: LED kurz grün machen und Text anzeigen
            document.getElementById('led-mic').className = 'led green';
            document.getElementById('status-text').innerText = "OK: " + d.filename;
            setTimeout(() => { 
                document.getElementById('led-mic').className = 'led orange'; 
                document.getElementById('status-text').innerText = "Bereit für nächste Messung";
            }, 3000);
        });
    }

    // Dummy-Funktion für Spektrometer (Placeholder)
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

# --- FLASK ROUTEN (BACKEND) ---

# 1. Startseite: Lädt den HTML Code
@app.route('/')
def index(): return render_template_string(html_code)

# 2. Kalibrierung empfangen: Wird aufgerufen, wenn man im Textfeld tippt
@app.route('/set_cal', methods=['POST'])
def set_cal():
    try:
        val = float(request.json['cal'])
        state['cal_factor'] = val # Speichere neuen Wert global
        return jsonify(success=True)
    except:
        return jsonify(success=False)

# 3. Video Stream: Das Herzstück für das Live-Bild
@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            # Wenn NICHT eingefroren -> Neues Bild von Kamera holen
            if not state["freeze"]:
                success, frame = camera.read()
                if success: state["last_frame"] = frame.copy()
            
            # Bild verarbeiten und senden
            if state["last_frame"] is not None:
                img_display = state["last_frame"].copy()
                
                # Wenn eingefroren -> Zeichne Maßstabsbalken (mit aktuellem Faktor!)
                if state["freeze"]:
                    img_display = draw_scale_bar_cv2(img_display, state["cal_factor"])
                
                # Bild zu JPG komprimieren
                ret, buffer = cv2.imencode('.jpg', img_display)
                
                # Als MJPEG Stream senden (das versteht der Browser als Video)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Kurze Pause um CPU zu schonen (ca. 25 FPS)
            time.sleep(0.04)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 4. Freeze umschalten (wird vom Button geklickt)
@app.route('/toggle_freeze', methods=['POST'])
def toggle_freeze():
    state["freeze"] = not state["freeze"]
    return jsonify(status="ok")

# 5. Speichern: Legt Bild und JSON ab
@app.route('/snapshot', methods=['POST'])
def snapshot():
    if state["last_frame"] is not None:
        d = request.json # Die Daten vom Browser
        
        # Zeitstempel generieren (z.B. 251224_1430)
        ts = datetime.now().strftime("%y%m%d_%H%M")
        
        # Dateinamen zusammenbauen
        fname = f"{ts}_{d['type']}_{d['name']}_{d['pos']}_{d['light']}_{d['pol']}.jpg"
        
        # Bild vorbereiten
        img = state["last_frame"].copy()
        # Maßstab dauerhaft ins gespeicherte Bild brennen
        img = draw_scale_bar_cv2(img, d['cal'])
        
        # Speichern
        cv2.imwrite(os.path.join(OUTPUT_DIR, fname), img)
        
        # Metadaten als JSON speichern
        with open(os.path.join(LOG_DIR, fname.replace(".jpg", ".json")), "w") as f:
            json.dump(d, f)
            
        return jsonify(filename=fname)
    return jsonify(error="no frame")

# 6. Spektrometer Transfer (Dummy)
@app.route('/x200_transfer', methods=['POST'])
def x200_transfer():
    time.sleep(0.5)
    return jsonify(success=True)

# --- HAUPTPROGRAMM START ---
if __name__ == '__main__':
    # Startet den Server auf Port 5000, erreichbar von überall im Netzwerk (0.0.0.0)
    app.run(host='0.0.0.0', port=5000, threaded=True)