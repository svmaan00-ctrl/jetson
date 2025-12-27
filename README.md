📋 Projekt-Dokumentation: Lab_station_v1 ➔ v2 Upgrade
Version: v1.5 (Transition to v2)

Status: AP 1 Abgeschlossen / Entwicklung aktiv

Entwickler: Lab-Station-Experte (Jetson Dev)

1. System-Übersicht
Kombiniertes Inspektionssystem (Mikroskopie & UV-VIS Spektrometrie) auf einem Jetson Nano/Xavier.

Hardware: Jetson Board, USB-Kamera (V4L2, MJPG), Arduino (Sensor-Bridge via Serial).

Architektur: Modularer Aufbau. Quellcode in /src/, Daten in /data/.

2. Verzeichnisstruktur (Ist-Zustand)
Plaintext

/home/jetson/inspection_project/
├── README.md                # Projekt-Dokumentation
├── src/                     # Quellcode & Frontend
│   ├── lab_station_v1.py    # Hauptprogramm (Backend)
│   ├── index.html           # Benutzeroberfläche (Frontend)
│   ├── config.py            # System-Konfiguration
│   └── spec_watcher.py      # Hintergrunddienst für Spektrometer-Daten
└── data/                    # Zentraler Datenspeicher
    ├── bilder/              # Assets
    ├── mikroskopbilder/     # Aktuelle JPG-Aufnahmen
    ├── spektren/            # Aktuelle CSV/Txt Spektrendaten
    ├── logs/                # Systemlogs
    ├── sensordaten/         # Arduino-Logs
    ├── x200_rohdaten_eingang/    # [NEU] Watch-Folder für WinSCP
    ├── x200_spektren_ergebnisse/ # [NEU] Prozessierte Plots
    ├── archivierte_spektren/     # [NEU] Archiv Spektren
    └── archivierte_mikroskopbilder/ # [NEU] Archiv Bilder
3. System-Steuerung (Aliase aus .bashrc)
# --- JETSON OPTIMIERUNG & PROJEKT ---
alias monitoraus='sudo systemctl set-default multi-user.target && sudo reboot'

alias monitoran='sudo systemctl set-default graphical.target && sudo reboot'

# Projekt-Steuerung (Industrie-Standard)
alias systemstart="python3 ~/inspection_project/src/spec_watcher.py & python3 ~/inspection_project/src/lab_station_v1.py"

alias systemreset="fuser -k 5000/tcp; pkill -f spec_watcher.py; pkill -f lab_station_v1.py; sudo udevadm trigger"

alias systemaus='sudo shutdown -h now'

alias systemreboot='sudo reboot'

# Daten-Zugriff
alias mikroskopbilder='ls -l ~/inspection_project/data/mikroskopbilder/'

alias spektren='ls -l ~/inspection_project/data/spektren/'

# System-Check
alias ramcheck='ps -e -o rss,command | grep node | awk "{print \$1/1024 \" MB\", \$2}" | sort -nr | head -n 10'

# Kamera-Informationen
alias caminfo='v4l2-ctl --list-formats-ext -d /dev/video0'

4. Vollständiger Projektplan: Lab_station_v2 Upgrade

"AP 1 ist in Arbeit"
Ordnerstruktur steht, pandas, matplotlib wurde installiert und schreibrechte vergeben

 📦 AP 1: Infrastruktur & Environment Setup
Ziel: Vorbereitung der Umgebung auf dem Jetson, um Schreibkonflikte und Pfad-Fehler zu vermeiden.

[x] Verzeichnisstruktur härten:

[x] Anlegen von /home/jetson/inspection_project/data/x200_rohdaten_eingang/ (Lese- & Schreibrechte für Flask und WinSCP-User).

[x] Anlegen von /home/jetson/inspection_project/data/archivierte_spektren/.

[x] Anlegen von /home/jetson/inspection_project/data/archivierte_mikroskopbilder/.

[ ] WinSCP-Konfiguration validieren:

[ ] Verifizierung der Client-Einstellung "Transfer to temporary filename" (Erzeugung von .filepart), um die Atomarität beim Upload sicherzustellen.

[x] Bibliotheken installieren:

[x] pip3 install watchdog

