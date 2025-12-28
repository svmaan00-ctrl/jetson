
________________________________________
2. Verzeichnisstruktur (Finaler Zustand v2)
Betriebssystem und Daten liegen auf einer dedizierten NVMe SSD, um die SD-Karte vor Verschleiß durch Schreibzyklen (Swap/Logs) zu schützen.

Projekt-Dokumentation: Lab_station_v2 (HAZION EMBEDDED SYSTEM)
Version: 2.1 (HAZION Upgrade Phase) Plattform: NVIDIA Jetson Orin Nano (8GB Unified Memory) Status: AP 1-5 (Core) abgeschlossen | AP 6-10 (UI/Logic) offen

1. System-Übersicht
Kombiniertes Inspektionssystem für Mikroskopie, UV-VIS Spektrometrie und kontinuierliche Umgebungsüberwachung. Das System ist für den 24/7-Dauerbetrieb ausgelegt.

Architektur: Modularer Monolith mit Flask-Backend und Vanilla JS Frontend.

Neu in v2.1: Umstellung von Polling auf Server-Sent Events (SSE) zur Eliminierung von Datenverlusten.

Performance-Ziel: Maximale RAM-Effizienz und Echtzeit-Validierung von Dateinamen vor der Speicherung.

2. Verzeichnisstruktur (Finaler Zustand)
Betriebssystem und Daten liegen auf einer dedizierten NVMe SSD.

~/inspection_project/ ├── src/ │ ├── app.py # Flask Server (SSE Streams implementiert) │ ├── config.py # Zentrale Pfade & Regex-Regeln │ ├── data_manager.py # Thread-Safe Singleton │ ├── file_monitor.py # Watchdog (Signalisiert Ingest an Frontend) │ ├── sensor_bridge.py # Serial Parser (T1, T2, RH1, RH2, Gas) │ ├── camera_engine.py # GStreamer Pipeline │ └── spectrum_processor.py # Stellarnet Parser ├── templates/ │ └── index.html # HAZION Dashboard (Grid Layout) └── static/ ├── js/ # Modularisiertes JS (Naming, SSE, Canvas) └── css/ # Styles für LEDs und Overlay

3. Das Naming Scheme (Strikte Validierung)
Das System erzwingt konsistente Dateinamen. Die Generierung erfolgt automatisch durch Dropdown-Menüs im Dashboard.

A. Dateimuster
Mikroskopie: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol_EXT

Spektrum: YYYYMMDD_HHMMSS_TYP_ID_POS_Modus_EXT

Klimadaten: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID_EXT

B. Variablen & Dropdowns
Diese Werte werden im Frontend gewählt und vom System zu Dateinamen zusammengesetzt:

TYP: Bohrprobe (B), Wischprobe (W), Material (M), Referenz (R)

MODUS (Spektrum): ABS (Absorbance), TRANS (Transmission), SCOPE (Scope Mode)

LICHT: Ring (R), Coax (C), Side (S), Off (O)

POL: An (1), Aus (0)

ID: Freitext (Alphanumerisch, via Regex bereinigt)

POS: Freitext (Alphanumerisch, via Regex bereinigt)

4. UI- & Dashboard-Standards (HAZION Design)
Globales Layout
Titel: "HAZION EMBEDDED SYSTEM"

Modi-Buttons: "Mikroskop-Modus", "Spektrum-Modus", "Klimadaten-Modus"

Dateianzeige: Unter dem Viewport wird immer der aktuell generierte oder geladene Dateiname angezeigt.

Status-LEDs (Ampelsystem)
Spektrum-Ingest (Watchdog):

🟢 Grün: Datei erfolgreich erkannt, verarbeitet und gespeichert.

🔴 Rot: Warte auf Datei / Schreibfehler.

Klima-System:

🟢 Grün: Heartbeat OK, Werte innerhalb der Toleranz.

🔴 Rot: Sensor-Timeout (>5s) oder kritische Werte.

Mikroskop-System:

🟢 Grün: Pipeline "PLAYING".

🔴 Rot: Pipeline-Fehler / Kamera nicht gefunden.

Mikroskop-Overlay (Auto-Cal)
Sichtbarkeit: Nur im "Mikroskop-Modus" aktiv.

Logik: 1mm Maßstab, der dynamisch skaliert wird basierend auf der gewählten Vergrößerung (Kalibrierungswert aus JSON).

Kalibrierung: Einmaliges Einmessen per Lineal pro Objektiv nötig.

Klimadaten-Display
Keine Konsole mehr. Darstellung als Digital Readout Cards:
Temperatur 1 (°C) | Temperatur 2 (°C)

Luftfeuchte 1 (%) | Luftfeuchte 2 (%)

