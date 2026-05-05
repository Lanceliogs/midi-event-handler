"""
Editor main page and partials.
"""

from fastapi import APIRouter, Depends
from fastapi.requests import Request

from midi_event_handler.core.app import MidiApp
from midi_event_handler.core.config import get_current_version
from midi_event_handler.core.editor import editor_state

from midi_event_handler.web import context
from midi_event_handler.web.context import get_midiapp
from . import common

router = APIRouter()


@router.get("/")
async def editor(
    request: Request, version: str = Depends(get_current_version), midiapp: MidiApp = Depends(get_midiapp)
):
    """Main editor page."""
    editor_state.load_from_runtime()
    return context.templates.TemplateResponse(
        request,
        "editor.html",
        {
            "version": version,
            "mapping": editor_state.mapping,
            "dirty": editor_state.dirty,
            "app_running": midiapp.running if midiapp else False,
            "active_events": common.get_active_events(),
            "ports": common.get_ports(),
            "ports_refresh_url": "/meh/ui/editor/partials/ports",
        },
    )


@router.get("/partials/ports")
async def editor_ports(request: Request):
    """Refresh ports status."""
    return context.templates.TemplateResponse(
        request,
        "partials/sidebar/midi_ports.html",
        {
            "ports": common.get_ports(),
            "ports_refresh_url": "/meh/ui/editor/partials/ports",
        },
    )


@router.get("/partials/content")
async def editor_content(request: Request):
    """Refresh editor content (for WebSocket updates)."""
    return common.render_content(request)
