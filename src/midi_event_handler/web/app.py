from fastapi import (
    FastAPI, 
    WebSocket, WebSocketDisconnect,
    File, UploadFile,
    HTTPException
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pathlib import Path
from pydantic import BaseModel

import psutil, os, shutil

from midi_event_handler.tools.connection import ConnectionManager
from midi_event_handler.tools import logtools
from midi_event_handler.core.app import MidiApp

log = logtools.get_logger(__name__)

templates = Jinja2Templates(directory="src/midi_event_handler/web/templates")

app = FastAPI()
midiapp = MidiApp()

# --- JSON API routes -------------------------------------------------------------

@app.post("/upload-mapping")
async def upload_mapping(file: UploadFile = File(...)):

    if midiapp.running:
        raise HTTPException(status_code=400, detail="Can't reload while the app is running")
    if not file.filename.endswith(".yaml"):
        raise HTTPException(status_code=400, detail="File must be a .yaml")

    runtime_path = Path(".runtime")
    runtime_path.mkdir(exist_ok=True)
    mapping_path = runtime_path / "mapping.yaml"

    try:
        with mapping_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        midiapp.reload_mapping()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload or reload mapping: {e}")

    return {"status": "ok", "mapping": file.filename}

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

# --- ADMIN routes -------------------------------------------------------------

@app.post("/admin/restart")
async def request_restart():
    Path(".runtime").mkdir(exist_ok=True)
    Path(".runtime/restart.flag").touch()
    return {"status": "restart requested"}

@app.post("/admin/exit")
async def exit_and_let_launcher_restart():
    pid = os.getpid()
    psutil.Process(pid).terminate()  # launcher will relaunch


# Mount static as html at the end
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")

