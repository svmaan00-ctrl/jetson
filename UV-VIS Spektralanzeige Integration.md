Projektstruktur: Lab_station_v2 Upgrade

📦 AP 1: Infrastruktur & Environment Setup
Ziel: Vorbereitung der Umgebung auf dem Jetson, um Schreibkonflikte und Pfad-Fehler zu vermeiden.

Verzeichnisstruktur härten:

Anlegen von /data/x200_rohdaten_eingang/ (Nur Lese-Rechte für Flask, Schreibrechte für WinSCP-User).

Anlegen von /data/archived_spectra/ und /data/saved_snapshots/.

WinSCP-Konfiguration validieren:

Verifizierung der Client-Einstellung "Transfer to temporary filename" (Erzeugung von .filepart), um die Atomarität sicherzustellen.

Bibliotheken:

Installation von watchdog und opencv-python-headless (Wichtig: Headless-Version auf Jetson nutzen, um X11-Konflikte zu vermeiden).

📦 AP 2: Backend Core – Ingestion & State Management
Ziel: Robuste Erkennung neuer Dateien ohne Blockieren des Haupt-Threads (Global State Manager).

Global State Manager (Singleton):

Implementierung der Klasse DataManager in src/data_manager.py.

Einbau von threading.Lock() für thread-sicheren Zugriff auf den aktuellen DataFrame und Status.

Watchdog-Service:

Implementierung des PatternMatchingEventHandler in src/file_monitor.py.

Logik: Ignorieren von .filepart. Trigger nur bei on_moved (wenn Umbenennung zu .csv erfolgt) oder on_created (ohne .filepart).

Integration des "Debouncing" (kurze Wartezeit), falls das Dateisystem noch Metadaten schreibt.

📦 AP 3: Backend Processing – Parsing & Rendering
Ziel: Umwandlung von CSV-Rohdaten in valide Plots, isoliert vom Video-Stream.

CSV-Parser (Pandas):

Entwicklung der Header-Erkennungslogik (Suche nach Keywords "Wavelength"/"Absorbance" in den ersten 20 Zeilen).

Implementierung der pd.read_csv Logik mit Fehlerbehandlung für "schmutzige" CSVs.

Plotting Engine (Matplotlib):

Konfiguration des Agg-Backends (Headless Rendering).

Erstellung der Funktion create_plot(), die ein PNG als Byte-Stream (io.BytesIO) zurückgibt.

Caching: Implementierung, dass der Plot nur neu berechnet wird, wenn sich der Zeitstempel der Quelldatei ändert.

📦 AP 4: Backend API & Video Stream (Flask)
Ziel: Bereitstellung der Endpunkte für das Frontend und Zusammenführung der Subsysteme.

Video-Route (/video_feed):

Bestehenden MJPEG-Generator beibehalten.

Reminder: Sicherstellen, dass das 1mm-Skala-Overlay im Video-Stream erhalten bleibt (Bottom-Right, zentriertes Label).

Spektrum-Route (/spectrum_plot.png):

Auslieferung des gecachten PNGs aus AP 3.

Steuerungs-API:

/api/status: JSON-Response mit aktuellem Dateinamen und Timestamp (für Polling).

/api/save: Implementierung der Kontext-Logik. Unterscheidung anhand des JSON-Payloads (context: 'video' vs. context: 'spectrum').

Naming Scheme: Durchsetzung des Schemas Time_Type_ID_... beim Speichern/Archivieren.

📦 AP 5: Frontend – Dashboard & Interaktion
Ziel: Sauberes HTML/JS Interface ohne externe Frameworks (Vanilla JS).

Layout & UI:

Anpassung der index.html.

Implementierung des "Toggle Switch" (CSS Checkbox) zum Umschalten zwischen Video und Plot.

Präzision: Sicherstellen, dass Sensor-Readouts (falls vorhanden) exakt formatiert sind (zwei Leerzeichen nach Doppelpunkt).

State Machine (JS):

Logik für currentMode (Video vs. Spektrum).

Video-Modus: Setzen von src="/video_feed".

Spektrum-Modus: Setzen von src="/spectrum_plot.png" und Starten des Pollings (setInterval) auf /api/status.

Implementierung des Cache-Busting (?t=...) beim Neuladen des Plots.

Save-Button:

Anbindung an fetch('/api/save') mit dynamischem Kontext-Payload.

📦 AP 6: Integration & Logging
Ziel: Systemstabilität und Fehlerverfolgung.

Logging-Konfiguration:

Flask-Logging auf ERROR beschränken (Silent Logs).

Separates File-Logging für den Watchdog (z.B. "Neue CSV erkannt", "Parsing Fehler").

Integrationstest:

Testen des "Race Conditions"-Szenarios: Upload einer großen CSV via WinSCP bei gleichzeitigem Video-Streaming.

Testen der Toggle-Logik: Stoppt der Video-Traffic im Browser wirklich, wenn auf Spektrum geschaltet wird?



Technische Spezifikation und Implementierungsbericht: Erweiterung der Laborstation V1 zur UV-VIS-Spektroskopie-Integration

