"""
Shared dependencies for editor routers.
"""

from fastapi import Request
from fastapi.templating import Jinja2Templates

from midi_event_handler.core.app import MidiApp
from midi_event_handler.core.editor import editor_state
from midi_event_handler.core.midi.utils import get_ports_status

# Will be set by configure()
templates: Jinja2Templates = None
midiapp: MidiApp = None


def configure(t: Jinja2Templates, app: MidiApp):
    """Configure shared dependencies."""
    global templates, midiapp
    templates = t
    midiapp = app


def get_active_events() -> set:
    """Get set of currently active event names."""
    if not midiapp or not midiapp.running:
        return set()
    active = set()
    for handler in midiapp.handlers.values():
        if handler.event:
            active.add(handler.event.name)
    return active


def render_content(request: Request):
    """Render editor content after mutations."""
    return templates.TemplateResponse(request, "partials/editor/editor_content.html", {
        "mapping": editor_state.mapping,
        "dirty": editor_state.dirty,
        "app_running": midiapp.running if midiapp else False,
        "active_events": get_active_events(),
    })


def get_ports():
    """Get ports status from editor state."""
    return get_ports_status(editor_state.inputs, editor_state.outputs)
