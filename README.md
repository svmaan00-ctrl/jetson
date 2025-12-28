📋 Projekt-Dokumentation: Lab_station_v1 ➔ v2 Upgrade
Version: v1.5 (Transition to v2)

Status: AP 1 & 1.5 in Umsetzung / Backend Core Planung aktiv

Entwickler: Lab-Station-Experte (Jetson Dev)

1. System-Übersicht
Kombiniertes Inspektionssystem (Mikroskopie & UV-VIS Spektrometrie) auf einem NVIDIA Jetson Nano Orin Super.

Hardware: Jetson Orin Nano (8GB Unified Memory), USB-Kamera (V4L2, MJPG), Arduino (Sensor-Bridge via Serial), Stellarnet Greenwave UV-VIS.

Architektur: Modularer Aufbau. Strikte Trennung von Backend (Python/Flask) und Frontend (Vanilla JS).

Betriebsziel: 24/7-Stabilität ohne Memory-Leaks oder OOM-Kills.

2. Verzeichnisstruktur (Soll-Zustand v2)
Plaintext
/home/jetson/inspection_project/
├── README.md                    # Projekt-Dokumentation
├── src/                         # Quellcode
│   ├── app.py                   # Hauptprogramm (Flask Server)
│   ├── data_manager.py          # [NEU] Thread-Safe State Management
│   ├── file_monitor.py          # [NEU] Watchdog-Dienst (WinSCP-Ingestion)
│   ├── config.py                # System-Konfiguration & Pfade
│   └── templates/
│       └── index.html           # UI (getrennt vom Backend)
└── data/                        # Zentraler Datenspeicher (NVMe SSD)
    ├── x200_rohdaten_eingang/   # Drop-Zone für WinSCP (.filepart Support)
    ├── x200_spektren_ergebnisse/# Prozessierte Plots & CSVs
    ├── mikroskopbilder/         # Aktuelle Bilder (Naming Scheme!)
    ├── archivierte_spektren/    # Langzeitarchiv
    ├── archivierte_mikroskopbilder/ # Langzeitarchiv
    ├── logs/                    # Systemlogs (Flask Level: ERROR)
    └── sensordaten/             # Arduino-Logs
3. Sicherheits- & Performance-Status
Firewall (UFW): Aktiv. default deny incoming. Ports 22 (SSH) und 5000 (Flask) sind freigegeben.

Flask Binding: Gebunden an 0.0.0.0 (Erreichbarkeit im LAN gesichert).

Memory Management: 4GB Swapfile auf NVMe aktiv (Schutz vor OOM). ZRAM deaktiviert.

4. Vollständiger Projektplan: Lab_station_v2 Upgrade
📦 AP 1: Infrastruktur & Environment Setup
Ziel: Maximale Hardware-Ausnutzung des Jetson für den 24/7 Betrieb.

[x] Verzeichnisstruktur härten (Erstellung aller /data/ Unterordner).

[x] Bibliotheken installieren (watchdog, opencv-python-headless, pandas, matplotlib).

[x] Memory-Härtung:

[x] ZRAM deaktivieren (sudo systemctl disable nvzramconfig).

[x] 16GB Swapfile auf NVMe anlegen und in /etc/fstab persistent machen.

[x] /etc/fstab bereinigt und persistent.

[ ] WinSCP-Schnittstelle:

[ ] Validierung der .filepart Extension bei Übertragung vom Win7-Mess-PC.

📦 AP 1.5: System-Härtung & Security Setup
Ziel: Absicherung der Schnittstellen.

[x] Firewall-Konfiguration (UFW aktiv, Port 22 & 5000 offen).

[x] Flask-Audit:
app.run(host='0.0.0.0', debug=False) verifiziert [1]
[x] app.run(host='0.0.0.0') verifizieren.

[x] Logging-Level in lab_station_v1.py strikt auf logging.ERROR setzen.

[x] User-Security:

[x] Passwort für User jetson ist sicher und geprüft.

[x] SSH-Hardening (PermitRootLogin no) durchgeführt.

📦 AP 2: Backend Core – DataManager & Watchdog
Ziel: Thread-sichere Datenverwaltung zwischen Hardware-Events und UI.

[ ] DataManager (Singleton):

[ ] Implementierung in src/data_manager.py mit threading.Lock.

[ ] Double-Checked Locking Pattern für die Instanziierung verwenden.

[ ] Smart Watchdog:

[ ] Implementierung in src/file_monitor.py.

[ ] Strikte Logik: NUR auf on_moved reagieren (wenn WinSCP von .filepart zu .csv umbenennt).

[ ] Async-Trigger für Plot-Generierung (darf Stream nicht blockieren).

📦 AP 3: Backend Processing – UV-VIS & Vision
Ziel: Mathematisch korrekte Aufbereitung der Daten.

[ ] Stellarnet Parser:

[ ] Unterstützung für .abs, .trans und .scope.

[ ] Korrekte X-Achsen-Skalierung (Cubic Fit Wavelength Support).

[ ] Performance & Hygiene:

[ ] Integration von gc.collect() nach aufwendigen Plot-Operationen.

[ ] OpenCV MJPEG-Generator mit GStreamer-Support für Jetson-Hardware-Beschleunigung.

📦 AP 4: UI-Präzision & Grafik-Standards
Ziel: Einhaltung der visuellen Werksnormen.

[ ] 1mm-Maßstab Overlay:

[ ] Implementierung unten rechts im Bild.

[ ] Zentrierung des Labels über der Linie via cv2.getTextSize.

[ ] Sensor-Readouts:

[ ] Formatierung: Strikte zwei Leerzeichen nach Doppelpunkt (z.B. Temperatur: 24.5°C).

[ ] Naming Scheme Validator:

[ ] Erzwingen von YYYYMMDD_HHMMSS_TYP_ID_POS_... beim Speichern.

📦 AP 5: Frontend – Dashboard (Vanilla JS)
Ziel: Schlanke UI ohne "Overhead".

[ ] Umschalter (Toggle) zwischen Live-Video und Spektrum-Plot.

[ ] State-Machine in JS zur Steigerung der Client-Performance.

[ ] Cache-Busting für Spektren-Updates (?t=TIMESTAMP).

5. System-Steuerung (Aliase)
Alias	Funktion
systemstart	Startet Backend & Watchdog
systemreset	Killt Prozesse, leert Port 5000, triggert udev
ramcheck	Zeigt Top-Memory-Consumer auf dem Jetson
caminfo	Listet V4L2 Formate der Kamera