[x] pip3 install opencv-python-headless (Wichtig: Headless-Version zur Vermeidung von X11-Konflikten).

[x] pip3 install pandas matplotlib (Für das Processing in AP 3).

📦 AP 2: Backend Core – Ingestion & State Management
Ziel: Robuste Erkennung neuer Dateien ohne Blockieren des Haupt-Threads.

[ ] Global State Manager (Singleton):

[ ] Implementierung der Klasse DataManager in src/data_manager.py.

[ ] Einbau von threading.Lock() für thread-sicheren Zugriff auf den aktuellen DataFrame und Status.

[ ] Watchdog-Service:

[ ] Implementierung des PatternMatchingEventHandler in src/file_monitor.py.

[ ] Logik: Ignorieren von .filepart. Trigger nur bei on_moved (Umbenennung zu .csv) oder on_created (ohne .filepart).

[ ] Integration von "Debouncing" (kurze Wartezeit vor dem Einlesen).

📦 AP 3: Backend Processing – Parsing & Rendering
Ziel: Umwandlung von CSV-Rohdaten in valide Plots, isoliert vom Video-Stream.

[ ] CSV-Parser (Pandas):

[ ] Entwicklung der Header-Erkennung (Suche nach "Wavelength"/"Absorbance" in den ersten 20 Zeilen).

[ ] Implementierung von pd.read_csv mit Fehlerbehandlung für unvollständige Dateien.

[ ] Plotting Engine (Matplotlib):

[ ] Konfiguration des Agg-Backends (Headless Rendering).

[ ] Erstellung der Funktion create_plot(), die ein PNG als Byte-Stream (io.BytesIO) zurückgibt.

[ ] Caching-Logik:

[ ] Implementierung: Plot wird nur neu berechnet, wenn sich der Zeitstempel der Quelldatei ändert.

📦 AP 4: Backend API & Video Stream (Flask)
Ziel: Bereitstellung der Endpunkte und Zusammenführung der Subsysteme.

[ ] Video-Route (/video_feed):

[ ] Bestehenden MJPEG-Generator beibehalten.

[ ] Sicherstellen: 1mm-Skala-Overlay bleibt erhalten (unten rechts, Label zentriert).

[ ] Spektrum-Route (/spectrum_plot.png):

[ ] Auslieferung des gecachten PNGs aus AP 3.

[ ] Steuerungs-API:

[ ] /api/status: JSON-Response mit aktuellem Dateinamen und Timestamp.

[ ] /api/save: Implementierung der Kontext-Logik (Unterscheidung context: 'video' vs. context: 'spectrum').

[ ] Naming Scheme:

[ ] Striktes Format Zeit_Typ_ID_... beim Speichern/Archivieren erzwingen.

📦 AP 5: Frontend – Dashboard & Interaktion
Ziel: Sauberes User-Interface ohne externe Frameworks (Vanilla JS).

[ ] Layout & UI:

[ ] Anpassung der src/index.html.

[ ] Einbau des "Toggle Switch" (CSS Checkbox) zum Umschalten zwischen Video und Plot.

[ ] Präzision in UI:

[ ] Formatierung der Sensor-Readouts prüfen (zwei Leerzeichen nach Doppelpunkt).

[ ] State Machine (JS):

[ ] Logik für currentMode.

[ ] Video-Modus: src="/video_feed".

[ ] Spektrum-Modus: src="/spectrum_plot.png" + Start Polling (setInterval) auf /api/status.

[ ] Implementierung Cache-Busting (?t=...) beim Bild-Refresh.

[ ] Save-Button:

[ ] Anbindung an fetch('/api/save') mit dynamischem JSON-Payload.

📦 AP 6: Integration & Logging
Ziel: Systemstabilität und Fehlerverfolgung.

[ ] Logging-Konfiguration:

[ ] Flask-Logging auf ERROR beschränken (Silent Logs).

[ ] Separates File-Logging für den Watchdog-Dienst.

[ ] Integrationstests:

[ ] Test des "Race Condition"-Szenarios: WinSCP-Upload während aktivem Video-Streaming.

[ ] Überprüfung der Toggle-Logik: Stoppt der Video-Traffic im Browser bei Modus-Wechsel?