Gas-Sensor (ppm)
________________________________________
5. Vollständiger Projektplan: Lab_station_v2
📦 AP 1: Infrastruktur & Environment (Abgeschlossen)
●	[x] Verzeichnisstruktur auf NVMe SSD gehärtet.
●	[x] ZRAM deaktiviert und 16GB Swapfile auf NVMe angelegt.8
●	[x] NumPy-ABI Konflikt gelöst (numpy==1.26.4, pandas<2.2.2).
📦 AP 1.5: System-Härtung (Abgeschlossen)
●	[x] Firewall (UFW) aktiv: Ports 22 (SSH) und 5000 (Flask) offen.9
●	[x] SSH-Hardening (PermitRootLogin no) und Fail2Ban aktiv.
●	[x] Flask-Audit: debug=False und Silent-Logging verifiziert.
📦 AP 2: Backend Core – DataManager & Sensoren (Abgeschlossen)
●	[x] DataManager (Singleton): Thread-safe Implementierung mit threading.Lock.
●	[x] Sensor-Bridge: Polling (Intervall: 2s) und Logging in /data/klimadaten/.
●	[x] Smart Watchdog: Reagiert nur auf on_moved-Events von WinSCP.10
📦 AP 3: Backend Processing – Vision & UV-VIS (Abgeschlossen)
●	[x] Stellarnet Parser: Support für .abs, .trm und .ssm Dateien.11
●	[x] GStreamer Integration: Hardware-beschleunigte Pipeline via nvv4l2decoder.13
●	[x] Memory-Hygiene: Aktives gc.collect() nach Plot-Aktionen.15
📦 AP 4: UI-Präzision (Abgeschlossen)
●	[x] 1mm-Maßstab Overlay: Dynamische Zentrierung des Textes.
●	[x] Naming Scheme Validator: Regex-basierte Validierung im DataManager.
📦 AP 5: Frontend – Dashboard (Abgeschlossen)
●	[x] 3-Mode-Toggle: Nahtlose Umschaltung via Vanilla JS ohne Stream-Abriss.
●	[x] AJAX-Polling: Live-Update der Sensorwerte und Spektren-Grafiken (Base64).

Offene Arbeitspakete (v2.1 Upgrade)
📦 AP 6: Architektur-Fix (SSE & Realtime)
[ ] BUGFIX: DataManager.update_sensors auf 5 Parameter erweitern 
[ ] Refactoring app.py: Umstellung von AJAX Polling auf Server-Sent Events (SSE) /stream.

[ ] Frontend: Implementierung EventSource in JS für verzögerungsfreie Datenupdates (Lösung des Problems "fehlende Daten").

[ ] Sensor-Bridge: Parsing des neuen Arduino-Strings (csv: T1,T2,RH1,RH2,Gas) und Push in den SSE-Kanal.

📦 AP 7: Frontend Logic & Naming Engine
[ ] Dashboard-Header: Titel auf "HAZION EMBEDDED SYSTEM" ändern.

[ ] Dropdown-Logik: JS-Funktion erstellen, die bei Änderung von TYP/LICHT/POL sofort den Dateinamen neu generiert (updateFileName()).

[ ] Regex-Validator: Client-seitige Sperre des "Speichern"-Buttons, wenn ID oder POS ungültige Zeichen enthalten.

📦 AP 8: Mikroskopie & Auto-Cal
[ ] Canvas Overlay: Implementierung eines HTML5 Canvas über dem Videostream.

[ ] Kalibrierungs-Logik: Erstellung calibration.json. Mapping von Dropdown-Auswahl (z.B. "Objektiv 10x") auf Pixel-Faktor.

[ ] Visibility: Overlay wird per JS ausgeblendet, wenn nicht im Mikroskop-Modus.

📦 AP 9: Status-LEDs & Monitoring
[ ] CSS-LEDs: Erstellung der Klassen .led-green, .led-red, .led-blink.

[ ] Watchdog-Verdrahtung: Backend file_monitor.py muss Event an SSE senden -> Frontend schaltet LED auf Grün.

[ ] Sensor-Panel: HTML-Grid für die 5 Sensorwerte (T1, T2, RH1, RH2, Gas) erstellen und mit SSE-Daten füttern.

📦 AP 10: File-Browser & Re-Ingest
[ ] API: Endpunkt /api/files/<type> erstellen (listet Dateien aus /data/ JSON-formatiert).

[ ] UI-Tabelle: Sortierbare Tabelle im Dashboard zum Durchsuchen alter Aufnahmen/Logs.

[ ] Lade-Funktion: Klick auf Datei lädt Bild in den Canvas bzw. Spektrum in den Plotter und setzt den Dateinamen-Text.
________________________________________
6. System-Steuerung (Aliase)
Alias	Funktion
systemstart	Startet Flask, Watchdog und Sensor-Threads zentral via app.py
systemreset	Beendet Flask-Prozesse, leert Port 5000 und triggert udev
ramcheck	Zeigt Top-Memory-Consumer (Python) auf dem Jetson
caminfo	Listet V4L2 Formate der Kamera (v4l2-ctl --list-formats-ext)
systemaus	Fährt den Jetson sicher herunter
