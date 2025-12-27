import os

# Pfade basierend auf deiner Struktur
paths = [
    "data/x200_rohdaten_eingang",
    "data/archivierte_spektren",
    "data/archivierte_mikroskopbilder"
]

def check_access():
    print(f"{'Ordner':<35} | R | W | Status")
    print("-" * 55)
    for p in paths:
        full_path = os.path.expanduser(f"~/inspection_project/{p}")
        exists = os.path.exists(full_path)
        
        # Prüfe Leserechte (Read) und Schreibrechte (Write)
        read = os.access(full_path, os.R_OK) if exists else False
        write = os.access(full_path, os.W_OK) if exists else False
        
        status = "OK" if read and write else "FEHLER"
        if not exists: status = "FEHLT"
        
        print(f"{p:<35} | {'X' if read else '-'} | {'X' if write else '-'} | {status}")

if __name__ == "__main__":
    check_access()