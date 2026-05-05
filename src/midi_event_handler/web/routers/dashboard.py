"""
Dashboard UI routes: /meh/ui/dashboard/*
"""

import time
from fastapi import APIRouter, Depends
from fastapi.requests import Request

from midi_event_handler.core.app import MidiApp
from midi_event_handler.core.config import get_current_version
from midi_event_handler.core.midi.utils import get_ports_status
from midi_event_handler.web import context
from midi_event_handler.web.context import get_midiapp

router = APIRouter(prefix="/meh/ui/dashboard", tags=["dashboard"])


def format_timestamp(ts):
    """Format unix timestamp as HH:MM:SS."""
    if not ts:
        return "--:--:--"
    t = time.localtime(ts)
    return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"


@router.get("")
async def dashboard(request: Request, version: str = Depends(get_current_version)):
    return context.templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "version": version,
            "ports": get_ports_status(),
            "ports_refresh_url": "/meh/ui/partials/sidebar/ports",
        },
    )


@router.get("/status")
async def status_fragment(request: Request, midiapp: MidiApp = Depends(get_midiapp)):
    return context.templates.TemplateResponse(
        request,
        "partials/dashboard_content.html",
        {
            "status": midiapp.get_status(),
        },
    )
