import cv2
import time
import os

# --- KONFIGURATION ---
save_folder = "/home/jetson/inspection_project/data/bilder"
filename = "test_aufnahme_v4l2.jpg"
full_path = os.path.join(save_folder, filename)

print(f"--- MIKROSKOP TEST (V4L2 Modus) ---")

# 1. Kamera öffnen mit V4L2 Treiber (WICHTIG für USB!)
# Index 0 ist meistens richtig. Falls nicht, testen wir gleich Index 1.
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

# 2. Format auf MJPG zwingen (Verhindert Daten-Stau am USB)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

# 3. Auflösung setzen
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024)

if not cap.isOpened():
    print("FEHLER: Kamera konnte nicht geöffnet werden.")
else:
    print("Kamera verbunden. Warte auf Belichtung...")
    time.sleep(2)  # Etwas länger warten
    
    # 4. Bild holen
    ret, frame = cap.read()
    
    if ret:
        cv2.imwrite(full_path, frame)
        if os.path.exists(full_path):
            print(f"✅ ERFOLG: Bild gespeichert unter:\n{full_path}")
        else:
            print("❌ FEHLER: Schreibrechte fehlen?")
    else:
        print("❌ FEHLER: Das gelesene Bild war leer.")

cap.release()
