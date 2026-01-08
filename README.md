📋 Projekt-Dokumentation: Lab_station_v2 (HAZION EMBEDDED SYSTEM)Version: 

2.1 (HAZION Upgrade Phase)Stand: 06.01.2026 (Full Data Restore)Plattform: NVIDIA Jetson Orin Nano (8GB Unified Memory)1. System-ÜbersichtKombiniertes Inspektionssystem für Mikroskopie (Dino-Lite), UV-VIS Spektrometrie (StellarNet) und kontinuierliche Umgebungsüberwachung (Arduino). Das System ist für den 24/7-Dauerbetrieb ausgelegt.

Architektur: Modularer Monolith mit Flask-Backend und Vanilla JS Frontend.Neu in v2.1:Echtzeit: Wechsel von Polling auf Server-Sent Events (SSE).Video: Hybrid-Pipeline (v4l2src + nvv4l2decoder) für USB-Kameras auf Jetson Hardware.Peripherie: Native Linux-Steuerung der Mikroskop-LEDs via uvcdynctrl.

RAM-Optimierung: Betrieb im Headless-Modus (X11 aus), um Speicher für Bildverarbeitung zu maximieren.2. Netzwerk-Fixes & Erreichbarkeit (Stand 05.01.2026)Um die VS Code SSH-Timeouts zu eliminieren, wurde die Infrastruktur gehärtet:Statische IP: 192.168.1.230 (festgelegt via nmcli auf Interface wlP1p1s0).

WLAN Power Management: Permanent DEAKTIVIERT via udev-Regel (70-wifi-powermanagement.rules), um den Standby des WLAN-Moduls zu verhindern.Firewall (UFW): Aktiviert mit default deny incoming. Erlaubt sind Port 22 (SSH) und Port 5000 (Flask).

3. Verzeichnisstruktur (Finaler Zustand)Betriebssystem und Daten liegen auf einer dedizierten NVMe SSD.Plaintext~/inspection_project/
├── src/
│   ├── app.py                # Flask Server (SSE Streams & Routing)
│   ├── config.py             # Zentrale Pfade & Regex-Regeln
│   ├── data_manager.py       # Thread-Safe Singleton (System-State)
│   ├── file_monitor.py       # Watchdog (Überwacht /x200_rohdaten_eingang/)
│   ├── sensor_bridge.py      # Serial Parser (Arduino Reconnect-Loop)
│   ├── camera_engine.py      # GStreamer Pipeline (MJPEG HW-Decoding)
│   └── spectrum_processor.py # Stellarnet Parser (Dynamischer Header-Skip)
├── templates/
│   └── index.html            # HAZION Dashboard (Grid Layout)
└── data/ (NVMe Mount)
    ├── x200_rohdaten_eingang/ # Drop-Zone für SpectraWiz.abs Dateien
    ├── mikroskopbilder/       # Speicherort für Snapshots
    ├── spektren/              # Speicherort für geparste/validierte Spektren
    ├── klimadaten/            # Sensor-Logs (CSV)
    └── logs/                  # System Logs

3.2. Aktualisierte Verzeichnisstruktur & ArchitekturDie Architektur nutzt nun erfolgreich den Singleton DataManager, um Sensordaten thread-sicher via SSE (Server-Sent Events) an das Dashboard zu pushen.spectrum_processor.py: Unterstützt .abs, .trm, .ssm. Nutzt Agg-Backend für RAM-Hygiene. 

Status: Produktivfile_monitor.py: Watchdog reagiert auf Datei-Eingang und triggert sofort den SSE-Push. 
Status: Produktivcamera_engine.py: Hybrid-Pipeline (ISP auf GPU, Encoding auf CPU) für Orin Nano optimiert. 
Status: Produktiv4. Das Naming Scheme (Strikte Validierung)

