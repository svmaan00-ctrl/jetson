Projekt-Dokumentation: Lab_station_v2 (HAZION EMBEDDED SYSTEM)
Version: 2.1 (HAZION Upgrade Phase) Stand: 29.12.2025 Plattform: NVIDIA Jetson Orin Nano (8GB Unified Memory) Status: AP 1-5 (Core) abgeschlossen | AP 6-10 (Integration & UI) in Bearbeitung

1. System-Übersicht
Kombiniertes Inspektionssystem für Mikroskopie (Dino-Lite), UV-VIS Spektrometrie (StellarNet) und kontinuierliche Umgebungsüberwachung (Arduino). Das System ist für den 24/7-Dauerbetrieb ausgelegt.

Architektur: Modularer Monolith mit Flask-Backend und Vanilla JS Frontend. Neu in v2.1:

Echtzeit: Wechsel von Polling auf Server-Sent Events (SSE).

Video: Hybrid-Pipeline (v4l2src + nvv4l2decoder) für USB-Kameras auf Jetson Hardware.

Peripherie: Native Linux-Steuerung der Mikroskop-LEDs via uvcdynctrl.

2. Verzeichnisstruktur (Finaler Zustand)
Betriebssystem und Daten liegen auf einer dedizierten NVMe SSD.

~/inspection_project/ ├── src/ │ ├── app.py # Flask Server (SSE Streams & Routing) │ ├── config.py # Zentrale Pfade & Regex-Regeln │ ├── data_manager.py # Thread-Safe Singleton (System-State) │ ├── file_monitor.py # Watchdog (Überwacht /x200_rohdaten_eingang/) │ ├── sensor_bridge.py # Serial Parser (Arduino Reconnect-Loop) │ ├── camera_engine.py # GStreamer Pipeline (MJPEG HW-Decoding) │ └── spectrum_processor.py # Stellarnet Parser (Dynamischer Header-Skip) ├── templates/ │ └── index.html # HAZION Dashboard (Grid Layout) └── data/ (NVMe Mount) ├── x200_rohdaten_eingang/# Drop-Zone für SpectraWiz.abs Dateien ├── mikroskopbilder/ # Speicherort für Snapshots ├── spektren/ # Speicherort für geparste/validierte Spektren ├── klimadaten/ # Sensor-Logs (CSV) └── logs/ # System Logs

3. Das Naming Scheme (Strikte Validierung)
Die Generierung erfolgt automatisch durch Dropdown-Menüs im Dashboard. Jede Datei muss exakt so benannt werden können.

A. Dateimuster

Mikroskopie: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol.jpg

Spektrum: YYYYMMDD_HHMMSS_TYP_ID_POS_Modus.csv

Klimadaten: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID.csv

B. Variablen

TYP: Bohrprobe (B), Wischprobe (W), Material (M), Referenz (R)

LICHT: Ring (R), Coax (C), Side (S), Off (O)

POL: An (1), Aus (0)

MODUS: ABS (Absorbance), TRANS (Transmission), SCOPE (Scope Mode)

ID/POS: Freitext (Alphanumerisch, via Regex bereinigt)

4. UI- & Dashboard-Standards
Titel: "HAZION EMBEDDED SYSTEM"

Modi-Buttons: Mikroskop-Modus, Spektrum-Modus, Klimadaten-Modus.

Dateianzeige: Unter dem Viewport wird immer der aktuelle Dateiname angezeigt.

Visuelles Feedback: Buttons leuchten bei Klick kurz auf (Active State).

5. Vollständiger Projektplan: Lab_station_v2
📦 AP 1: Infrastruktur & Environment (Abgeschlossen)
[x] Verzeichnisstruktur auf NVMe SSD gehärtet.

[x] ZRAM deaktiviert und 16GB Swapfile auf NVMe angelegt.

[x] NumPy-ABI Konflikt gelöst (numpy==1.26.4).

📦 AP 1.5: System-Härtung (Abgeschlossen)
[x] Firewall (UFW) aktiv: Ports 22 (SSH) und 5000 (Flask) offen.

[x] SSH-Hardening (PermitRootLogin no).

[x] Flask-Audit: debug=False und Silent-Logging.

📦 AP 2: Backend Core – DataManager & Sensoren (Abgeschlossen)
[x] DataManager (Singleton): Thread-safe Implementierung.

[x] Sensor-Bridge: Basic Polling Struktur.

[x] Smart Watchdog: Event-Handler für Dateisystem.

📦 AP 3: Backend Processing – Vision & UV-VIS (Abgeschlossen)
[x] Stellarnet Parser Grundgerüst.

[x] GStreamer Integration Grundgerüst.

[x] Memory-Hygiene (gc.collect).

📦 AP 4: UI-Präzision (Abgeschlossen)
[x] 1mm-Maßstab Overlay Konzept.

[x] Naming Scheme Validator (Regex).

📦 AP 5: Frontend – Dashboard (Abgeschlossen)
[x] 3-Mode-Toggle (HTML/CSS).

