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

from midi_event_handler.web.routers import api, ws, dashboard, editor, partials
from midi_event_handler.web import help, shutdown

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

# Shared instances (created before lifespan to be accessible)
templates = Jinja2Templates(directory=get_templates_path())
templates.env.filters['note_name'] = note_to_name
midiapp = MidiApp()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup on shutdown
    log.info("[Lifespan] Shutting down MidiApp...")
    if midiapp.running:
        await midiapp.stop()
    log.info("[Lifespan] Cleanup complete")

app = FastAPI(lifespan=lifespan)

# Configure routers with shared dependencies
api.set_midiapp(midiapp)
dashboard.configure(templates, midiapp)
editor.configure(templates, midiapp)
partials.configure(templates)

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