1. Management Summary und Projektdefinition

1.1 Einführung und ZielsetzungDie vorliegende technische Ausarbeitung dokumentiert die umfassende Erweiterung der bestehenden lab_station_v1-Architektur. Das primäre Ziel dieses Upgrades besteht darin, die Funktionalität der Station von einer reinen visuellen Überwachungseinheit zu einem multi-modalen Analyseinstrument zu transformieren. 

Im Zentrum steht die Integration von UV-VIS-Spektroskopiedaten (Ultraviolett-Visible Spectroscopy), die asynchron über das Netzwerkprotokoll WinSCP in Form von CSV-Dateien (Comma-Separated Values) in das System eingespeist werden.Diese Erweiterung ist nicht nur ein additiver Prozess, sondern erfordert eine fundamentale Umstrukturierung der internen Datenverarbeitungslogik. Die Anforderung, eine "Umschalt-Logik" (Toggle Logic) im Dashboard bereitzustellen, impliziert den Übergang von einem statischen Single-View-System zu einem dynamischen Multi-Context-System. Der Benutzer muss in der Lage sein, nahtlos zwischen der Echtzeit-Videoüberwachung der Probe und der analytischen Darstellung des Absorptionsspektrums zu wechseln. 

Darüber hinaus fordert die "kontextsensitive Speicherung", dass das System intelligent genug ist, um die Intention des Benutzers basierend auf dem aktuellen Ansichtsmodus zu interpretieren – sei es das Einfrieren eines Videoframes oder die Archivierung eines komplexen spektralen Datensatzes.Der Bericht analysiert die technischen Herausforderungen, die sich aus der Kollision von Echtzeit-Streaming (Video) und ereignisgesteuerter Dateiverarbeitung (Spektrum) ergeben, und schlägt eine robuste, auf Micro-Services basierende Architektur innerhalb eines monolithischen Flask-Frameworks vor. Besonderes Augenmerk liegt auf der Datenintegrität während des WinSCP-Transfers und der Thread-Sicherheit bei der serverseitigen Generierung von Spektralplots.

1.2 Kernanforderungen und LösungsansatzDie Analyse der Anforderungen führt zu vier technologischen Säulen, die das Fundament der lab_station_v2 bilden:Asynchrone Daten-Ingestion: Implementierung eines robusten Dateiüberwachungsdienstes (File Monitoring Daemon), der das Verzeichnis /data/x200_rohdaten_eingang überwacht. Hierbei muss spezifisch auf die temporären Dateinamenkonventionen von WinSCP (z.B. .filepart) eingegangen werden, um Race Conditions und den Zugriff auf korrupte, unvollständige Dateien zu verhindern.

1.3 Server-Side Rendering (SSR) für Spektraldaten: Nutzung der Matplotlib-Bibliothek im "Headless"-Modus (Agg-Backend) zur Generierung von hochauflösenden Plots aus den CSV-Rohdaten. Dies erfordert eine strikte Trennung vom Haupt-Thread der Webanwendung, um Blockaden des Video-Streams zu vermeiden.3Hybrides Dashboard-Interface: Entwicklung einer Frontend-Logik mittels HTML5 und Vanilla JavaScript, die den Zustand der Anwendung (Video vs. Spektrum) verwaltet und via Fetch-API mit dem Backend kommuniziert.Kontextabhängige Persistenz: Ein logischer Layer im Backend, der Save-Requests entgegennimmt, den aktuellen Kontext prüft und entweder cv2.imwrite (für Video) oder Datei-Operationen (für CSV-Archivierung) auslöst.5

2. Systemarchitektur und Design-Prinzipien

2.1 Theoretischer Rahmen: Ereignisgesteuert vs. AnfragegesteuertDie größte architektonische Herausforderung bei der Erweiterung der lab_station_v1 liegt in der Divergenz der Datenquellen.Video-Subsystem: Dieses arbeitet synchron und anfragegesteuert. Der Client (Browser) fordert einen kontinuierlichen Strom von Daten an. Der Server muss permanent Frames liefern, solange die Verbindung besteht.Spektral-Subsystem: Dieses arbeitet asynchron und ereignisgesteuert. Der Zeitpunkt, zu dem ein neues Spektrum verfügbar ist, wird extern durch den WinSCP-Upload bestimmt. Der Server muss auf dieses Ereignis reagieren (Reactivity), ohne dass der Client explizit danach fragt, und den neuen Zustand bereithalten.Um diese Diskrepanz aufzulösen, wird ein Global State Manager (GSM) eingeführt. Dieser fungiert als Singleton-Instanz innerhalb der Flask-Applikation und hält den aktuellen Zustand des Systems (z.B. letzter bekannter CSV-Pfad, gecachtes Plot-Bild, Zeitstempel der letzten Änderung). Die Web-Handler (Routes) greifen lediglich lesend auf diesen GSM zu, während Hintergrund-Threads (Watchdog) schreibend darauf zugreifen.