[x] Basic Layout Implementation.

Offene Arbeitspakete (v2.1 Upgrade & Fixes)
Die folgenden Pakete adressieren die im Untersuchungsbericht festgestellten Defizite (Kamera-Lag, fehlende LED-Steuerung, Parsing-Fehler).

📦 AP 6: Hardware-Integration & Low-Level Fixes
Ziel: Stabilisierung der Peripherie (Kamera, Licht, Sensoren).

[ ] Video-Engine Rewrite: Ersetzen von nvarguscamerasrc durch v4l2src mit MJPEG-Decoding (nvv4l2decoder mjpeg=1), um das "Rödeln" zu beheben und 30FPS zu garantieren.

[ ] LED-Steuerung (Linux): Implementierung von subprocess-Aufrufen für uvcdynctrl, um Ringlicht, Coax und LEDs per Software zu schalten (Ersetzt Mock-Logik).

[ ] Sensor-Bridge Serial: Implementierung von pyserial mit Reconnect-Schleife ("Try/Except SerialException") für robustes Lesen des Arduino-Strings (T1\tH1...).

📦 AP 7: Data Ingest & Storage Logic
Ziel: Korrekte Verarbeitung von Spektren und Speicherung aller Daten.

[ ] Robustes Spectrum Parsing: Anpassung SpectrumProcessor auf dynamisches Header-Skipping (Suche nach erster Zeile mit 2 Floats), da.abs Header variabel sind.

[ ] Watchdog Logik: file_monitor.py muss .abs Dateien in /data/x200_rohdaten_eingang erkennen, parsen und das Ergebnis via SSE an das Frontend pushen (Auto-Plot).

[ ] Speicher-Funktion (Backend): Finalisierung von /api/save_data. Muss secure_filename nutzen und die Dateien basierend auf dem Modus (Mikroskop/Spektrum/Klima) in den korrekten Unterordner schieben.

📦 AP 8: Mikroskopie-Features (Frontend)
Ziel: Messbarkeit und Bildkontrolle.

[ ] Freeze-Button: JS-Funktion implementieren, die das Video-Element pausiert (video.pause()) und wieder startet ("Standbild").

[ ] Dynamischer Maßstab: Canvas-Overlay Logik anpassen. Der 1mm-Strich muss sich basierend auf der gewählten Vergrößerung (Dropdown) und der tatsächlichen Video-Auflösung (nicht CSS-Größe) skalieren.

[ ] Kalibrierung: Hinterlegen der Pixel-pro-mm Werte in einer JS-Config für die Objektive.

📦 AP 9: Dashboard UX & Feedback
Ziel: Benutzerführung und Status-Informationen.

[ ] Dateinamen-Vorschau: Implementierung einer Live-Anzeige unter dem Screen: "Aktueller Dateiname:".

[ ] Visuelles Feedback: CSS-Klasse .active-click erstellen, die Buttons kurz grün aufleuchten lässt, wenn die AJAX/Fetch-Anfrage erfolgreich war (200 OK).

[ ] Lade-Funktion (Load Data): Neuer Button/Bereich, um alte Bilder oder Spektren aus den data/-Verzeichnissen zu laden und im Viewer anzuzeigen.

📦 AP 10: Final Deployment & Test
[ ] Autostart: Einrichtung als systemd Service (hazion.service).

[ ] Log-Rotation: Setup logrotate für Sensordaten, um NVMe nicht zuzumüllen.

[ ] System-Test: Validierung des kompletten Flows: Probe rein -> LEDs an -> Fokus -> Freeze -> Speichern -> Validierung Dateiname.

6. System-Steuerung (Aliase)
Alias	Funktion
systemstart	Startet Flask, Watchdog und Sensor-Threads zentral via app.py
systemreset	Beendet Flask-Prozesse, leert Port 5000 und triggert udev
ramcheck	Zeigt Top-Memory-Consumer (Python) auf dem Jetson
caminfo	Listet V4L2 Formate der Kamera (v4l2-ctl --list-formats-ext)
ledcheck	Listet verfügbare LED-Controls (uvcdynctrl -c)
7. Aktueller Interims-Status (29.12.2025)
Kamera: Aktuell instabil (Dashboard rödelt). Fix in AP 6 definiert.

LEDs: Ohne Funktion. Fix in AP 6 (uvcdynctrl) definiert.

Spektrum: Watchdog erkennt Datei, Parser scheitert aber an Header-Länge. Fix in AP 7 definiert.

Speicherung: Logik vorhanden, aber Pfade noch nicht final auf NVMe verlinkt.

8. Empfehlungen für Phase v2.1
Stromversorgung: Sicherstellen, dass der Jetson im 15W Modus läuft (sudo nvpmodel -m 0), da die USB-Kamera und der Arduino Strom ziehen.

Beleuchtung: Das Dino-Lite Koaxial-Licht benötigt oft einen speziellen UVC-Extension-Code (0xf4 statt 0xf2). Dies muss beim Testing von AP 6 validiert werden.

