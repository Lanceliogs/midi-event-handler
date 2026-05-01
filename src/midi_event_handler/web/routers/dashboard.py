"""
Dashboard UI routes: /meh/ui/dashboard/*
"""

import time
from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from midi_event_handler.core.config import get_current_version
from midi_event_handler.core.app import MidiApp
from midi_event_handler.core.midi.utils import get_ports_status

router = APIRouter(prefix="/meh/ui/dashboard", tags=["dashboard"])

# Will be set by main app
templates: Jinja2Templates = None
midiapp: MidiApp = None


def configure(t: Jinja2Templates, app: MidiApp):
    global templates, midiapp
    templates = t
    midiapp = app

    # Add custom filter for time formatting
    templates.env.filters["format_time"] = format_timestamp


def format_timestamp(ts):
    """Format unix timestamp as HH:MM:SS."""
    if not ts:
        return "--:--:--"
    t = time.localtime(ts)
    return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"


@router.get("")
async def dashboard(request: Request, version: str = Depends(get_current_version)):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "version": version,
            "ports": get_ports_status(),
            "ports_refresh_url": "/meh/ui/partials/sidebar/ports",
        },
    )


@router.get("/status")
async def status_fragment(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/dashboard_content.html",
        {
            "status": midiapp.get_status(),
        },
    )