2.2 Verzeichnisstruktur und Datenfluss: Eine klare Definition der Verzeichnisstruktur ist essentiell für die Stabilität des Watchdog-Dienstes und die Sicherheit der Daten. Der Datenfluss wird streng unidirektional konzipiert, um Schreibkonflikte zu vermeiden.Verzeichnisstruktur:/opt/lab_station/: Programmcode und statische Assets./data/x200_rohdaten_eingang/: Drop-Zone. Hier hat der WinSCP-User Schreibrechte. Die Flask-Applikation hat hier ausschließlich Leserechte (Read-Only), um versehentliches Löschen zu verhindern./data/archived_spectra/: Archiv-Zone. Hierhin werden CSV-Dateien verschoben oder kopiert, sobald der Benutzer die kontextsensitive Speicherung auslöst./data/saved_snapshots/: Media-Zone. Speicherort für Videoframes.Datenfluss-Diagramm (Textuell):Quelle: UV-VIS Spektrometer PC -> WinSCP Upload -> /data/x200_rohdaten_eingang.Trigger: Watchdog erkennt MOVED_TO Ereignis (Umbenennung von .filepart zu .csv).Verarbeitung: Python-Thread parst CSV -> Validiert Daten -> Rendert Plot -> Speichert Plot im RAM (BytesIO).Präsentation: Dashboard pollt Status -> Lädt neues Bild via HTTP GET.Aktion: Nutzer klickt "Speichern" -> Backend kopiert CSV von /data/x200... nach /data/archived....

3. Das Ingestion-Subsystem: WinSCP und WatchdogDie Zuverlässigkeit der gesamten Anwendung steht und fällt mit der Fähigkeit, ankommende Dateien korrekt zu erkennen. Eine naive Implementierung, die lediglich auf die Existenz einer Datei prüft, würde bei großen Transfers scheitern, da der Leseprozess beginnen könnte, während WinSCP noch Daten schreibt.

3.1 WinSCP Übertragungsmechanik und Atomarität: WinSCP verwendet standardmäßig Mechanismen, um die Integrität von Dateiübertragungen zu gewährleisten, insbesondere bei instabilen Netzwerkverbindungen. Das Verständnis dieser Mechanismen ist entscheidend für die Konfiguration des Watchdog-Listeners.

3.1.1 Die .filepart ProblematikWenn WinSCP eine Datei überträgt, wird diese am Zielort (auf der lab_station) zunächst mit einem temporären Namen erstellt, typischerweise durch Anhängen der Endung .filepart an den ursprünglichen Dateinamen.2Beispiel: Der Upload von spektrum_probe_A.csv erscheint im Dateisystem als spektrum_probe_A.csv.filepart.Erst wenn der Transfer des binären Datenstroms vollständig abgeschlossen ist und der Server den Empfang aller Pakete bestätigt hat, führt WinSCP eine Umbenennungsoperation (Rename) durch, um die Endung .filepart zu entfernen.Dieses Verhalten ist für unser System von Vorteil, da die Umbenennung auf den meisten modernen Dateisystemen (ext4, NTFS) eine atomare Operation darstellt. Das bedeutet, die Datei existiert unter ihrem finalen Namen (.csv) erst in dem Moment, in dem sie vollständig und valide ist.6

3.1.2 KonfigurationsempfehlungUm sicherzustellen, dass dieses Verhalten deterministisch auftritt, muss auf der Client-Seite (dem PC, der WinSCP ausführt) sichergestellt werden, dass die Option "Transfer to temporary filename" (Übertragung in temporäre Datei) in den Einstellungen unter "Endurance" (Ausdauer) aktiviert ist. Wäre diese Option deaktiviert, würde die Datei sofort unter dem Namen .csv wachsen, was komplexe Sperrmechanismen (File Locking) auf Serverseite erfordern würde, um Lesezugriffe auf unfertige Dateien zu verhindern.8

3.2 Watchdog ImplementierungFür die Überwachung des Verzeichnisses /data/x200_rohdaten_eingang verwenden wir die Python-Bibliothek watchdog. Diese abstrahiert die betriebssystemspezifischen APIs (wie inotify unter Linux oder ReadDirectoryChangesW unter Windows).1

3.2.1 Der PatternMatchingEventHandlerAnstatt alle Ereignisse im Ordner zu überwachen, implementieren wir eine spezialisierte Klasse, die von PatternMatchingEventHandler oder FileSystemEventHandler erbt. Die Logik muss filtern, welche Ereignisse relevant sind.Relevante Ereignisse:on_moved: Dies ist das primäre Signal für einen erfolgreichen WinSCP-Upload mit .filepart-Konfiguration. Wir überwachen das Ziel des Verschiebevorgangs (dest_path). Wenn dest_path auf .csv endet, ist die Datei fertig.on_created: Dies dient als Fallback, falls eine Datei lokal kopiert wird oder WinSCP so konfiguriert ist, dass es keine temporären Dateien für sehr kleine Dateien verwendet. Hier müssen wir jedoch vorsichtig sein und explizit prüfen, dass die Datei nicht auf .filepart endet.10Ignorierte Ereignisse:on_modified: Während des Uploads feuert das Betriebssystem kontinuierlich modified-Events für die .filepart-Datei. Diese müssen strikt ignoriert werden, um eine Überlastung des Parsers zu verhindern.

