Projekt-Dokumentation: Lab_station_v2
Version: 2.0 (Stable)
Status: AP 1 - AP 5 vollständig abgeschlossen
Plattform: NVIDIA Jetson Orin Nano (8GB Unified Memory)
________________________________________1. System-Übersicht
Kombiniertes Inspektionssystem für Mikroskopie, UV-VIS Spektrometrie und kontinuierliche Umgebungsüberwachung. Das System ist für den 24/7-Dauerbetrieb ausgelegt und nutzt die Hardware-Beschleunigung des Jetson Orin Nano zur Entlastung der CPU.
●	Architektur: Modularer "Monolith" mit Flask-Backend und Vanilla JS Frontend.
●	Daten-Ingestion: Automatisierte Übernahme von Spektren via WinSCP (Smart Watchdog-Prinzip für .filepart Support).
●	Performance-Ziel: Maximale RAM-Effizienz durch Thread-Safe Singleton State Management (DataManager) und manuelle Garbage Collection (gc.collect()) nach speicherintensiven Plot-Operationen.1
________________________________________2. Verzeichnisstruktur (Finaler Zustand v2)
Betriebssystem und Daten liegen auf einer dedizierten NVMe SSD, um die SD-Karte vor Verschleiß durch Schreibzyklen (Swap/Logs) zu schützen.3
A. Projekt-Verzeichnis (Anwendungslogik)
~/inspection_project/
├── README.md # Diese Dokumentation
├── src/ # Quellcode (App-Logik)
│ ├── app.py # Flask Server (Haupteinstiegspunkt)
│ ├── config.py # Zentrale Konfiguration & Naming Schemes
│ ├── data_manager.py # Thread-Safe Singleton (State Management)
│ ├── file_monitor.py # Smart Watchdog (WinSCP-Überwachung)
│ ├── sensor_bridge.py # I2C/Arduino Sensor-Thread
│ ├── camera_engine.py # GStreamer Video-Pipeline (HW-beschleunigt)
│ └── spectrum_processor.py # Stellarnet Parser & Plotter (Agg-Backend)
└── templates/ # Dashboard Frontend
└── index.html # 3-Mode Dashboard (Vanilla JS)
B. Daten-Verzeichnis (NVMe SSD Partition)
/data/
├── x200_rohdaten_eingang/ # Drop-Zone für WinSCP (.filepart Support)
├── mikroskopbilder/ # Bildarchiv (Striktes Naming Scheme)
├── spektren/ # Spektrenarchiv (.abs,.trm,.ssm)
├── klimadaten/ # Kontinuierliche Sensor-Logs (CSV)
└── logs/ # Systemlogs (Flask Level: ERROR)
________________________________________3. Das Naming Scheme (Strikte Validierung)
Jede Datei wird vor dem Speichern gegen folgende Muster geprüft 4:
●	Mikroskopiebild: YYYYMMDD_HHMMSS_TYP_ID_POS_Licht_Pol_EXT
●	Spektrum: YYYYMMDD_HHMMSS_TYP_ID_POS_Modus_EXT
●	Klimadaten: LOG-Zeitraum_Bezeichnung_Ortsangabe_ID_EXT
Variablen:
●	TYP: Bohrprobe (B), Wischprobe (W), Material (M), Referenz (R)
●	Modus: ABS (Absorbance), TRANS (Transmission), SCOPE (Scope Mode)
●	Licht: Ring (R), Coax (C), Side (S), Off (O) | Pol: an (1), aus (0)
________________________________________4. UI- & Grafik-Standards
●	Sensor-Readouts: Exakt zwei Leerzeichen nach dem Doppelpunkt (z.B. Temperatur: 24.5°C).
●	1mm-Maßstab: Unten rechts im Videobild; das Label wird via cv2.getTextSize exakt mittig über der skalierten Linie zentriert.
●	Mathematische Zentrierung:
$P_{line} = \frac{1000 \mu m}{C_{cal}}$
$X_{text} = X_{line\_center} - \frac{W_{text}}{2}$
●	Logging: Flask-Logs sind auf Level ERROR begrenzt (Silent Mode zur SSD-Schonung).7
________________________________________5. Vollständiger Projektplan: Lab_station_v2
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
________________________________________6. System-Steuerung (Aliase)
Alias	Funktion
systemstart	Startet Flask, Watchdog und Sensor-Threads zentral via app.py
systemreset	Beendet Flask-Prozesse, leert Port 5000 und triggert udev
ramcheck	Zeigt Top-Memory-Consumer (Python) auf dem Jetson
caminfo	Listet V4L2 Formate der Kamera (v4l2-ctl --list-formats-ext)
systemaus	Fährt den Jetson sicher herunter
