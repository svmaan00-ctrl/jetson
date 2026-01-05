Projekt-Dokumentation: Lab_station_v2 (HAZION EMBEDDED SYSTEM)Version: 2.1 (HAZION Upgrade Phase)Stand: 05.01.2026 (Update: Netzwerk & IP Fix)

Plattform: NVIDIA Jetson Orin Nano (8GB Unified Memory)Status: 

AP 1-5 (Core) abgeschlossen | 

AP 6-10 (Integration & UI) in Bearbeitung1. System-ÜbersichtKombiniertes Inspektionssystem für Mikroskopie (Dino-Lite), UV-VIS Spektrometrie (StellarNet) und kontinuierliche Umgebungsüberwachung (Arduino). Das System ist für den 24/7-Dauerbetrieb ausgelegt.Architektur: Modularer Monolith mit Flask-Backend und Vanilla JS Frontend. 

Neu in v2.1:Echtzeit: Wechsel von Polling auf Server-Sent Events (SSE).Video: Hybrid-Pipeline (v4l2src + nvv4l2decoder) für USB-Kameras auf Jetson Hardware.Peripherie: Native Linux-Steuerung der Mikroskop-LEDs via uvcdynctrl.

RAM-Optimierung: Betrieb im Headless-Modus (X11 aus), um Speicher für Bildverarbeitung zu maximieren.2. NEU: Netzwerk-Fixes & Erreichbarkeit (Stand 05.01.2026)Um die VS Code SSH-Timeouts zu eliminieren, wurde die Infrastruktur gehärtet:Statische IP: 192.168.1.230 (festgelegt via nmcli auf Interface wlP1p1s0).WLAN Power Management: Permanent DEAKTIVIERT via udev-Regel (70-wifi-powermanagement.rules), um den Standby des WLAN-Moduls zu verhindern.Firewall (UFW): Aktiviert mit default deny incoming. Erlaubt sind Port 22 (SSH) und Port 5000 (Flask).3. Verzeichnisstruktur (Finaler Zustand)Betriebssystem und Daten liegen auf einer dedizierten NVMe SSD.~/inspection_project/├── src/│   ├── app.py # Flask Server (SSE Streams & Routing)│   ├── config.py # Zentrale Pfade & Regex-Regeln│   ├── data_manager.py # Thread-Safe Singleton (System-State)│   ├── file_monitor.py # Watchdog (Überwacht /x200_rohdaten_eingang/)│   ├── sensor_bridge.py # Serial Parser (Arduino Reconnect-Loop)│   ├── camera_engine.py # GStreamer Pipeline (MJPEG HW-Decoding)│   └── spectrum_processor.py # Stellarnet Parser (Dynamischer Header-Skip)├── templates/│   └── index.html # HAZION Dashboard (Grid Layout)└── data/ (NVMe Mount)├── x200_rohdaten_eingang/ # Drop-Zone für SpectraWiz.abs Dateien├── mikroskopbilder/ # Speicherort für Snapshots├── spektren/ # Speicherort für geparste/validierte Spektren├── klimadaten/ # Sensor-Logs (CSV)└── logs/ # System Logs4. Das Naming Scheme (Strikte Validierung)Die Generierung erfolgt automatisch durch Dropdown-Menüs im Dashboard. Jede Datei muss exakt so benannt werden können.A. DateimusterMikroskopie: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol.jpgSpektrum: YYYYMMDD_HHMMSS_TYP_ID_POS_Modus.csvKlimadaten: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID.csvB. VariablenTYP: Bohrprobe (B), Wischprobe (W), Material (M), Referenz (R)LICHT: Ring (R), Coax (C), Side (S), Off (O)POL: An (1), Aus (0)MODUS: ABS (Absorbance), TRANS (Transmission), SCOPE (Scope Mode)ID/POS: Freitext (Alphanumerisch, via Regex bereinigt)5. UI- & Dashboard-StandardsTitel: "HAZION EMBEDDED SYSTEM"Modi-Buttons: Mikroskop-Modus, Spektrum-Modus, Klimadaten-Modus.Dateianzeige: Unter dem Viewport wird immer der aktuelle Dateiname angezeigt.Visuelles Feedback: Buttons leuchten bei Klick kurz auf (Active State).Präzision: Sensorwerte immer mit zwei Leerzeichen nach dem Doppelpunkt (Wert:  XX.X).Maßstab: 1mm-Overlay unten rechts fixiert, Label exakt zentriert über der Linie.6. System-Steuerung (Aliase)AliasFunktionsystemstartStartet Flask, Watchdog und Sensor-Threads zentral via app.pysystemresetBeendet Flask-Prozesse, leert Port 5000 und triggert udevramcheckZeigt Top-Memory-Consumer (Python) auf dem JetsoncaminfoListet V4L2 Formate der Kamera (v4l2-ctl --list-formats-ext)ledcheckListet verfügbare LED-Controls (uvcdynctrl -c)7. Korrektur: System-Status (v2.1)Spektrum-Parser (FIXED): Der Parser scheitert nicht mehr an der Header-Länge. Wir haben ein dynamisches Header-Skipping implementiert, das die erste Datenzeile via Regex identifiziert 1111.Encoding-Fix (FIXED): Dateien wie Leerküvette.ABS werden nun fehlerfrei verarbeitet, da wir von UTF-8 auf latin-1 umgestellt haben, um Windows-Umlaute zu unterstützen.NumPy-ABI (FIXED): Der "Multi-dimensional indexing"-Crash unter NumPy 1.26.4 wurde durch explizite Konvertierung in NumPy-Arrays (.to_numpy()) in der spectrum_processor.py behoben.Speicherung (STABIL): Die Pfade sind via config.py fest auf die NVMe-Pfade verlinkt 2222. /api/save_data in app.py sortiert Snapshots, Spektren und Logs bereits korrekt ein.

