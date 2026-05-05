"""
Event type CRUD routes.
"""

from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from fastapi.responses import Response

from midi_event_handler.core.editor import editor_state

from midi_event_handler.web import context
from . import common

router = APIRouter()


@router.get("/event-type/new")
async def event_type_new(request: Request):
    """New event type form modal."""
    return context.templates.TemplateResponse(
        request,
        "partials/editor/modals/event_type_form.html",
        {
            "is_new": True,
            "current_name": "",
        },
    )


@router.get("/event-type/{name}")
async def event_type_edit(request: Request, name: str):
    """Edit event type form modal."""
    if name not in editor_state.event_types:
        raise HTTPException(status_code=404, detail="Event type not found")

    return context.templates.TemplateResponse(
        request,
        "partials/editor/modals/event_type_form.html",
        {
            "is_new": False,
            "current_name": name,
            "original_name": name,
        },
    )


@router.post("/event-type")
async def event_type_save(request: Request):
    """Save event type (create or update)."""
    form = await request.form()
    name = form.get("name", "").strip()
    original_name = form.get("original_name", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if original_name:
        editor_state.update_event_type(original_name, name)
    else:
        if not editor_state.add_event_type(name):
            return Response(
                content="",
                status_code=400,
                headers={"X-Toast": f"'{name}' already exists", "X-Toast-Type": "error"},
            )

    return common.render_content(request)


@router.get("/check-event-type")
async def check_event_type(name: str = "", original_name: str = ""):
    """Live uniqueness check for event type names."""
    name = name.strip()
    if not name:
        return Response("")
    if name != original_name and name in editor_state.event_types:
        return Response('<span class="resolution-error">Already exists</span>')
    return Response("")


@router.delete("/event-type/{name}")
async def event_type_delete(request: Request, name: str):
    """Delete event type (cascades to events)."""
    editor_state.delete_event_type(name)
    return common.render_content(request)


@router.get("/confirm-delete/event-type/{name}")
async def confirm_delete_event_type(request: Request, name: str):
    """Confirm delete event type modal with cascade warning."""
    affected = editor_state.get_events_by_type(name)
    return context.templates.TemplateResponse(
        request,
        "partials/editor/modals/confirm_delete.html",
        {
            "item_type": "event-type",
            "item_name": name,
            "cascade_warning": len(affected) > 0,
            "cascade_count": len(affected),
            "cascade_events": [e.name for e in affected],
        },
    )
