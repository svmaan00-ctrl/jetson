import serial
import time

# Dein Port (wir wissen jetzt, es ist ACM0)
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

print(f"--- ARDUINO MONITOR START ---")
print(f"Verbinde zu {SERIAL_PORT}...")

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Warten auf Arduino-Reset
    print("Verbindung steht! Daten werden formatiert...")
    print("-" * 50)

    while True:
        if ser.in_waiting > 0:
            try:
                # 1. Zeile lesen
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # 2. Prüfen: Hat die Zeile Tabs (\t)? (Dann sind es unsere Daten)
                if '\t' in line and "T1" not in line:
                    # 3. Zerlegen an den Tabs
                    parts = line.split('\t')
                    
                    # Wir erwarten 6 Teile (T1, H1, T2, H2, Gas, Alarm)
                    if len(parts) >= 6:
                        t1 = parts[0]
                        h1 = parts[1]
                        t2 = parts[2]
                        h2 = parts[3]
                        gas = parts[4]
                        alarm = parts[5]
                        
                        # 4. Schön ausgeben
                        print(f"SENSOR 1  | Temp: {t1}°C  | Feuchte: {h1}%")
                        print(f"SENSOR 2  | Temp: {t2}°C  | Feuchte: {h2}%")
                        print(f"UMGEBUNG  | Gas:  {gas:<5} | Status:  {alarm}")
                        print("-" * 50) # Trennlinie
                    else:
                        # Falls mal eine kaputte Zeile kommt
                        print(f"Unvollständige Daten: {line}")
                        
            except Exception as e:
                print(f"Fehler: {e}")
                
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nBeendet.")
    ser.close()
except Exception as e:
    print(f"Verbindungsfehler: {e}")