3.2.2 Latenz und Debouncing: In seltenen Fällen kann es vorkommen, dass nach dem Umbenennen (on_moved) noch Metadaten-Operationen (wie das Setzen des Zeitstempels) stattfinden. Es ist daher ratsam, eine minimale Verzögerung (Debounce) von wenigen Millisekunden einzubauen oder den Datei-Zugriff in einen try-except-Block zu kapseln, der bei einem "File Locked"-Fehler kurz wartet und es erneut versucht.1

4. Datenverarbeitungspipeline: CSV Parsing und ValidierungSobald der Watchdog eine valide Datei meldet, übergibt er den Dateipfad an den DataManager. Dieser ist verantwortlich für das Einlesen (Parsing) und die Validierung der Daten.4.1 Robustes Parsing mit PandasCSV-Dateien aus Laborgeräten sind selten perfekt formatierte Tabellen. Oft enthalten sie Metadaten-Header (Gerätename, Datum, Operator), die vor den eigentlichen Messdaten stehen. Ein starrer Parser würde hier scheitern.Flexible Header-Erkennung:Wir nutzen pandas für das Parsing. Um die Robustheit zu erhöhen, implementieren wir eine Logik, die den Header dynamisch sucht.

4.1 Die Strategie:Einlesen der ersten 20 Zeilen der Datei als rohen Text.Suche nach Schlüsselwörtern wie "Wavelength", "Wellenlänge", "nm" oder "Absorbance".Identifikation der Zeilennummer, in der diese Schlüsselwörter vorkommen.Nutzung dieser Zeilennummer als header-Parameter für pd.read_csv.Falls keine Header gefunden werden, Versuch, die Datei ohne Header (header=None) zu lesen und anzunehmen, dass Spalte 0 die X-Achse und Spalte 1 die Y-Achse ist.

4.2 Datenvalidierung und SanitizationBevor die Daten visualisiert werden, müssen sie validiert werden, um Fehler im Dashboard zu vermeiden.Numerische Integrität: Sicherstellen, dass die Spalten tatsächlich Zahlen enthalten. pd.to_numeric(..., errors='coerce') wandelt nicht-numerische Werte in NaN um, die anschließend entfernt werden können.Bereichsprüfung: UV-VIS Daten haben typische Bereiche (z.B. 190nm bis 1100nm). Werte außerhalb plausibler Grenzen könnten auf einen Einheitenfehler hindeuten, sollten aber i.d.R. angezeigt werden (eventuell mit Warnhinweis).Leere Daten: Wenn das DataFrame nach der Bereinigung leer ist, muss der Status "Fehlerhafte Datei" gesetzt werden, anstatt einen leeren Plot zu generieren.Parsing SchrittMethode / FunktionZielHeader-Suchereadlines() + RegexStartzeile der Daten findenLadenpd.read_csv(skiprows=N)DataFrame erstellenTyp-Konversionpd.to_numericString-Fragmente entfernenBereinigungdf.dropna()Lückenhafte Messreihen fixen5. Visualisierungs-Engine: Matplotlib im Server-KontextDie Generierung der Spektralkurven erfolgt serverseitig. Dies entlastet den Client (Browser) und stellt sicher, dass die Darstellung konsistent ist, unabhängig von der Rechenleistung des Endgeräts.

5.1 Das Backend-Problem: GUI vs. HeadlessMatplotlib ist standardmäßig oft so konfiguriert, dass es versucht, ein Fenster zu öffnen (z.B. mit dem TkAgg oder Qt5Agg Backend). In einer Serverumgebung (wie Flask), die oft ohne Monitor (headless) läuft, führt dies zu einem sofortigen Absturz (TclError: no display name).Zudem ist das pyplot-Interface (state-based) nicht thread-sicher. Wenn zwei Web-Requests gleichzeitig plt.plot() aufrufen, würden sie in denselben globalen Status schreiben, was zu vermischten oder fehlerhaften Grafiken führt.

5.2 Die Objekt-Orientierte Lösung (OO-API)Für lab_station_v2 ist die Verwendung der objektorientierten API von Matplotlib zwingend erforderlich. Hierbei werden Figure- und Axes-Objekte explizit instanziiert und sind lokal im Scope der Funktion isoliert.Das Backend muss explizit auf Agg (Anti-Grain Geometry) gesetzt werden, welches ein reines Raster-Backend ist und PNG-Daten im Speicher erzeugt.

Implementierungsmuster:Pythonfrom matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

def create_plot(dataframe):
    # Isolierte Instanz - Thread Safe
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.plot(dataframe['wavelength'], dataframe['absorbance'])
    
    # Rendering in den RAM
    output = io.BytesIO()
    FigureCanvasAgg(fig).print_png(output)
    return output.getvalue()

