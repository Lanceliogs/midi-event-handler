"""
Output port CRUD routes.
"""

import mido
from fastapi import APIRouter, HTTPException
from fastapi.requests import Request

from midi_event_handler.core.editor import editor_state
from midi_event_handler.core.midi.utils import resolve_port

from . import common

router = APIRouter()


@router.get("/output/new")
async def output_new(request: Request):
    """New output form modal."""
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/output_form.html",
        {
            "is_new": True,
            "current_name": "",
            "available_outputs": mido.get_output_names(),
        },
    )


@router.get("/output/{name}")
async def output_edit(request: Request, name: str):
    """Edit output form modal."""
    if name not in editor_state.outputs:
        raise HTTPException(status_code=404, detail="Output not found")

    available = mido.get_output_names()
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/output_form.html",
        {
            "is_new": False,
            "current_name": name,
            "original_name": name,
            "available_outputs": available,
            "resolved_port": resolve_port(name, available),
        },
    )


@router.post("/output")
async def output_save(request: Request):
    """Save output (create or update)."""
    form = await request.form()
    name = form.get("name", "").strip()
    original_name = form.get("original_name", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if original_name:
        editor_state.update_output(original_name, name)
    else:
        editor_state.add_output(name)

    return common.render_content(request)


@router.delete("/output/{name}")
async def output_delete(request: Request, name: str):
    """Delete output."""
    editor_state.delete_output(name)
    return common.render_content(request)


@router.get("/confirm-delete/output/{name}")
async def confirm_delete_output(request: Request, name: str):
    """Confirm delete output modal."""
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/confirm_delete.html",
        {
            "item_type": "output",
            "item_name": name,
            "cascade_warning": False,
        },
    )
