from fastapi import (
    FastAPI, 
    WebSocket, WebSocketDisconnect,
    File, UploadFile,
    HTTPException,
    Depends
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pathlib import Path
from pydantic import BaseModel

import psutil, os, shutil, asyncio, logging

from midi_event_handler.core.config import (
    RUNTIME_PATH, get_current_version
)

from midi_event_handler.tools.connection import ConnectionManager

from midi_event_handler.core.app import MidiApp

from midi_event_handler.web import help
from midi_event_handler.web import shutdown

from contextlib import asynccontextmanager

def get_templates_path():
    if "__compiled__" in globals():
        return Path("templates")
    return Path(__file__).parent / "templates"

def get_static_path():
    if "__compiled__" in globals():
        return Path("static")
    return Path(__file__).parent / "static"

log = logging.getLogger(__name__)

templates = Jinja2Templates(directory=get_templates_path())

# --- APP -----------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):    
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(help.router)
app.include_router(shutdown.router)

midiapp = MidiApp()

# --- JSON API routes -------------------------------------------------------------

@app.post("/meh.api/upload-mapping")
async def upload_mapping(file: UploadFile = File(...)):

    if midiapp.running:
        raise HTTPException(status_code=400, detail="Can't reload while the app is running")
    if not file.filename.endswith(".yaml"):
        raise HTTPException(status_code=400, detail="File must be a .yaml")

    RUNTIME_PATH.mkdir(exist_ok=True)
    mapping_path = RUNTIME_PATH / "mapping.yaml"

    try:
        with mapping_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        midiapp.reload_mapping()
    except Exception as e:
        log.exception("Failed to upload or reload mapping")
        raise HTTPException(status_code=500, detail=f"Failed to upload or reload mapping: {e}")

    return {"status": "ok", "mapping": file.filename}

@app.post("/meh.api/start")
async def start_show():
    await midiapp.start()
    return {
        "running": midiapp.running
    }

@app.post("/meh.api/stop")
async def stop_show():
    await midiapp.stop()
    return {
        "running": midiapp.running
    }

@app.get("/meh.api/status")
async def get_status():
    return midiapp.get_status()

# --- Websockets ----------------------------------------------------------------

@app.websocket("/meh.ws/events")
async def ws_endpoint_events(ws: WebSocket):
    manager = ConnectionManager("meh-app")
    await manager.manage_until_death(ws)

# --- UI routes ----------------------------------------------------------------

@app.get("/")
async def index():
    return RedirectResponse("/meh.ui/dashboard")

@app.get("/meh.ui/dashboard")
async def dashboard(request: Request, version: str = Depends(get_current_version)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "version": version
    })

@app.get("/meh.ui/dashboard/status")
async def status_fragment(request: Request):
    return templates.TemplateResponse("partials/status_fragment.html", {
        "request": request,
        "status": midiapp.get_status(),
    })

# --- ADMIN routes -------------------------------------------------------------

@app.post("/meh.api/restart")
async def request_restart():
    Path(".runtime").mkdir(exist_ok=True)
    Path(".runtime/restart.flag").touch()
    return {"status": "restart requested"}

# Mount static as html at the end
app.mount("/static", StaticFiles(directory=get_static_path(), html=True), name="static")