5.3 Performance-Optimierung und CachingDas Rendern eines PNGs mittels Matplotlib ist eine CPU-intensive Operation (ca. 50-200ms je nach Komplexität). Würde bei jedem Neuladen des Dashboards das Bild neu berechnet, würde dies unnötige Last erzeugen.Caching-Strategie: Der DataManager speichert das generierte PNG-Byte-Objekt. Solange keine neue CSV-Datei via WinSCP eintrifft, liefert der Webserver bei Anfragen an /spectrum_plot.png einfach das gecachte Byte-Objekt aus. Dies reduziert die Latenz für den Client auf nahezu Null und schont die CPU für den Video-Stream.

6. Video-Subsystem: Echtzeit-StreamingWährend die Spektralanalyse statisch ist, erfordert der Video-Modus hohen Durchsatz und niedrige Latenz.

6.1 Protokollwahl: MJPEG über HTTPFür Laboranwendungen, bei denen die Latenz (Verzögerung zwischen Realität und Bild) kritischer ist als die Bandbreiteneffizienz, ist MJPEG (Motion JPEG) oft die beste Wahl gegenüber H.264/H.265 Streaming (wie via RTSP).Vorteil MJPEG: Jedes Bild ist ein unabhängiges JPEG. Es gibt kein Inter-Frame-Buffering (P-Frames, B-Frames), was die Latenz minimiert. Browser können MJPEG nativ ohne zusätzliche Bibliotheken darstellen.Implementierung: Flask nutzt hierfür "Multipart Responses" (multipart/x-mixed-replace). Ein Generator liefert kontinuierlich Byte-Chunks, die durch Boundaries getrennt sind.

6.2 Hardware-Abstraktion (OpenCV)Die Bilderfassung erfolgt über OpenCV (cv2).Wichtiger Hinweis für Embedded Systeme (Jetson/Raspberry Pi):Falls die lab_station auf einem NVIDIA Jetson Nano läuft, kann es Konflikte zwischen OpenCV und dem Headless-Betrieb geben. Standardmäßige opencv-python Pakete enthalten oft Abhängigkeiten zu X11/GTK. Es wird dringend empfohlen, opencv-python-headless zu verwenden, um Fehler zu vermeiden und den Footprint zu reduzieren.

6.3 Konfliktvermeidung: Der Global Interpreter Lock (GIL)Python erlaubt immer nur einem Thread die Ausführung von Bytecode (GIL).Konflikt: Ein schwerer Render-Prozess (Matplotlib) könnte den Video-Stream-Generator kurzzeitig blockieren, was zu Rucklern führt.Lösung: Da wir Matplotlib-Plots cachen und nur bei neuen Dateien (seltenes Ereignis) neu berechnen, ist der Konflikt minimiert. Sollte die Berechnung dennoch zu lange dauern, müsste der Render-Prozess in einen separaten multiprocessing.Process ausgelagert werden. Für die typische CSV-Größe in der UV-VIS Spektroskopie (< 1MB) ist dies jedoch meist Over-Engineering; einfaches Threading reicht aus.

7. Web-Frontend und Dashboard-LogikDas Frontend ist die Schnittstelle zum Benutzer. Die Anforderung nach einer "Umschalt-Logik" und "kontextsensitiver Speicherung" verlagert einen Teil der Anwendungslogik in den Browser.

7.1 Dashboard-Design und Toggle-SwitchDas UI sollte minimalistisch sein. Ein zentraler Viewport (Container) zeigt entweder das Video oder das Diagramm.Der Umschalter (Toggle) wird als CSS-gestylte Checkbox realisiert. Dies ist leichtgewichtig und erfordert keine externen Frameworks wie React oder Vue, was die Wartbarkeit erhöht.

7.2 Die "Umschalt-Logik" (Client-Side State Machine)JavaScript verwaltet den Zustand (currentState).Zustand: VIDEODer src-Attribute des <img>-Tags im Viewport zeigt auf die Route /video_feed.Der Browser hält die Verbindung offen und empfängt den MJPEG-Stream.Polling-Intervalle für Spektraldaten sind pausiert, um Netzwerkverkehr zu sparen.Zustand: SPEKTRUMBeim Umschalten wird src geändert auf /spectrum_plot.png.Gleichzeitig wird die Verbindung zum Video-Stream abgebrochen (Browser-Verhalten beim Ändern von src).Ein Polling-Timer (z.B. setInterval alle 2000ms) wird gestartet. Dieser fragt einen leichten API-Endpunkt (/api/status) ab, ob eine neue Datei eingetroffen ist (Vergleich von Zeitstempeln).Falls neue Daten vorliegen: Aktualisierung des src-Attributs mit einem Cache-Buster-Parameter (?t=timestamp), um das Neuladen des Bildes zu erzwingen.

7.3 Kontextsensitive SpeicherungDer "Speichern"-Button hat keine feste Funktion, sondern seine Aktion hängt vom currentState ab.Ablauf beim Klick:JavaScript liest currentState (Video oder Spektrum).Ein asynchroner POST-Request (via Fetch API) wird an /api/save gesendet.Der Payload des Requests enthält den Kontext: JSON.stringify({ context: 'video' }) oder { context: 'spectrum' }.Der Server führt die entsprechende Logik aus und antwortet mit JSON (Erfolg/Fehler).Das Frontend zeigt eine temporäre Benachrichtigung (Toast) an, z.B. "Snapshot gespeichert" oder "Spektrum archiviert".

