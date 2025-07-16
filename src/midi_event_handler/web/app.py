from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from midi_event_handler.web.connection import ConnectionManager
from midi_event_handler.tools import logtools
from midi_event_handler.core.app import MidiApp

log = logtools.get_logger(__name__)

app = FastAPI()
midiapp = MidiApp()

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
    
@app.websocket("/events")
async def ws_endpoint_events(ws: WebSocket):
    manager = ConnectionManager("meh-app")
    await manager.manage_until_death(ws)

# Mount static as html at the end
static_path = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

