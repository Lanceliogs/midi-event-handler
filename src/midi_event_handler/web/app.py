from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pathlib import Path
from pydantic import BaseModel

from midi_event_handler.tools.connection import ConnectionManager
from midi_event_handler.tools import logtools
from midi_event_handler.core.app import MidiApp

log = logtools.get_logger(__name__)

templates = Jinja2Templates(directory="src/midi_event_handler/web/templates")

app = FastAPI()
midiapp = MidiApp()

# --- JSON API routes -------------------------------------------------------------

@app.post("/start")
async def start_show():
    await midiapp.start()
    return {
        "running": midiapp.running
    }

@app.post("/stop")
async def stop_show():
    await midiapp.stop()
    return {
        "running": midiapp.running
    }

@app.get("/status")
async def get_status():
    return midiapp.get_status()

# --- Websockets ----------------------------------------------------------------

@app.websocket("/events")
async def ws_endpoint_events(ws: WebSocket):
    manager = ConnectionManager("meh-app")
    await manager.manage_until_death(ws)

# --- UI routes ----------------------------------------------------------------

@app.get("/")
async def index():
    return RedirectResponse("/dashboard")

@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard/status")
async def status_fragment(request: Request):
    return templates.TemplateResponse("partials/status_fragment.html", {
        "request": request,
        "status": midiapp.get_status(),
    })

# Mount static as html at the end
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")