8. Server-Implementierung (Flask)Der Flask-Server fungiert als Orchestrator. Er initialisiert den Watchdog, verwaltet den globalen Daten-Cache und routet die Anfragen.

8.1 API-DesignDie Routen müssen klar getrennt sein zwischen View-Rendering (HTML), Daten-Streaming (Video/Bild) und Steuerungs-API (JSON).RouteMethodeBeschreibungKontext/GETLädt das Haupt-Dashboard HTML.User/video_feedGETStreamt MJPEG (Infinite Response).Video/spectrum_plot.pngGETLiefert das gerenderte PNG (Cached).Spektrum/api/statusGETLiefert JSON mit Metadaten der aktuellen CSV (Name, Zeit).Polling/api/savePOSTFührt Speicheraktion basierend auf JSON-Body aus.Trigger

8.2 Kontext-Handling im BackendDie Route /api/save implementiert die geforderte kontextsensitive Logik.5Case Video:Zugriff auf das globale Kamera-Objekt.Auslesen eines Einzelbildes (ret, frame = camera.read()).Generierung eines Dateinamens mit Zeitstempel.Schreiben der Datei mittels cv2.imwrite in /data/saved_snapshots.Case Spektrum:Prüfung, ob ein valides DataFrame im DataManager vorliegt.Kopieren der Original-CSV-Datei aus dem Eingangspfad /data/x200_rohdaten_eingang in den Archivpfad /data/archived_spectra.Optional: Speichern des gerenderten PNGs ebenfalls im Archiv.Wichtig: Hier sollte shutil.copy2 verwendet werden, um Metadaten der Datei zu erhalten.

9. Detaillierte ImplementierungsanleitungIm Folgenden werden die kritischen Code-Segmente vorgestellt, die für die Umsetzung der Spezifikation notwendig sind.

9.1 Modul: data_manager.py (Zustandsverwaltung)Dieses Modul ist das Herzstück der Datenhaltung. Es muss Thread-Safe sein.Pythonimport pandas as pd
import threading
import io
import os
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

class DataManager:
    def __init__(self):
        # Lock für Thread-Sicherheit beim Schreiben/Lesen
        self.lock = threading.Lock()
        self.current_df = None
        self.current_filename = "Warte auf Daten..."
        self.last_update_ts = 0
        self.cached_png = None

    def load_csv(self, filepath):
        """Wird vom Watchdog-Thread aufgerufen."""
        with self.lock:
            try:
                # Versuch, die Daten robust zu lesen
                # Annahme: CSV hat Header oder Spalte 0=X, 1=Y
                df = pd.read_csv(filepath)
                
                # Minimale Validierung: Mindestens 2 Spalten
                if df.shape < 2:
                    print(f"Warnung: Datei {filepath} hat ungültiges Format.")
                    return

                # Normalisierung der Spaltennamen für internen Gebrauch
                # Wir nehmen an, die ersten beiden Spalten sind relevant
                df.columns.values = "wavelength"
                df.columns.values = "absorbance"
                
                self.current_df = df
                self.current_filename = os.path.basename(filepath)
                self.last_update_ts = time.time()
                self.cached_png = None # Cache invalidieren
                print(f"Daten geladen: {self.current_filename}")
                
            except Exception as e:
                print(f"Fehler beim Parsen von {filepath}: {e}")

    def get_plot_bytes(self):
        """Wird vom Flask-Thread aufgerufen."""
        with self.lock:
            if self.current_df is None:
                return None
            
            # Cache Hit?
            if self.cached_png:
                return self.cached_png
            
            # Rendering (Agg Backend)
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)
            
            # Plotten der Daten
            x = self.current_df.iloc[:, 0]
            y = self.current_df.iloc[:, 1]
            ax.plot(x, y, label='Absorbance', color='#2980b9')
            
            # Styling
            ax.set_title(f"Spektrum: {self.current_filename}")
            ax.set_xlabel("Wellenlänge (nm)")
            ax.set_ylabel("Absorption (AU)")
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            
            # In Memory Buffer schreiben
            buf = io.BytesIO()
            FigureCanvasAgg(fig).print_png(buf)
            self.cached_png = buf.getvalue()
            
            return self.cached_png

# Globales Singleton
data_store = DataManager()

9.2 Modul: file_monitor.py (Watchdog)Pythonfrom watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os
from data_manager import data_store

class WinSCPHandler(FileSystemEventHandler):
    def _process(self, filepath):
        filename = os.path.basename(filepath)
        # Filter: Nur CSVs, keine temporären.filepart Dateien
        if filename.endswith('.csv') and not filename.endswith('.filepart'):
            data_store.load_csv(filepath)

    def on_moved(self, event):
        # Kritisch für WinSCP: Umbenennung von.filepart ->.csv
        if not event.is_directory:
            self._process(event.dest_path)

    def on_created(self, event):
        # Fallback für direkte Kopien
        if not event.is_directory:
            # Kurzes Warten, falls Datei noch gesperrt (Race Condition Mitigation)
            time.sleep(0.5)
            self._process(event.src_path)

