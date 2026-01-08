from flask import Flask, render_template, Response, request, jsonify
import json
from data_manager import DataManager
from lighting import DinoLightControl
from file_monitor import start_watchdog
from config import DIRS
import serial
import time
import os
import subprocess  
import cv2
from datetime import datetime
import threading 

class VideoCamera:
    def __init__(self):
        # Wir nutzen V4L2 (Index 0), da dies in deinem Test stabil lief
        # GStreamer macht hier Probleme, V4L2 ist direkt und sicher.
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        # WICHTIG: MJPG erzwingen (sonst bleibt das Bild bei hoher Auflösung schwarz)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)

        self.lock = threading.Lock()
        self.is_frozen = False
        self.last_frame = None
        
        if not self.cap.isOpened():
            print("ERROR: Kamera konnte nicht via V4L2 gestartet werden.")
        else:
            # --- HARDWARE-INIT ---
            try:
                # Helligkeit & Fokus via V4L2-Befehl setzen (Basis-Einstellungen)
                subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '-c', 'brightness=80'], check=False)
                subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '-c', 'focus_automatic_continuous=0'], check=False)
            except Exception as e:
                print(f"WARNUNG: V4L2-Settings fehlgeschlagen: {e}")
    
    def get_frame(self):
        with self.lock:
            # Falls nicht eingefroren, neuen Frame lesen
            if not self.is_frozen or self.last_frame is None:
                success, frame = self.cap.read()
                if not success:
                    return None
                
                # Overlay direkt auf den Frame zeichnen
                self.last_frame = self._draw_overlay(frame)
            
            # Kodierung für den Flask-Stream
            success, jpeg = cv2.imencode('.jpg', self.last_frame)
            if not success:
                return None
            return jpeg.tobytes()

    def _draw_overlay(self, frame):
        """Zeichnet den 1mm Maßstab fixiert unten rechts."""
        # Parameter: 100px entsprechen 1mm (Kalibrierungswert für AP 8)
        line_width = 100 
        h, w = frame.shape[:2]
        
        # Position: 20px Abstand vom Rand
        x2, y2 = w - 20, h - 20
        x1, y1 = x2 - line_width, y2
        
        # Weiße Linie (2px Dicke)
        cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
        
        # Label: "1mm" exakt zentriert über der Linie
        text = "1mm"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        
        text_x = x1 + (line_width // 2) - (text_size[0] // 2)
        text_y = y1 - 8  # 8px Abstand über der Linie
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
        return frame

    def toggle_freeze(self):
        """Schaltet den Freeze-Modus um und gibt den neuen Status zurück."""
        with self.lock:
            self.is_frozen = not self.is_frozen
            return self.is_frozen

    def take_snapshot(self, filepath):
        """Speichert den aktuellen Frame (inkl. Overlay) auf die Disk."""
        with self.lock:
            if self.last_frame is not None:
                return cv2.imwrite(filepath, self.last_frame)
        return False

    def stop(self):
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()

# Flask Setup
base_path = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(base_path, '..', 'templates')
app = Flask(__name__, template_folder=template_path)

dm = DataManager()
# Wir nutzen die lokale Klasse VideoCamera statt der externen Engine
cam = VideoCamera()

# Start Hardware (VideoCamera hat kein start_stream(), init passiert im __init__)
# cam.start_stream() entfällt hier, da VideoCamera den Stream im Konstruktor öffnet
start_watchdog()

def arduino_bridge():
    """Liest Arduino: T1 H1 T2 H2 Gas (Filtert Textmeldungen lautlos)"""
    ser = None
    while True:
        try:
            if ser is None or not ser.is_open:
                ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
                dm.set_led("clim", "green")
            
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                p = line.split() 
                if len(p) >= 5:
                    try:
                        # Versuch der Konvertierung - klappt nur bei Zahlen
                        # Mapping: T1 (0), T2 (2), RH1 (1), RH2 (3), Gas (4)
                        dm.update_sensors(float(p[0]), float(p[2]), float(p[1]), float(p[3]), int(p[4]))
                    except ValueError:
                        # Alles was keine Zahl ist (Header, Kalibrierung), wird hier ignoriert
                        pass
        except Exception as e:
            print(f"SERIAL ERROR: {e}")
            dm.set_led("clim", "red")
            if ser: ser.close()
            ser = None
            time.sleep(5)

threading.Thread(target=arduino_bridge, daemon=True).start()
### End Hardware Setup ###



@app.route('/')
def index(): return render_template('index.html')

@app.route('/stream')
def stream():
    def event_stream():
        q = dm.listen()
        while True: yield q.get()
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            frame_bytes = cam.get_frame()
            if frame_bytes is not None:
                # Hier dürfen keine Prints oder sleeps stehen, die den Stream bremsen
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Falls kein Bild kommt, eine winzige Pause, um CPU-Last zu vermeiden
                time.sleep(0.01)
                
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

def emit_spectrum_file(filepath):
    try:
        with open(filepath, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        # Wir nutzen jetzt die neue Methode push_event
        msg = f"data: {json.dumps({'type': 'new_spectrum_data', 'payload': {'raw': lines}})}\n\n"
        dm.push_event(msg) 
    except Exception as e:
        print(f"🔴 SSE-Fehler: {e}")


@app.route('/api/freeze', methods=['POST'])
def freeze():
    return jsonify({"frozen": cam.toggle_freeze()})

@app.route('/api/save_data', methods=['POST'])
def save_data():
    data = request.json
    mode = data.get('mode')
    
    # Zeitstempel für Dateinamen
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Metadaten reinigen (Leerzeichen zu Unterstrichen)
    typ = str(data.get('typ', 'R')).strip()
    id_val = str(data.get('id', 'ID')).strip().replace(" ", "_")
    pos = str(data.get('pos', 'POS')).strip().replace(" ", "_")

    # 1. ABSOLUTE PFADE DEFINIEREN (Hardcoded wie gewünscht)
    base_dir = "/home/jetson/inspection_project/data"
    path_micro = os.path.join(base_dir, "mikroskopbilder")
    path_spec  = os.path.join(base_dir, "spektren")
    path_clim  = os.path.join(base_dir, "klimadaten")

    # 2. SICHERSTELLEN, DASS ORDNER EXISTIEREN
    os.makedirs(path_micro, exist_ok=True)
    os.makedirs(path_spec, exist_ok=True)
    os.makedirs(path_clim, exist_ok=True)

    try:
        # --- FALL A: MIKROSKOP ---
        if mode == 'micro':
            # Format: YYYYMMDD_HHMMSS_Typ_ID_Pos_Licht_Pol.jpg
            licht = data.get('licht', 'R')
            pol = data.get('pol', 'Off')
            fn = f"{ts}_{typ}_{id_val}_{pos}_{licht}_{pol}.jpg"
            full_path = os.path.join(path_micro, fn)
            
            # Snapshot auslösen
            if cam.take_snapshot(full_path): 
                print(f"✅ BILD GESPEICHERT: {full_path}")
                return jsonify({"status": "success", "file": fn, "path": full_path})
            else:
                print("❌ FEHLER: Kamera konnte Bild nicht speichern.")
                return jsonify({"status": "error", "message": "Kamerafehler"}), 500

        # --- FALL B: SPEKTRUM (VOLLSTÄNDIG) ---
        elif mode == 'spec':
            # 1. Dateinamen generieren (Mapping aus dem Frontend)
            spec_mode = data.get('spec_mode', 'Abs')
            fn = f"{ts}_{typ}_{id_val}_{pos}_{spec_mode}.abs"
            full_path = os.path.join(path_spec, fn)
            
            # 2. DATEI SCHREIBEN
            # Wir schreiben hier die Messdaten in die Datei.
            # WICHTIG: Der Parser im Browser braucht pro Zeile: "NM WERT"
            with open(full_path, 'w') as f:
                f.write(f"Header: {ts} {typ} {id_val}\n") 
                f.write("204.0 1.000E-01\n") # Testpunkt 1: Wellenlänge <Leertaste> Wert
                f.write("204.75 1.200E-01\n") # Testpunkt 2 (0.75nm Schrittweite)
                # Später: Hier schreibt die Hardware 1844 Zeilen rein.
            
            # 3. DER ENTSCHEIDENDE SCHRITT: DATEN AN STREAM SENDEN
            # Diese Funktion liest die gerade gespeicherte Datei sofort wieder ein
            # und schickt sie über den DataManager an den Browser-Graphen.
            # Ohne diesen Aufruf bleibt die Anzeige im Frontend "tot".
            emit_spectrum_file(full_path)
            
            print(f"✅ ERFOLG: Spektrum gespeichert unter {fn} und an UI gesendet.")
            
            # 4. ANTWORT AN DAS FRONTEND (Bestätigung für den Button-Klick)
            return jsonify({
                "status": "success", 
                "info": "Datei gespeichert und Stream ausgelöst",
                "file": fn
            })

        # --- FALL C: KLIMA ---
        elif mode == 'clim':
            # Format: LOG_Typ_ID_Pos.csv (Append Mode)
            fn = f"LOG_{typ}_{id_val}.csv"
            full_path = os.path.join(path_clim, fn)
            
            # Aktuelle Werte aus dem DataManager holen
            vals = dm.current_values
            line = f"{ts},{vals.get('t1',0)},{vals.get('t2',0)},{vals.get('rh1',0)},{vals.get('rh2',0)},{vals.get('gas',0)}\n"
            
            with open(full_path, 'a') as f: # 'a' für append (anhängen)
                f.write(line)
                
            print(f"✅ KLIMA LOG GESCHRIEBEN: {full_path}")
            return jsonify({"status": "success", "file": fn})

    except Exception as e:
        print(f"❌ SYSTEM FEHLER BEIM SPEICHERN: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "error", "message": "Unbekannter Modus"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)