Die Generierung erfolgt automatisch durch Dropdown-Menüs im Dashboard. Jede Datei muss exakt so benannt werden können.
A. Dateimuster 
Mikroskopie: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol.jpg
Spektrum: YYYYMMDD_HHMMSS_TYP_ID_POS_Modus.csv
Klimadaten: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID.csvB. 
VariablenTYP: Bohrprobe (B), Wischprobe (W), Material (M), Referenz (R)
LICHT: Ring (R), Coax (C), Side (S), Off (O)POL: An (1), Aus (0)MODUS: ABS (Absorbance), TRANS (Transmission), SCOPE (Scope Mode)
ID/POS: Freitext (Alphanumerisch, via Regex bereinigt)

5. UI- & Dashboard-StandardsTitel: "HAZION EMBEDDED SYSTEM"Modi-Buttons: Mikroskop-Modus, Spektrum-Modus, Klimadaten-Modus.Dateianzeige: Unter dem Viewport wird immer der aktuelle Dateiname angezeigt.Visuelles Feedback: Buttons leuchten bei Klick kurz auf (Active State).Präzision: Sensorwerte immer mit zwei Leerzeichen nach dem Doppelpunkt (Wert:  XX.X).Maßstab: 1mm-Overlay unten rechts fixiert, Label exakt zentriert über der Linie.

6. System-Steuerung (Aliase)AliasFunktionsystemstartStartet Flask, Watchdog und Sensor-Threads zentral via app.pysystemresetBeendet Flask-Prozesse, leert Port 5000 und triggert udevramcheckZeigt Top-Memory-Consumer (Python) auf dem JetsoncaminfoListet V4L2 Formate der Kamera (v4l2-ctl --list-formats-ext)ledcheckListet verfügbare LED-Controls (uvcdynctrl -c)

7. Verbesserungen & Forschungsbericht (v2.1)Spektrum-Parser (FIXED): Der Parser scheitert nicht mehr an der Header-Länge. Wir haben ein dynamisches Header-Skipping implementiert, das die erste Datenzeile via Regex identifiziert.Encoding-Fix (FIXED): Dateien wie Leerküvette.ABS werden nun fehlerfrei verarbeitet, da wir von UTF-8 auf latin-1 umgestellt haben, um Windows-Umlaute zu unterstützen.NumPy-ABI (FIXED): Der "Multi-dimensional indexing"-Crash unter NumPy 1.26.4 wurde durch explizite Konvertierung in NumPy-Arrays (.to_numpy()) in der spectrum_processor.py behoben.Speicherung (STABIL): Die Pfade sind via config.py fest auf die NVMe-Pfade verlinkt. /api/save_data in app.py sortiert Snapshots, Spektren und Logs bereits korrekt ein.Beleuchtung: Das Dino-Lite Koaxial-Licht benötigt oft einen speziellen UVC-Extension-Code (0xf4 statt 0xf2). Dies muss bei AP 6 validiert werden.Stromversorgung: Sicherstellen, dass der Jetson im 15W Modus läuft (sudo nvpmodel -m 0), da USB-Kamera und Arduino Strom ziehen.

8. Offene Punkte & Neue Anforderungen (AP 6.5) Die Steuerung erfolgt über die API-Route /api/camera_control:ParameterBereichBefehl (Beispiel)Brightness1 - 128v4l2-ctl -c brightness=XContrast1 - 32v4l2-ctl -c contrast=XFocus0 - 32v4l2-ctl -c focus_absolute=XGamma1 - 12v4l2-ctl -c gamma=X


Ergänzung Forschungsbericht (v2.1) - UI/UX Logik
Anforderung SNV-Toggle: Die Evaluierung hat ergeben, dass die Umschaltung zwischen Rohdaten und SNV (KI-Ready) für den Anwender direkt im Modus-Menü (Zahnrad) erreichbar sein muss.

Bug-Fix: Die Sichtbarkeits-Logik in switchSpecView(v) muss zwingend die Graphen-Skalierung (resize()) triggern, um Darstellungsfehler nach dem DOM-Wechsel zu vermeiden.