def start_watcher(path):
    handler = WinSCPHandler()
    observer = Observer()
    observer.schedule(handler, path, recursive=False)
    observer.start()
    return observer

9.3 Modul: app.py (Flask Server)Pythonfrom flask import Flask, render_template, Response, request, jsonify
import cv2
import os
import shutil
import time
from data_manager import data_store
from file_monitor import start_watcher

app = Flask(__name__)

# Konfiguration
INPUT_DIR = "/data/x200_rohdaten_eingang"
ARCHIVE_DIR = "/data/archived_spectra"
SNAPSHOT_DIR = "/data/saved_snapshots"

# Sicherstellen, dass Verzeichnisse existieren
for d in:
    os.makedirs(d, exist_ok=True)

# Kamera Initialisierung
camera = cv2.VideoCapture(0) # Index 0 ist meist die Standard-USB-Kamera

def generate_video_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        # JPEG Encoding
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        # Multipart Frame Yield
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_video_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/spectrum_plot.png')
def spectrum_plot():
    img_data = data_store.get_plot_bytes()
    if img_data:
        return Response(img_data, mimetype='image/png')
    return Response("Keine Daten", mimetype='text/plain', status=404)

@app.route('/api/status')
def api_status():
    return jsonify({
        "filename": data_store.current_filename,
        "timestamp": data_store.last_update_ts
    })

@app.route('/api/save', methods=)
def api_save():
    """Kontextsensitive Speicherlogik"""
    data = request.json
    context = data.get('context')
    
    if context == 'video':
        success, frame = camera.read()
        if success:
            fname = f"snapshot_{int(time.time())}.jpg"
            path = os.path.join(SNAPSHOT_DIR, fname)
            cv2.imwrite(path, frame)
            return jsonify({"msg": f"Bild gespeichert: {fname}", "status": "success"})
        return jsonify({"msg": "Kamerafehler", "status": "error"}), 500
        
    elif context == 'spectrum':
        # Archivierung der aktuellen CSV
        src_name = data_store.current_filename
        if not src_name or "Warte" in src_name:
             return jsonify({"msg": "Kein Spektrum geladen", "status": "error"}), 400
             
        src_path = os.path.join(INPUT_DIR, src_name)
        # Timestamp hinzufügen um Überschreiben zu vermeiden
        dest_name = f"{int(time.time())}_{src_name}"
        dest_path = os.path.join(ARCHIVE_DIR, dest_name)
        
        try:
            shutil.copy2(src_path, dest_path)
            return jsonify({"msg": f"Spektrum archiviert: {dest_name}", "status": "success"})
        except Exception as e:
            return jsonify({"msg": str(e), "status": "error"}), 500

    return jsonify({"msg": "Unbekannter Kontext", "status": "error"}), 400

if __name__ == '__main__':
    observer = start_watcher(INPUT_DIR)
    try:
        # Threaded=True ist wichtig für gleichzeitiges Video & Polling
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        observer.stop()
        camera.release()

