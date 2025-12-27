📋 Projekt-Dokumentation: Lab_station_v1 (V_02)
Status: Aktiv / GUI Fertiggestellt

Hardware: Jetson Board, USB-Kamera (V4L2), Arduino (Sensor-Bridge)

📂 1. Verzeichnisstruktur
Alle Dateien befinden sich im Hauptverzeichnis zur Vermeidung von Pfadfehlern:

~/inspection_project/

lab_station_v1.py – Hauptprogramm (Backend: Flask, CV2, Serial)

index.html – Benutzeroberfläche (Frontend: HTML, CSS, JS)

spec_watcher.py – Hintergrunddienst für Spektrometer-Daten

README.md – Diese Dokumentation

/data/ – Zentraler Datenspeicher

/mikroskopbilder/ – JPG-Aufnahmen

/spektren/ – CSV/Txt Spektrendaten

/logs/ – JSON-Metadaten zu Snapshots

🚀 2. System-Steuerung (Aliase)
Bedienung über das Terminal mittels vordefinierter Kurzbefehle:

Projekt-Management
system_start : Startet Backend & Spec-Watcher (Headless/Background)

system_reset : Killt Prozesse auf Port 5000 & resetet USB-Ports (udev)

system_aus : Fährt den Jetson sicher herunter

system_reboot: Startet das System neu

Jetson-Optimierung
monitor_aus : Deaktiviert Desktop-GUI (spart RAM) -> Reboot in Konsole

monitor_an : Aktiviert Desktop-GUI -> Reboot in Desktop-Modus

ram_check : Zeigt die Top 10 RAM-Verbraucher (Fokus auf Node/Background)

Daten-Zugriff
mikroskopbilder : Schnelle Liste aller gespeicherten Bilder

spektren : Schnelle Liste aller Spektren-Dateien

🎨 3. UI-Spezifikationen & Design
Design: Rein schwarzer Hintergrund, weiße Schrift.

Präzision: Sensorwerte mit exakt zwei Leerzeichen nach dem Doppelpunkt (Temperatur: 24.5°C).

Buttons: Beschriftung in Großbuchstaben (BILDDATEI SPEICHERN).

📏 4. Mess- & Speicherlogik
1mm-Maßstab:

Position: Unten rechts im Bild.

Label: "1 mm" steht exakt mittig über der Linie zentriert.

Funktion: Nur im "Freeze"-Modus zur Referenzierung eingeblendet.

Namensschema:

Format: Zeit_Typ_ID_Position.jpg

Beispiel: 20251226_1300_UV_001_A.jpg

🛠 5. Wartung
Nach Änderungen an der .bashrc immer source ~/.bashrc ausführen.

Bei Hardware-Hängern (Kamera/Sensoren) zuerst system_reset nutzen.

Das Backend findet die index.html automatisch im selben Verzeichnis via os.path.abspath.

🚧 6. Offene Punkte / To-Do
Silent Logging umsetzen: Das Flask-Terminal spammt aktuell noch 200 OK Nachrichten. Dies muss noch auf logging.ERROR (Silent Mode) umgestellt werden, um die Shell übersichtlich zu halten. Maßstab muss entsprechend der Vergrößerung kalibriert werden da aktuell eine Einpunktkalibrierung vor Messbeginn eingemessen werden muss und bei anpassen der Vergrößerung dieser dann nicht mehr stimmt.

Entwickler-Notiz: Pragmatische Struktur. Trennung von Backend und Frontend ist zwingend. Code muss im Code exakt beschrieben sein