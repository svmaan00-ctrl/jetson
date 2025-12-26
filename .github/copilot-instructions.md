## Spracheinstellungen (WICHTIG)
- Antworte IMMER auf Deutsch.
- Schreibe alle Code-Kommentare, Docstrings und technische Erklärungen auf Deutsch.
- Fachbegriffe wie "Endpoints", "Serial" oder "Flask" können beibehalten werden.

## Quick purpose

This file gives targeted guidance for AI coding agents working on the inspection_project repository — what to change, what to run, and what to avoid.

## Big picture

- Small multi-component Python project. Main responsibilities:
  - Web UI (Flask) served from `web_gui.py` and `web_gui_update_uv_vis.py`.
  - Live camera/focus endpoints in `src/live_focus.py`.
  - Data storage under `data/` (mikroskopbilder, spectra, environment metadata, logs) with code that auto-creates these folders.
  - Optional hardware/serial integration guarded by a `SERIAL_AVAILABLE` flag when `pyserial` is importable.

## Key files to read first

- `web_gui.py` — primary Flask app and endpoints (run with `python web_gui.py`).
- `web_gui_update_uv_vis.py` — variant of the web UI that talks to Arduino/UV hardware when serial is present.
- `src/live_focus.py` — small Flask app for live-focus streaming.
- `test_arduino_verbindung.py` — example hardware test that assumes a serial device (default `/dev/ttyACM0`).
- `test_mikroskop.py` / `src/test_mikroskop.py` — local tests for microscope integration.

## Project-specific patterns and conventions

- Guard hardware imports: modules import `serial` in a try/except and set `SERIAL_AVAILABLE = False` when unavailable. Code paths that interact with hardware check this flag before executing.
- Base data directory is constructed via `os.path.expanduser('~/inspection_project/data/')` in several modules. 
- WICHTIG: Die Bilder werden im Ordner `mikroskopbilder/` gespeichert. Stelle sicher, dass Pfade darauf verweisen und nicht auf den alten Namen `bilder/`.
- Many parts of the code assume that layout and create subfolders `mikroskopbilder/`, `spektren/`, `umgebung/`, `logs/` if missing — avoid changing base path globally without checking callers.
- Web entrypoints commonly have an `if __name__ == '__main__':` block and are run directly for development.
- Tests and small scripts may open serial ports directly (no mocking) — be conservative when running on CI or developer machines without hardware.

## How to run and test (discovered from code)

- Local web app (development): `python web_gui.py` or `python web_gui_update_uv_vis.py` (these create Flask servers).
- Live-focus: `python -m src.live_focus` or run `src/live_focus.py` directly.
- Tests: this repo uses simple test scripts; run `pytest -q` or `python -m pytest` if you add pytest-based tests. Be aware `test_arduino_verbindung.py` will attempt to open `/dev/ttyACM0`.
- Install runtime deps discovered in code: at minimum `flask` and optionally `pyserial` for hardware. Create a virtualenv and run `pip install flask pyserial` when needed.

## Hardware & integration notes

- Serial usage is optional. When `pyserial` is missing the code prints a warning and disables Arduino-specific routes. Use the `SERIAL_AVAILABLE` pattern when adding features that touch hardware.
- Developer test `test_arduino_verbindung.py` uses a hard-coded `SERIAL_PORT` — change it or mock `serial.Serial` before running on machines without that device.

## Data and logs

- Persisted files live under `data/` with these subfolders: `mikroskopbilder/`, `spektren/`, `umgebung/`, `logs/`, `sensordaten/`. Several modules create those directories at startup — inspect the module-level `BASE_DIR` constants before changing file I/O.

## When modifying code

- Prefer small, local edits that preserve the `SERIAL_AVAILABLE` guard and the `BASE_DIR` data layout.
- For web changes, run the corresponding `web_gui*.py` and verify endpoints with the browser or `curl`.
- Add unit tests that avoid opening hardware devices; use dependency injection or monkeypatching for `serial.Serial`.

## Useful examples (search targets)

- Search for `SERIAL_AVAILABLE` and `os.path.expanduser('~/inspection_project/data/')` to find other modules following these patterns.
- See `web_gui_update_uv_vis.py` for an example `with serial.Serial(port, BAUD_RATE, timeout=...)` usage.

## Ask for clarification

If something in this file seems incomplete or you need more details about running the GUI, hardware setup, or tests, ask the repository owner for the preferred development commands and an authoritative `requirements.txt` to pin dependencies.