9.4 Frontend Template (templates/index.html)Hier wird die Umschalt-Logik implementiert. Der CSS-Switch steuert die Sichtbarkeit und das Polling-Verhalten.HTML<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Lab Station V2 Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #ecf0f1; text-align: center; margin: 0; padding: 20px; }
       .dashboard-container { background: white; max-width: 900px; margin: 0 auto; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
        /* Viewport Styling */
       .viewport { width: 100%; height: 500px; background: #2c3e50; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }
       .viewport img { max-width: 100%; max-height: 100%; object-fit: contain; }
        
        /* Controls Styling */
       .controls { display: flex; justify-content: space-between; align-items: center; background: #bdc3c7; padding: 15px; border-radius: 5px; }
        
        /* Toggle Switch CSS */
       .switch-container { display: flex; align-items: center; gap: 10px; font-weight: bold; }
       .switch { position: relative; display: inline-block; width: 60px; height: 34px; }
       .switch input { opacity: 0; width: 0; height: 0; }
       .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #7f8c8d; transition:.4s; border-radius: 34px; }
       .slider:before { position: absolute; content: ""; height: 26px; width: 26px; left: 4px; bottom: 4px; background-color: white; transition:.4s; border-radius: 50%; }
        input:checked +.slider { background-color: #3498db; }
        input:checked +.slider:before { transform: translateX(26px); }
        
        /* Save Button */
       .btn-save { background-color: #e74c3c; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 4px; cursor: pointer; transition: background 0.3s; }
       .btn-save:hover { background-color: #c0392b; }
        
        #status-text { margin-top: 10px; color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <h1>UV-VIS Lab Station V2</h1>
        
        <div class="viewport">
            <img id="main-display" src="/video_feed" alt="Ansicht">
        </div>

        <div class="controls">
            <div class="switch-container">
                <span>Video</span>
                <label class="switch">
                    <input type="checkbox" id="mode-toggle">
                    <span class="slider"></span>
                </label>
                <span>Spektrum</span>
            </div>
            
            <button class="btn-save" onclick="handleSave()">💾 Speichern / Archivieren</button>
        </div>
        <div id="status-text">System bereit - Modus: Video</div>
    </div>

    <script>
        const display = document.getElementById('main-display');
        const toggle = document.getElementById('mode-toggle');
        const statusText = document.getElementById('status-text');
        
        // State Variable
        let currentMode = 'video'; 
        let pollingInterval = null;
        let lastTimestamp = 0;

        // --- Umschalt-Logik ---
        toggle.addEventListener('change', (e) => {
            if (e.target.checked) {
                // Modus Wechsel: Zu Spektrum
                currentMode = 'spectrum';
                statusText.innerText = "Modus: Spektrum - Warte auf Daten...";
                // Video Stream stoppen durch Bildwechsel
                display.src = "/spectrum_plot.png?t=" + Date.now();
                startPolling();
            } else {
                // Modus Wechsel: Zu Video
                currentMode = 'video';
                statusText.innerText = "Modus: Video Stream";
                stopPolling();
                display.src = "/video_feed";
            }
        });

        // --- Polling Logik (Nur im Spektrum Modus aktiv) ---
        function startPolling() {
            // Sofortiger Check
            checkUpdate();
            // Periodischer Check alle 2s
            pollingInterval = setInterval(checkUpdate, 2000);
        }

        function stopPolling() {
            if (pollingInterval) clearInterval(pollingInterval);
        }

        function checkUpdate() {
            fetch('/api/status')
               .then(res => res.json())
               .then(data => {
                    // Update UI wenn neuer Zeitstempel erkannt
                    if (data.timestamp > lastTimestamp) {
                        lastTimestamp = data.timestamp;
                        // Cache Busting via Timestamp Parameter
                        display.src = "/spectrum_plot.png?t=" + Date.now();
                        statusText.innerText = "Daten geladen: " + data.filename;
                    }
                })
               .catch(err => console.error("Polling Fehler:", err));
        }

        // --- Kontextsensitive Speicherung ---
        function handleSave() {
            fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ context: currentMode })
            })
           .then(res => res.json())
           .then(data => {
                alert(data.msg); // Einfaches Feedback
                if (data.status === 'success') {
                    // Optional: Visuelles Feedback im Button
                }
            })
           .catch(err => alert("Netzwerkfehler beim Speichern"));
        }
    </script>
</body>
</html>

10. Sicherheit, Wartung und Betrieb

10.1 Sicherheitsaspekte Da die lab_station im Labornetzwerk betrieben wird, müssen folgende Punkte beachtet werden:Netzwerk-Isolation: Der Flask-Entwicklungsserver (app.run) ist nicht für das öffentliche Internet gehärtet. Der Zugriff sollte über ein VPN oder VLAN auf Laborgeräte beschränkt sein.Input Sanitization: Das Einlesen von CSV-Dateien ist ein potenzielles Angriffsvektor (Buffer Overflow durch manipulierte Dateien). Die Verwendung von Pandas (read_csv) in einem try-except Block mit expliziter Typ-Konvertierung mindert dieses Risiko, eliminiert es aber nicht vollständig.Dateiberechtigungen: Der Linux-User, unter dem die Flask-App läuft, sollte Schreibrechte nur in /data/saved_snapshots und /data/archived_spectra haben, jedoch im /data/x200... Eingangskorb idealerweise nur Leserechte (und WinSCP User Schreibrechte), um Datenverlust zu verhindern. Da wir aber Dateien nicht löschen (sondern nur lesen), ist dies sicher. Falls die Archivierung ein "Verschieben" (Move) statt "Kopieren" sein soll, sind Schreibrechte nötig.

10.2 Fehlerbehandlung und LoggingIm Falle eines Fehlers (z.B. Kamera nicht verbunden, CSV korrupt) darf die Anwendung nicht abstürzen.Watchdog: Exceptions im Event-Handler werden gefangen und geloggt, der Thread läuft weiter.Kamera: Wenn camera.read() fehlschlägt, sollte das Video-Feed ein statisches "Fehlerbild" (Placeholder) senden, anstatt die Verbindung zu schließen.Logging: Alle Ereignisse (Datei erkannt, Fehler beim Parsen, Save-Action) sollten in eine rotierende Logdatei (/var/log/lab_station.log) geschrieben werden, um die Fehlersuche zu erleichtern.

10.3 FazitDie hier spezifizierte Architektur erfüllt alle Anforderungen an die Erweiterung der lab_station_v1. Durch die intelligente Kombination von asynchroner Dateiverarbeitung (Watchdog/WinSCP-Awareness) und synchronem Web-Streaming, gepaart mit einer kontextsensitiven Steuerlogik, entsteht ein leistungsfähiges Werkzeug für den modernen Laboralltag. Die Lösung ist modular, wartbar und nutzt etablierte Industriestandards (Pandas, Flask, OpenCV), was die Zukunftsfähigkeit sicherstellt.