import os
import time
import shutil

BASE_DIR = os.path.expanduser('~/inspection_project/data')
WATCH_DIR = os.path.join(BASE_DIR, 'x200_rohdaten_eingang')
REF_DIR   = os.path.join(BASE_DIR, 'temp_namensvorlagen')
FINAL_DIR = os.path.join(BASE_DIR, 'x200_spektren_ergebnisse')

for p in [WATCH_DIR, REF_DIR, FINAL_DIR]:
    if not os.path.exists(p): os.makedirs(p)

def get_latest_ref():
    files = [f for f in os.listdir(REF_DIR) if f.endswith('.txt')]
    if not files: return None
    files.sort(key=lambda x: os.path.getmtime(os.path.join(REF_DIR, x)), reverse=True)
    return files[0]

print(f"Watcher aktiv auf: {WATCH_DIR}")

while True:
    incoming = [f for f in os.listdir(WATCH_DIR) if not f.startswith('.')]
    if incoming:
        for f_name in incoming:
            time.sleep(1)
            ref = get_latest_ref()
            if ref:
                base = os.path.splitext(ref)[0]
                ext  = os.path.splitext(f_name)[1]
                target = base + ext
                shutil.move(os.path.join(WATCH_DIR, f_name), os.path.join(FINAL_DIR, target))
                os.remove(os.path.join(REF_DIR, ref))
                print(f"Erfolg: {target}")
    time.sleep(2)
