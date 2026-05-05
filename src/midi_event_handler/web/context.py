"""
Shared web application context.

Holds the Jinja2Templates and MidiApp instances used by all routers.
Initialized once from app.py lifespan, then accessed via module-level imports.
"""

from fastapi.templating import Jinja2Templates

from midi_event_handler.core.app import MidiApp

templates: Jinja2Templates = None
midiapp: MidiApp = None


def init(t: Jinja2Templates, app: MidiApp):
    """Initialize the shared context. Called once at app startup."""
    global templates, midiapp
    templates = t
    midiapp = app


def get_midiapp() -> MidiApp:
    """FastAPI dependency that returns the shared MidiApp instance."""
    return midiapp
