"""
Shared UI partials routes: /meh/ui/partials/*
"""

from fastapi import APIRouter
from fastapi.requests import Request

from midi_event_handler.core.midi.utils import get_ports_status
from midi_event_handler.web import context

router = APIRouter(prefix="/meh/ui/partials", tags=["partials"])


@router.get("/sidebar/ports")
async def sidebar_ports(request: Request):
    return context.templates.TemplateResponse(
        request,
        "partials/sidebar/midi_ports.html",
        {
            "ports": get_ports_status(),
            "ports_refresh_url": "/meh/ui/partials/sidebar/ports",
        },
    )
