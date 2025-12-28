import os
import threading
import logging
import cv2
import gc
from flask import Flask, render_template, jsonify, Response

# Import unserer modularen Komponenten
from config import PATHS, LOG_LEVEL, SECRET_KEY
from file_monitor import start_file_monitor
from data_manager import DataManager
from camera_engine import CameraEngine
from sensor_bridge import start_sensor_bridge
from spectrum_processor import SpectrumProcessor # NEU: Der Stellarnet-Kern

# --- SYSTEM-INITIALISIERUNG ---
logging.basicConfig(level=LOG_LEVEL)

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'static'))

app.secret_key = SECRET_KEY
dm = DataManager()
camera = CameraEngine(device_id=0)

# Speicher für das zuletzt gerenderte Spektrum (Cache zur RAM-Schonung)
cached_spectrum = {
    "path": None,
    "image_b64": ""
}

# --- GENERATOREN ---
def generate_mjpeg_stream():
    """Streamt das Kamerabild mit hardware-beschleunigtem Decoding.[3, 4]"""
    while True:
        frame = camera.get_frame()
        if frame is None: break
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- ROUTEN ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def get_status():
    """
    Zentraler API-Endpunkt. Versorgt das Dashboard mit Sensorwerten 
    und dem aktuellen Spektrum-Plot.
    """
    state = dm.get_current_state()
    global cached_spectrum

    # --- SPEKTRUM-LOGIK (Integration AP 3) ---
    # Wir prüfen, ob der Watchdog ein neues Spektrum gemeldet hat
    current_spec_path = state.get("last_spectrum_path")
    
    if current_spec_path and current_spec_path!= cached_spectrum["path"]:
        # Neue Datei erkannt -> Parsen und Plotten
        logging.info(f"Verarbeite neues Spektrum: {os.path.basename(current_spec_path)}")
        
        df = SpectrumProcessor.parse_file(current_spec_path)
        if df is not None:
            # Erzeuge Base64 Plot für das Dashboard
            img_b64 = SpectrumProcessor.plot_to_base64(df, title=os.path.basename(current_spec_path))
            
            # Cache aktualisieren, um doppeltes Plotten zu verhindern
            cached_spectrum["path"] = current_spec_path
            cached_spectrum["image_b64"] = img_b64
            
            # Memory-Hygiene nach rechenintensiver Operation 
            gc.collect()

    # Antwort-Objekt zusammenbauen
    return jsonify({
        "status": "online",
        "temp_display": dm.get_formatted_temp(),
        "hum_display": f"Feuchtigkeit:  {state['humidity']:.1f}%",
        "last_spectrum_img": cached_spectrum["image_b64"],
        "last_spectrum_name": os.path.basename(cached_spectrum["path"]) if cached_spectrum["path"] else "Kein Spektrum"
    })

# --- STARTSEQUENZ ---
if __name__ == '__main__':
    # Hintergrund-Dienste starten
    threading.Thread(target=start_file_monitor, daemon=True).start()
    start_sensor_bridge()
    
    logging.info("LAB-STATION V2: System bereit auf Port 5000")
    
    # Produktionsmodus (debug=False) für 24/7 Stabilität [6, 7]
    app.run(host='0.0.0.0', port=5000, debug=False)