3.2. Aktualisierte Verzeichnisstruktur & ArchitekturDie Architektur nutzt nun erfolgreich den Singleton DataManager, um Sensordaten thread-sicher via SSE (Server-Sent Events) an das Dashboard zu pushen 444444444.DateiFunktionStatusspectrum_processor.pyUnterstützt .abs, .trm, .ssm. Nutzt Agg-Backend für RAM-Hygiene 5Produktivfile_monitor.pyWatchdog reagiert auf Datei-Eingang und triggert sofort den SSE-Push 6666Produktivcamera_engine.pyHybrid-Pipeline (ISP auf GPU, Encoding auf CPU) für Orin Nano optimiert 777777777Produktiv8. Offene Punkte (Arbeitspakete 6 & 6.5)AP 6 (Hardware-Fixes): Die Implementierung von uvcdynctrl zur nativen LED-Steuerung (Ring/Coax) steht noch aus 8.AP 6.5 (Kamera-Slider): Die API-Route /api/camera_control für Brightness, Contrast und Focus muss noch in app.py und das Frontend integriert werden.AP 10 (Deployment): Die Einrichtung des systemd-Services für den Autostart nach Power-Loss fehlt noch.4. Das Naming Scheme (Single Source of Truth)Das Schema ist in config.py via VALID_NAME_REGEX hinterlegt und wird in app.py bei jedem Speichervorgang validiert 99999999:Mikroskopie: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol.jpgRegex: r'^[a-zA-Z0-9_-]+$' (Keine Leerzeichen erlaubt!) 101010109. Neue Anforderung: Schieberegler (AP 6.5)Die Steuerung erfolgt über die API-Route /api/camera_control:| Parameter | Bereich | Befehl (Beispiel) || :--- | :--- | :--- || Brightness | 1 - 128 | v4l2-ctl -c brightness=X || Contrast | 1 - 32 | v4l2-ctl -c contrast=X || Focus | 0 - 32 | v4l2-ctl -c focus_absolute=X || Gamma | 1 - 12 | v4l2-ctl -c gamma=X |10. Empfehlungen für Phase v2.1Stromversorgung: Sicherstellen, dass der Jetson im 15W Modus läuft (sudo nvpmodel -m 0), da USB-Kamera und Arduino Strom ziehen.Beleuchtung: Das Dino-Lite Koaxial-Licht benötigt oft einen speziellen UVC-Extension-Code (0xf4 statt 0xf2). Dies muss bei AP 6 validiert werden.📋 Projekt-Status & Roadmap (Stand: 2026-01-05)

📦 AP 1: Infrastruktur & Environment (Abgeschlossen)[x] Verzeichnisstruktur auf NVMe SSD gehärtet.[x] ZRAM deaktiviert und 16GB Swapfile auf NVMe angelegt.[x] NumPy-ABI Konflikt gelöst (numpy==1.26.4).

📦 AP 1.5: System-Härtung (Abgeschlossen)[x] Firewall (UFW) aktiv: Ports 22 und 5000 offen.[x] SSH-Hardening (PermitRootLogin no).[x] Flask-Audit: debug=False und Silent-Logging.[x] NEU: Statische IP und WLAN Power-Management Fix.

