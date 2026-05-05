"""
Mapping API routes: save, download, diff.
"""

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.responses import Response

from midi_event_handler.core.app import MidiApp
from midi_event_handler.core.editor import editor_state

from midi_event_handler.web import context
from midi_event_handler.web.context import get_midiapp

router = APIRouter()


@router.get("/api/mapping")
async def get_mapping():
    """Get current editor mapping as JSON."""
    editor_state.load_from_runtime()
    return {"mapping": editor_state.mapping, "dirty": editor_state.dirty}


@router.get("/api/mapping/download")
async def download_mapping():
    """Download current mapping as YAML file."""
    editor_state.load_from_runtime()
    return Response(
        content=editor_state.to_yaml(),
        media_type="application/x-yaml",
        headers={"Content-Disposition": 'attachment; filename="mapping.yml"'},
    )


@router.get("/save-confirm")
async def save_confirm(request: Request, midiapp: MidiApp = Depends(get_midiapp)):
    """Show save confirmation modal with diff."""
    if midiapp.running:
        return context.templates.TemplateResponse(
            request,
            "partials/editor/modals/save_blocked.html",
            {
                "reason": "Cannot save while app is running. Stop it first.",
            },
        )

    all_dupes = (
        editor_state.mapping.duplicate_inputs()
        + editor_state.mapping.duplicate_outputs()
        + editor_state.mapping.duplicate_event_types()
        + editor_state.mapping.duplicate_event_names()
    )
    if all_dupes:
        return context.templates.TemplateResponse(
            request,
            "partials/editor/modals/save_blocked.html",
            {
                "reason": "Duplicates found. Rename or delete them before saving.",
                "duplicate_names": all_dupes,
            },
        )

    return context.templates.TemplateResponse(
        request,
        "partials/editor/modals/save_confirm.html",
        {
            "diff": editor_state.compute_diff(),
            "has_changes": editor_state.has_changes(),
        },
    )


@router.post("/api/mapping/save")
async def save_mapping(request: Request, midiapp: MidiApp = Depends(get_midiapp)):
    """Save current editor state to runtime file."""
    if midiapp.running:
        return Response(
            content='<span class="feedback-error">Cannot save while app is running.</span>',
            media_type="text/html",
        )

    if editor_state.save_to_runtime():
        midiapp.reload_mapping()
        return Response(
            content='<span class="feedback-success">Mapping saved!</span>',
            media_type="text/html",
        )
    return Response(
        content='<span class="feedback-error">Failed to save mapping</span>',
        media_type="text/html",
    )
