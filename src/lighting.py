### 2. LED-Steuerung (src/lighting.py)
### Neu:** Dieses Modul nutzt `uvcdynctrl`, um die proprietären Befehle an das Dino-Lite zu senden. Es muss im System installiert sein (`sudo apt-get install uvcdynctrl`).

from sympy import python


python
import subprocess
import logging

logger = logging.getLogger("Lighting")

class DinoLightControl:
    @staticmethod
    def _send_uvc_cmd(unit, selector, payload):
        """
        Sendet einen Raw-Hex-Befehl an das UVC Extension Unit.
        Dino-Lite nutzt meist Unit 4.
        """
        # Befehl zusammenbauen: uvcdynctrl -S 4:2 0xf201...
        cmd = ["uvcdynctrl", "-S", f"{unit}:{selector}", str(payload)]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            logger.error(f"LED Control Failed: {cmd}")
            return False
        except FileNotFoundError:
            logger.error("uvcdynctrl nicht gefunden! Bitte 'sudo apt-get install uvcdynctrl' ausführen.")
            return False

    @staticmethod
    def set_light(mode, state):
        """
        Steuert die Beleuchtung basierend auf dem Modus.
        
        Args:
            mode (str): 'R' (Ring), 'C' (Coax), 'S' (Side/Custom), 'O' (Off)
            state (bool): Wird hier implizit durch den Modus gesteuert (Lichtwechsel)
        """
        # Hex-Codes für Dino-Lite (Little Endian Formatierung beachten)
        # Unit 4, Selector 2 ist Standard für LED-Switch
        
        if mode == 'O': # Alle Aus
            DinoLightControl._send_uvc_cmd(4, 2, "0xf200000000000000")
            
        elif mode == 'R': # Ringlicht An
            # Standard "LED On" Befehl
            DinoLightControl._send_uvc_cmd(4, 2, "0xf201000000000000")
            
        elif mode == 'C': # Coax (AXI)
            # Manche Modelle nutzen f4 für Coax, oder f3 Quadranten-Logik
            # Wir probieren den Standard-Switch für AXI
            DinoLightControl._send_uvc_cmd(4, 2, "0xf401000000000000")
            
        elif mode == 'S': # Side / FLC Quadrant
            # Beispiel: Nur Quadrant 1+2 an (Seitlich)
            # f3 + Bitmaske (diese muss ggf. experimentell ermittelt werden je nach Modell)
            DinoLightControl._send_uvc_cmd(4, 2, "0xf303000000000000")

        logger.info(f"Licht gesetzt auf: {mode}")