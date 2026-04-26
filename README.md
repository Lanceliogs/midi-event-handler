# Meh! — MIDI Event Handler

Map **MIDI inputs (single notes or chords)** to **custom MIDI outputs** with optional **time-based behavior** (min/max duration + fallback events). Comes with a full-featured web UI including a **visual mapping editor**, **live dashboard**, and **MIDI recording**.

> **Documentation**: See the [User Manual](docs/manual_en.md) for detailed usage instructions.

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

Open the app: [**http://127.0.0.1:8000**](http://127.0.0.1:8000)

#### Web UI Pages

| Page | URL | Description |
|------|-----|-------------|
| **Dashboard** | `/meh/ui/dashboard` | Live show monitoring with timers |
| **Editor** | `/meh/ui/editor` | Visual mapping editor with MIDI recording |
| **Help** | `/meh/ui/help` | Documentation and log viewer |

#### Sidebar Controls

- **START/STOP** the MIDI runtime
- **Upload** a new `mapping.yaml` or `.yml` (only when stopped)
- **Request restart** (for launcher/compiled mode)

### 2) Launcher (monitors & tray on Windows)

- In compiled/installed mode it shows a **system tray icon** with:
  - **Open Dashboard**
  - **Check for Updates** (GitHub releases)
  - **Quit**
- The launcher watches `.runtime/restart.flag` to cycle the app.

## Features

### Visual Editor

The **Editor** page provides full CRUD for your mapping configuration:

- Add/edit/delete **inputs**, **outputs**, **event types**, and **events**
- **Record MIDI notes** directly from your controller (click the mic icon)
- Interactive note/message badges
- Diff preview before saving
- Dirty state indicator for unsaved changes

### Live Dashboard

The **Dashboard** page provides real-time monitoring during shows:

- **Show timer** with elapsed time
- **Active events** per type with countdown progress bars
- **Event log** with START/END history
- **MIDI input monitor** showing incoming chords
- **Trigger statistics** sorted by most used
- **Port health** with activity indicators (green/orange/red)

### PAD Mode (Manual Triggering)

When the app is running, you can manually trigger events from the Editor:

- Click **PLAY** to trigger an event as if MIDI was received
- Click **STOP** to end an active event
- Useful for testing without a MIDI controller

## API (useful for scripting)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/meh/api/start` | Start the MIDI runtime |
| `POST` | `/meh/api/stop` | Stop the MIDI runtime |
| `GET` | `/meh/api/status` | JSON status (running, events, ports, tasks) |
| `POST` | `/meh/api/upload-mapping` | Upload a `.yaml`/`.yml` mapping (stopped only) |
| `POST` | `/meh/api/restart` | Request launcher restart |
| `GET` | `/meh/api/logs` | Get recent application logs |
| `WS` | `/meh/ws/events` | Real-time notifications for UI updates |

## Building releases

This project moved from Nuitka to embedded Python distribution. Why?

- **Open source friendly** — no proprietary compilation step, just Python
- **Fast builds** — Nuitka took 10+ minutes, embedded builds take seconds (Python is cached)
- **Easy patching** — need to fix something? Edit the `.py` files directly in the release folder
- **Cleaner release** — a small native CLI launcher (`meh.exe`) + standard Python, no compiled blobs

Helper scripts are wired in `pyproject.toml`:

```bash
# Build the release (downloads Python, builds wheel, compiles CLI launcher)
poetry run build

# Build a Windows installer with Inno Setup (reads .innosetup.conf for ISCC.exe path)
poetry run build-installer
```

Notes:

- Embedded Python and CLI exe are cached in `.build-cache/` for fast rebuilds.
- Installer output goes to `dist/installer/midi-event-handler-setup_<version>.exe`.
- The launcher handles graceful shutdown/restart by calling the app's `/shutdown` endpoint.
- Release checks pull from GitHub Releases and download the correct `midi-event-handler-setup_*.exe`.

## Usage tips & troubleshooting

- **Ports unavailable?** Check `/status` in the dashboard; inputs/outputs show **friendly name**, **resolved real name**, and **availability**.
- **Wrong port names?** Because of substring matching, pick distinctive friendly names (e.g., `LPD8_in` vs `in`).
- **Mapping changes not taking effect?**
  - If the app is **running**, stop it first, then upload a new mapping.
  - For CLI: `--mapping yourfile.yaml` copies to `.runtime/mapping.yaml` before startup.
- **Dev reloads**: `--reload` only works in dev mode (not in embedded releases).
- **Logs**: tweak `config.yaml` to change log levels/formatters.
- **Firewall**: the dashboard runs on your configured host/port; default is `127.0.0.1:8000`.