📦 AP 2: Backend Core – DataManager & Sensoren (Abgeschlossen)[x] DataManager (Singleton): Thread-safe Implementierung via _lock.[x] Sensor-Bridge: Basic Polling Struktur in sensor_bridge.py.[x] Smart Watchdog: Event-Handler für Dateisystem in file_monitor.py.

📦 AP 3: Backend Processing – Vision & UV-VIS (Abgeschlossen)[x] Stellarnet Parser Grundgerüst in spectrum_processor.py.[x] GStreamer Integration Grundgerüst via cv2.CAP_GSTREAMER.[x] Memory-Hygiene via gc.collect() nach rechenintensiven Operationen.

📦 AP 4: UI-Präzision (Abgeschlossen)[x] 1mm-Maßstab Overlay Konzept.[x] Naming Scheme Validator (Regex) in config.py und app.py aktiv.

📦 AP 5: Frontend – Dashboard (Abgeschlossen)[x] 3-Mode-Toggle (HTML/CSS) für Mikroskop, Spektrum und Klima.[x] Basic Layout Implementation mit Dark-Mode Dashboard.Offene Arbeitspakete (v2.1 Upgrade & Fixes)

📦 AP 6: Hardware-Integration & Low-Level Fixes[x] Video-Engine Rewrite: Optimierte Pipeline für Orin Nano.[ ] LED-Steuerung (Linux): Implementierung via uvcdynctrl.[ ] Sensor-Bridge Serial: Ausbau der Reconnect-Schleife für Arduino.[ ] ggf. Virtual Machine für Messrechner (Monitor-Remote).

📦 AP 6.5: Dynamische Kamera-Steuerung[ ] API-Route: Erstellung von /api/camera_control.[ ] Frontend-Slider: Integration der Schieberegler.

📦 AP 7: Data Ingest & Storage Logic (In Bearbeitung)[x] Robustes Spectrum Parsing (Header-Skipping aktiv).[x] Watchdog Logik: Erkennt .abs, .trm und .ssm Dateien.[x] Speicher-Funktion (Backend): /api/save_data sortiert nach DIRS.

📦 AP 8: Mikroskopie-Features (Frontend)[ ] Freeze-Button: JS-Funktion für Standbild-Modus.[x] Dynamischer Maßstab: Canvas-Logik für pxPerMm und scaleFactor.[x] Kalibrierung: CALIBRATION Werte hinterlegt.

📦 AP 9: Dashboard UX & Feedback[x] Dateinamen-Vorschau via updateFilenamePreview().[ ] Visuelles Feedback: CSS-Klasse .active-click.[ ] Lade-Funktion: Browser für Bestandsdaten in data/.

📦 AP 10: Final Deployment & Test[ ] Autostart: Einrichtung als systemd Service.[ ] Log-Rotation: Setup für Klimadaten-CSVs.[ ] System-Test: Validierung des kompletten Workflows.

📦 AP 11: Analyse-Tools (Zukunft)Das System visualisiert das Spektrum ohne automatisierte Peak-Erkennung. Interpretation durch den Anwender. Update für Schwellenwert-Algorithmen empfohlen.

📦 AP 12: Spektrendiagramm zeigt negative Werte an die müssen korrigiert werden da Absorption bzw. Transmission von 0-100 % oder die entsprechenden Counts geht. Diagramm muss ebenfalls an Y-Achse angepasst werden nach Vorgabe.

## AP 2: Backend Core - DataManager (KI-Ready Pipeline)
**Status:** In Arbeit
**Ziel:** Thread-sichere Orchestrierung von Bild- und Spektrometerdaten für KI-Training (Random Forest).

### Spezifikationen:
* **File-Watching:** Überwachung von `/data/x200_rohdaten_eingang/` via `watchdog`.
* **Event-Handling:** Trigger ausschließlich bei `IN_CLOSE_WRITE` (Vermeidung von Race Conditions).
* **Validierung:** Striktes Naming-Scheme Check (`Zeit_Typ_ID_Position`).
* **Preprocessing:** Implementierung der Normalisierung (SNV) zur Vorbereitung für Machine Learning.
* **Archivierung:** Verschieben in `archivierte_spektren/` erst NACH erfolgreicher Normalisierung.
* **Concurrency:** Absicherung aller Dateioperationen mittels `threading.Lock()`.

7. Aktueller Interims-Status (05.01.2026)Netzwerk: STABIL (Statische IP 192.168.1.230, Power-Save OFF).Kamera: Einsatzbereit über GStreamer; Software-Encoding via CPU aktiv.Sensoren: Stabil. Mock-Daten via SSE; Serial-Port Anbindung ausstehend.Maßstab: Funktional und kalibriert für 4x und 10x Objektive.Speicherung: Vollständig implementiert für alle drei Modi.