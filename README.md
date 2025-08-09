# Meh! — MIDI Event Handler

Map **MIDI inputs (single notes or chords)** to **custom MIDI outputs** with optional **time-based behavior** (min/max duration + fallback events). Comes with a small FastAPI web UI to start/stop the runtime and hot-swap mappings.

## Requirements

- **Python 3.12**+
- Windows first, but everything but the INNO SETUP installer is mostly platform independant.
- MIDI backend via `mido` + `python-rtmidi`

## Install

### Using Poetry (recommended)

```bash
# In the project root
pipx install poetry  # or: pip install --user poetry
poetry install
```

### Alternative: plain pip (editable dev install)

```bash
python -m venv .venv
# activate your venv...
pip install -e .
```

### First-run assets (already vendored)

HTMX and static assets are already included under `src/midi_event_handler/web/static/`.

## Configuration

### App port & logging

Edit `config.yaml`:

```yaml
app:
  host: 127.0.0.1
  port: 8000
# logging config trimmed...
```

### Mapping file (the heart of it)

Create/edit `mapping.yaml` (or reuse the sample at repo root). You can start with:

```yaml
inputs:
  - "loopIN0"    # Friendly input name (partial match to actual MIDI port)

outputs:
  - "loopOU0"    # Friendly output name (partial match to actual MIDI port)

event_types:
  - light
  - music

events:
  - name: event_key_108
    type: music
    trigger:
      port: loopIN0
      notes: [108]     # Single note or chord (list)
    start_messages:
      - {type: note_on, note: 108, velocity: 127, port: "loopOU0"}
    end_messages:
      - {type: note_off, note: 108, velocity: 0, port: "loopOU0"}
    duration_min: 10   # (optional) lock for at least N seconds
    duration_max: 20   # (optional) auto-fallback after N seconds
    fallback_event: event_key_107  # (optional)
```

#### How ports are resolved

- You configure **friendly names** in the mapping (e.g., `loopIN0`, `loopOU0`).
- At runtime, the app **auto-matches** those against real system ports by **substring** (helpful when OS renames ports).

#### Event lifecycle

- On trigger (matching chord), we send `start_messages`.
- If `duration_min` is set, the event is **locked** for that many seconds.
- If `duration_max` is set, when it elapses we **enqueue** the `fallback_event`.
- When a new event replaces the active one, we send the previous `end_messages`.

## Running (development)

You have two entry points:

### 1) Direct app (FastAPI + dashboard)

```bash
# default: host 0.0.0.0, port 8000
poetry run start-app

# Use a specific mapping file; it will be copied to .runtime/mapping.yaml
poetry run start-app --mapping mapping.yaml

# Shortcut for localhost:8000
poetry run start-app --local
```

Open the dashboard: [**http://127.0.0.1:8000/dashboard**](http://127.0.0.1:8000/dashboard)

From the sidebar you can:

- **START/STOP** the MIDI runtime
- **Upload** a new `mapping.yaml` (hot-reloads when the app isn’t running)
- **Request restart** (helpful for the launcher/compiled mode)

### 2) Launcher (monitors & tray on Windows)

- In compiled/installed mode it shows a **system tray icon** with:
  - **Open Dashboard**
  - **Check for Updates** (GitHub releases)
  - **Quit** (writes an exit flag)
- The launcher watches `.runtime/restart.flag` / `.runtime/exit.flag` to cycle the app.

## API (useful for scripting)

- `POST /meh.api/start` — starts the MIDI runtime
- `POST /meh.api/stop` — stops the MIDI runtime
- `GET  /meh.api/status` — JSON status (running, current events, MIDI ports, tasks)
- `POST /meh.api/upload-mapping` — multipart upload of a `.yaml` mapping (only when not running)
- `POST /meh.api/restart` — asks the launcher to restart
- WebSocket `/meh.ws/events` — pushes lightweight notifications so the dashboard can live-update

## Nuitka builds

The project includes helper scripts wired in `pyproject.toml`:

```bash
# Update version.txt from a tag or string (used by the installer naming)
poetry run update-version

# Compile the app (Nuitka). Produces a /build/Release layout the installer can use.
poetry run build-app

# Build a Windows installer with Inno Setup (reads .innosetup.conf for ISCC.exe path)
poetry run build-installer
```

Notes:

- Installer output goes to `dist/installer/midi-event-handler-setup_<version>.exe`.
- The launcher handles graceful shutdown/restart by calling the app’s `/shutdown` endpoint.
- Release checks pull from GitHub Releases and download the correct `midi-event-handler-setup_*.exe`.

## Usage tips & troubleshooting

- **Ports unavailable?** Check `/status` in the dashboard; inputs/outputs show **friendly name**, **resolved real name**, and **availability**.
- **Wrong port names?** Because of substring matching, pick distinctive friendly names (e.g., `LPD8_in` vs `in`).
- **Mapping changes not taking effect?**
  - If the app is **running**, stop it first, then upload a new mapping.
  - For CLI: `--mapping yourfile.yaml` copies to `.runtime/mapping.yaml` before startup.
- **Dev reloads**: `--reload` only works in **non-compiled** (dev) mode.
- **Logs**: tweak `config.yaml` to change log levels/formatters.
- **Firewall**: the dashboard runs on your configured host/port; default is `127.0.0.1:8000`.