9. AP 2: Backend Core - DataManager (KI-Ready Pipeline)Status: In ArbeitZiel: Thread-sichere Orchestrierung von Bild- und Spektrometerdaten für KI-Training (Random Forest).

Spezifikationen:

File-Watching: Überwachung von /data/x200_rohdaten_eingang/ via watchdog.Event-Handling: Trigger ausschließlich bei IN_CLOSE_WRITE (Vermeidung von Race Conditions).Validierung: Striktes Naming-Scheme Check (Zeit_Typ_ID_Position).

Preprocessing: Implementierung der Normalisierung (SNV) zur Vorbereitung für Machine Learning.Archivierung: Verschieben in archivierte_spektren/ erst NACH erfolgreicher Normalisierung.Concurrency: Absicherung aller Dateioperationen mittels threading.Lock().10. Aktueller Interims-Status (05.01.2026)

Netzwerk: STABIL (Statische IP 192.168.1.230, Power-Save OFF).Kamera: Einsatzbereit über GStreamer; Software-Encoding via CPU aktiv.Sensoren: Stabil. Mock-Daten via SSE; Serial-Port Anbindung ausstehend.Maßstab: Funktional und kalibriert für 4x und 10x Objektive.Speicherung: Vollständig implementiert für alle drei Modi.

📦 Detaillierte Arbeitspakete
📦 AP 1: Infrastruktur & Environment (Abgeschlossen)
[x] Verzeichnisstruktur auf NVMe SSD gehärtet.

[x] ZRAM deaktiviert und 16GB Swapfile auf NVMe angelegt.

[x] NumPy-ABI Konflikt gelöst (numpy==1.26.4).

📦 AP 1.5: System-Härtung (Abgeschlossen)
[x] Firewall (UFW) aktiv: Ports 22 und 5000 offen.

[x] SSH-Hardening (PermitRootLogin no).

[x] Flask-Audit: debug=False und Silent-Logging.

[x] NEU: Statische IP und WLAN Power-Management Fix.

📦 AP 2: Backend Core – DataManager & Sensoren (Abgeschlossen)
[x] DataManager (Singleton): Thread-safe Implementierung via _lock.

[x] Sensor-Bridge: Basic Polling Struktur in sensor_bridge.py.

[x] Smart Watchdog: Event-Handler für Dateisystem in file_monitor.py.

📦 AP 3: Backend Processing – Vision & UV-VIS (Abgeschlossen)
[x] Stellarnet Parser Grundgerüst in spectrum_processor.py.

[x] GStreamer Integration Grundgerüst via cv2.CAP_GSTREAMER.

[x] Memory-Hygiene via gc.collect() nach rechenintensiven Operationen.

📦 AP 4: UI-Präzision (Abgeschlossen)
[x] 1mm-Maßstab Overlay Konzept.

[x] Naming Scheme Validator (Regex) in config.py und app.py aktiv.

📦 AP 5: Frontend – Dashboard (Abgeschlossen)
[x] 3-Mode-Toggle (HTML/CSS) für Mikroskop, Spektrum und Klima.

[x] Basic Layout Implementation mit Dark-Mode Dashboard.

📦 AP 6: Hardware-Integration & Low-Level Fixes (In Arbeit)

[x] Video-Engine Rewrite: Optimierte Pipeline für Orin Nano.

[x] Legacy-Integration (M600): Physische Netzwerktrennung (192.168.10.x) auf eth0 etabliert.

[x] Remote-Access: RDP via SSH-Tunnel (Localhost-Forwarding) automatisiert (SSH-Keys).

[x] Headless-Config: Windows 7 GPU-Aktivierung (Dummy Plug Konzept) und Energiesparplan fixiert.

[x] Strategie-Entscheidung: Physischer RDP-Zugriff ersetzt Virtual Machine.

