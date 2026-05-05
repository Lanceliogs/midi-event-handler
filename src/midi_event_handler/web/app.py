"""
Main FastAPI application.
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pathlib import Path
from contextlib import asynccontextmanager

from midi_event_handler.core.config import is_embedded
from midi_event_handler.core.app import MidiApp
from midi_event_handler.core.midi.notes import note_to_name
from midi_event_handler.web.routers.dashboard import format_timestamp

from midi_event_handler.web import context, help, shutdown
from midi_event_handler.web.routers import api, ws, dashboard, editor, partials

import logging

log = logging.getLogger(__name__)


def get_templates_path():
    if is_embedded():
        return Path("templates")
    return Path(__file__).parent / "templates"


def get_static_path():
    if is_embedded():
        return Path("static")
    return Path(__file__).parent / "static"


# --- App Setup ----------------------------------------------------------------


def init_context():
    """Create shared instances and initialize the context module."""
    templates = Jinja2Templates(directory=get_templates_path())
    templates.env.filters["note_name"] = note_to_name
    templates.env.filters["format_time"] = format_timestamp
    midiapp = MidiApp()
    context.init(templates, midiapp)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_context()
    yield
    log.info("[Lifespan] Shutting down MidiApp...")
    if context.midiapp.running:
        await context.midiapp.stop()
    log.info("[Lifespan] Cleanup complete")


app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(api.router)
app.include_router(ws.router)
app.include_router(dashboard.router)
app.include_router(editor.router)
app.include_router(partials.router)
app.include_router(help.router)
app.include_router(shutdown.router)


# --- Root redirect ------------------------------------------------------------


@app.get("/")
async def index():
    return RedirectResponse("/meh/ui/dashboard")


# --- Static files (must be last) ----------------------------------------------

app.mount("/static", StaticFiles(directory=get_static_path(), html=True), name="static")
