from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from midi_event_handler.web.connection import ConnectionManager
from midi_event_handler.tools import logtools
from midi_event_handler.core.app import MidiApp

import uvicorn

log = logtools.get_logger()
log.info("this is a test!")

app = FastAPI()


class GlobalState(BaseModel):
    connections: int

@app.get("/globalstate")
async def get_global_state():
    manager = ConnectionManager("meh-app")
    return GlobalState(
        connections=manager.connections_num
    )

@app.websocket("/events")
async def ws_endpoint_events(ws: WebSocket):
    manager = ConnectionManager("meh-app")
    await manager.manage_until_death(ws)

# Mount static as html at the end
static_path = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

