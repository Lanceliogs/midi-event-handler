"""
WebSocket routes: /meh/ws/*
"""

from fastapi import APIRouter, WebSocket

from midi_event_handler.tools.connection import ConnectionManager

router = APIRouter(prefix="/meh/ws", tags=["websocket"])


@router.websocket("/events")
async def ws_endpoint_events(ws: WebSocket):
    manager = ConnectionManager("meh-app")
    await manager.manage_until_death(ws)