[ ] Integration in "systemaus" Alias (Jetson steuert Win7)

Der Jetson sendet den Abschaltbefehl über das Netzwerkkabel an den M600 und fährt sich danach selbst runter.

[x] LED-Steuerung (Linux): Implementierung via uvcdynctrl (Frontend-Zwang auf "Always Green" für Mikroskop-Status).

[ ] Sensor-Bridge Serial: Ausbau der Reconnect-Schleife für Arduino.

📦 AP 6.5: Dynamische Kamera-Steuerung

[ ] API-Route: Erstellung von /api/camera_control.

[ ] Frontend-Slider: Integration der Schieberegler.

📦 AP 7: Data Ingest & Storage Logic (In Bearbeitung)

[x] Robustes Spectrum Parsing (Header-Skipping aktiv).

[x] Watchdog Logik: Erkennt .abs, .trm und .ssm Dateien.

[x] Speicher-Funktion (Backend): /api/save_data sortiert nach DIRS.

📦 AP 8: Mikroskopie-Features (Frontend)

[x] Freeze-Button: JS-Funktion für Standbild-Modus implementiert.

[x] Dynamischer Maßstab: Canvas-Logik für pxPerMm und scaleFactor.

[x] Kalibrierung: CALIBRATION Werte hinterlegt.

📦 AP 9: Dashboard UX & Feedback (Deep-Level Integration)

Status: Kritisch / In Bearbeitung

Ziel: Orchestrierung der Modus-spezifischen Steuerelemente und Sicherstellung der grafischen Integrität bei Container-Wechseln.

Technische Anforderungen & Herausforderungen:

[x] SNV-Dropdown-Synchronisation (Bugfix durch ID-Bereinigung).

[x] Canvas-Rescaling-Algorithmus (chart.resize() Trigger mit Timeout).

[x] Event-Bubbling-Protection (Zahnrad-Logik fixiert).

[ ] Z-Score Mapping.

[ ] Visuelles Feedback-System (.active-click Klasse).

[x] UI-Struktur: Sidebar auf 32px Höhe gestrafft, um Überlappungen zu vermeiden.

[ ] Lade-Funktion: Browser für Bestandsdaten in data/.

📦 AP 10: Final Deployment & Test

[ ] Autostart: Einrichtung als systemd Service.

[ ] Log-Rotation: Setup für Klimadaten-CSVs.

[ ] System-Test: Validierung des kompletten Workflows.

📦 AP 11: Analyse-Tools (Zukunft)

Das System visualisiert das Spektrum ohne automatisierte Peak-Erkennung. Interpretation durch den Anwender.

📦 AP 12: Spektrendiagramm-Validierung (Korrekturphase)

[x] Live-Update: Datenintegration in rawChart und snvChart via SSE.

[x] Achsen-Design: X-Achse (204-1586nm) mit 100nm-Schritten und 50nm-Marker-Punkten finalisiert.

[x] Y-Achsen-Fix: Skalierung korrigiert (0,1 Schritte in  Linien).

[ ] Y-Achsen-Normalisierung.

[ ] Baseline-Fix.

[ ] Ziel: Laden und Anzeigen von historischen Daten im Frontend.

Die Aufgaben:

Backend (Python):

Neuer Endpunkt /api/list_files: Muss den Inhalt der Ordner (snapshots, spektren, logs) scannen und als JSON-Liste zurückgeben (filterbar nach ID oder Datum).

Neuer Endpunkt /api/load_file: Muss die Rohdaten der gewählten Datei an das Frontend senden.

Frontend (HTML/JS):

Button „Archiv laden“: Neben dem Speicher-Button.

Modal (Overlay-Fenster): Ein Pop-up, das die Dateiliste zeigt.

Rendering:

Bild: Ersetzt den Live-Stream durch das geladene Bild.

Spektrum: Lädt die Kurve in den Chart.js Graphen.

Klima: Zeigt den Verlauf aus dem Log an.