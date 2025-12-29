### 3. Sensor Bridge (src/sensor_bridge.py)
### Änderung:** Implementiert echte serielle Kommunikation mit Reconnect-Logik und Fehlerbehandlung für das TSV-Format.

python
import serial
import time
import threading
import logging

logger = logging.getLogger("SensorBridge")

def sensor_loop(dm_instance, port='/dev/ttyACM0', baud=115200):
    """
    Hintergrund-Thread für Arduino-Kommunikation.
    Liest: T1 \t H1 \t T2 \t H2 \t Gas \t Status
    """
    ser = None
    
    while True:
        try:
            # Reconnect Logik
            if ser is None or not ser.is_open:
                try:
                    ser = serial.Serial(port, baud, timeout=2)
                    logger.info(f"Arduino verbunden an {port}")
                    time.sleep(2) # Wait for Arduino Reset
                except serial.SerialException:
                    dm_instance.set_led("clim", "red")
                    time.sleep(3) # Retry delay
                    continue

            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Ignoriere Debug-Nachrichten (alles was nicht Tab-getrennt ist)
                if '\t' not in line:
                    continue

                parts = line.split('\t')
                
                # Wir erwarten 6 Werte
                if len(parts) >= 6:
                    try:
                        data = {
                            't1': float(parts),
                            'rh1': float(parts[1]),
                            't2': float(parts[2]),
                            'rh2': float(parts[3]),
                            'gas': int(parts[4]),
                            'status': parts[5] # "Normal" oder "ALARM"
                        }
                        
                        # Update Singleton
                        dm_instance.update_sensors(
                            data['t1'], data['t2'], 
                            data['rh1'], data['rh2'], 
                            data['gas']
                        )
                        
                        # Status LED Logik
                        if "ALARM" in data['status']:
                            dm_instance.set_led("clim", "blink")
                        else:
                            dm_instance.set_led("clim", "green")
                            
                    except ValueError:
                        pass # Parsing Fehler ignorieren
                        
        except Exception as e:
            logger.error(f"Serial Error: {e}")
            if ser:
                ser.close()
            ser = None
            dm_instance.set_led("clim", "red")
            time.sleep(1)