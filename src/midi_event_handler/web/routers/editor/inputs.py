"""
Input port CRUD routes.
"""

from html import escape

import mido
from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from fastapi.responses import Response

from midi_event_handler.core.editor import editor_state
from midi_event_handler.core.midi.utils import resolve_port

from . import common

router = APIRouter()


@router.get("/input/new")
async def input_new(request: Request):
    """New input form modal."""
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/input_form.html",
        {
            "is_new": True,
            "current_name": "",
            "available_inputs": mido.get_input_names(),
        },
    )


@router.get("/input/{name}")
async def input_edit(request: Request, name: str):
    """Edit input form modal."""
    if name not in editor_state.inputs:
        raise HTTPException(status_code=404, detail="Input not found")

    available = mido.get_input_names()
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/input_form.html",
        {
            "is_new": False,
            "current_name": name,
            "original_name": name,
            "available_inputs": available,
            "resolved_port": resolve_port(name, available),
        },
    )


@router.post("/input")
async def input_save(request: Request):
    """Save input (create or update)."""
    form = await request.form()
    name = form.get("name", "").strip()
    original_name = form.get("original_name", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if original_name:
        editor_state.update_input(original_name, name)
    else:
        if not editor_state.add_input(name):
            return Response(
                content="",
                status_code=400,
                headers={"X-Toast": f"'{name}' already exists", "X-Toast-Type": "error"},
            )

    return common.render_content(request)


@router.delete("/input/{name}")
async def input_delete(request: Request, name: str):
    """Delete input."""
    editor_state.delete_input(name)
    return common.render_content(request)


@router.get("/confirm-delete/input/{name}")
async def confirm_delete_input(request: Request, name: str):
    """Confirm delete input modal."""
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/confirm_delete.html",
        {
            "item_type": "input",
            "item_name": name,
            "cascade_warning": False,
        },
    )


@router.get("/resolve-port")
async def resolve_port_route(request: Request, name: str = "", type: str = "input", original_name: str = ""):
    """Live port resolution preview."""
    name = name.strip()
    if not name:
        return Response("")

    existing = editor_state.inputs if type == "input" else editor_state.outputs
    if name != original_name and name in existing:
        return Response('<span class="resolution-error">Already exists</span>')

    available = mido.get_input_names() if type == "input" else mido.get_output_names()
    resolved = resolve_port(name, available)

    if resolved:
        return Response(f'<span class="resolution-ok">Resolves to: {escape(resolved)}</span>')
    return Response('<span class="resolution-warn">No matching port found</span>')
