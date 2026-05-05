"""
Shared helpers for editor routers.
"""

from fastapi import Request

from midi_event_handler.core.editor import editor_state
from midi_event_handler.core.midi.utils import get_ports_status
from midi_event_handler.web import context


def get_active_events() -> set:
    """Get set of currently active event names."""
    if not context.midiapp or not context.midiapp.running:
        return set()
    active = set()
    for handler in context.midiapp.handlers.values():
        if handler.event:
            active.add(handler.event.name)
    return active


def render_content(request: Request):
    """Render editor content after mutations."""
    return context.templates.TemplateResponse(
        request,
        "partials/editor/editor_content.html",
        {
            "mapping": editor_state.mapping,
            "dirty": editor_state.dirty,
            "app_running": context.midiapp.running if context.midiapp else False,
            "active_events": get_active_events(),
        },
    )


def get_ports():
    """Get ports status from editor state."""
    return get_ports_status(editor_state.inputs, editor_state.outputs)
