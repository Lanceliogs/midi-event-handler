"""
Shared UI partials routes: /meh/ui/partials/*
"""

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from midi_event_handler.core.midi.utils import get_ports_status

router = APIRouter(prefix="/meh/ui/partials", tags=["partials"])

# Will be set by main app
templates: Jinja2Templates = None

def configure(t: Jinja2Templates):
    global templates
    templates = t


@router.get("/sidebar/ports")
async def sidebar_ports(request: Request):
    return templates.TemplateResponse(request, "partials/sidebar/midi_ports.html", {
        "ports": get_ports_status(),
        "ports_refresh_url": "/meh/ui/partials/sidebar/ports",
    })
