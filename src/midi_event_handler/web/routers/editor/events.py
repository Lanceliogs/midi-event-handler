"""
Event CRUD, testing (PAD), and MIDI recording routes.
"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from fastapi.responses import Response

from midi_event_handler.core.editor import editor_state, empty_event
from midi_event_handler.core.events.models import MidiEvent, MidiChord, MidiMessage
from midi_event_handler.core.exceptions import MidiAppError
from midi_event_handler.core.midi.notes import parse_notes_input, note_to_name
from midi_event_handler.core.midi.recorder import MidiRecorder

from . import common

import logging

log = logging.getLogger(__name__)

router = APIRouter()

# Track active recordings per port (stores the recorder instance for abort)
_active_recordings: dict[str, MidiRecorder] = {}


# =============================================================================
# Helpers
# =============================================================================


def _messages_to_json(messages: list) -> str:
    """Convert MidiMessage list to JSON string."""
    return json.dumps([{"port": m.port, "type": m.type, "note": m.note, "velocity": m.velocity} for m in messages])


# =============================================================================
# Event CRUD
# =============================================================================


@router.get("/event/new")
async def event_new(request: Request):
    """New event form modal."""
    event = empty_event()
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/event_form.html",
        {
            "is_new": True,
            "event": event,
            "inputs": editor_state.inputs,
            "outputs": editor_state.outputs,
            "event_types": editor_state.event_types,
            "event_names": [e.name for e in editor_state.events],
            "start_messages_json": _messages_to_json(event.start_messages),
            "end_messages_json": _messages_to_json(event.end_messages),
        },
    )


@router.get("/event/{name}")
async def event_edit(request: Request, name: str):
    """Edit event form modal."""
    event = editor_state.get_event(name)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/event_form.html",
        {
            "is_new": False,
            "event": event,
            "original_name": name,
            "inputs": editor_state.inputs,
            "outputs": editor_state.outputs,
            "event_types": editor_state.event_types,
            "event_names": [e.name for e in editor_state.events if e.name != name],
            "start_messages_json": _messages_to_json(event.start_messages),
            "end_messages_json": _messages_to_json(event.end_messages),
        },
    )


@router.post("/event")
async def event_save(request: Request):
    """Save event (create or update)."""
    form = await request.form()
    original_name = form.get("original_name", "").strip()
    name = form.get("name", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    notes_str = form.get("trigger_notes", "").strip()
    notes = []
    if notes_str:
        try:
            notes = parse_notes_input(notes_str)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Parse messages from JSON
    start_messages = []
    end_messages = []

    start_messages_json = form.get("start_messages", "[]")
    end_messages_json = form.get("end_messages", "[]")

    try:
        start_msgs_data = json.loads(start_messages_json) if start_messages_json else []
        for m in start_msgs_data:
            start_messages.append(
                MidiMessage(
                    type=m.get("type", "note_on"),
                    note=int(m.get("note", 0)),
                    velocity=int(m.get("velocity", 100)),
                    port=m.get("port", ""),
                )
            )
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        log.warning(f"Failed to parse start_messages: {e}")

    try:
        end_msgs_data = json.loads(end_messages_json) if end_messages_json else []
        for m in end_msgs_data:
            end_messages.append(
                MidiMessage(
                    type=m.get("type", "note_off"),
                    note=int(m.get("note", 0)),
                    velocity=int(m.get("velocity", 0)),
                    port=m.get("port", ""),
                )
            )
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        log.warning(f"Failed to parse end_messages: {e}")

    event = MidiEvent(
        name=name,
        type=form.get("type", "").strip(),
        chord=MidiChord(
            port=form.get("trigger_port", "").strip(),
            notes=notes,
        ),
        start_messages=start_messages,
        end_messages=end_messages,
        duration_min=int(form.get("duration_min") or 0) or None,
        duration_max=int(form.get("duration_max") or 0) or None,
        fallback_event=form.get("fallback_event", "").strip() or None,
        comment=form.get("comment", "").strip() or None,
    )

    if original_name:
        editor_state.update_event(original_name, event)
    else:
        editor_state.add_event(event)

    return common.render_content(request)


@router.delete("/event/{name}")
async def event_delete(request: Request, name: str):
    """Delete event."""
    editor_state.delete_event(name)
    return common.render_content(request)


@router.get("/confirm-delete/event/{name}")
async def confirm_delete_event(request: Request, name: str):
    """Confirm delete event modal."""
    return common.templates.TemplateResponse(
        request,
        "partials/editor/modals/confirm_delete.html",
        {
            "item_type": "event",
            "item_name": name,
            "cascade_warning": False,
        },
    )


# =============================================================================
# Event Testing (PAD)
# =============================================================================


@router.post("/event/{name}/play")
async def event_play(request: Request, name: str):
    """Manually trigger (play) an event."""
    if not common.midiapp or not common.midiapp.running:
        return Response(
            content='{"error": "App is not running"}',
            media_type="application/json",
            status_code=400,
        )

    success = await common.midiapp.trigger_event(name)
    if success:
        return common.render_content(request)
    return Response(
        content='{"error": "Failed to trigger event"}',
        media_type="application/json",
        status_code=400,
    )


@router.post("/event/{name}/stop")
async def event_stop(request: Request, name: str):
    """Manually stop an active event."""
    if not common.midiapp or not common.midiapp.running:
        return Response(
            content='{"error": "App is not running"}',
            media_type="application/json",
            status_code=400,
        )

    success = await common.midiapp.stop_event(name)
    if success:
        return common.render_content(request)
    return Response(
        content='{"error": "Event is not active"}',
        media_type="application/json",
        status_code=400,
    )


# =============================================================================
# MIDI Recording
# =============================================================================


@router.post("/event/{name}/trigger")
async def event_update_trigger(request: Request, name: str):
    """Update an event's trigger notes from recording."""
    event = editor_state.get_event(name)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    form = await request.form()
    notes_str = form.get("notes", "")

    if notes_str:
        notes = parse_notes_input(notes_str)
        event.chord.notes = notes
        editor_state.update_event(name, event)

    return common.render_content(request)


@router.post("/record")
async def record_midi(request: Request):
    """Record MIDI notes from a port (5s timeout)."""
    data = await request.json()
    port = data.get("port", "")

    if common.midiapp and common.midiapp.running:
        return Response(
            content='{"error": "Cannot record while app is running. Stop the app first."}',
            media_type="application/json",
            status_code=400,
        )

    # Prevent concurrent recordings on the same port
    if port in _active_recordings:
        return Response(
            content='{"error": "Recording already in progress on this port"}',
            media_type="application/json",
            status_code=409,
        )

    recorder = MidiRecorder(port, timeout=5.0)
    _active_recordings[port] = recorder
    try:
        notes = await recorder.record()

        if notes:
            return {"notes": [note_to_name(n) for n in notes]}
        elif recorder.was_aborted:
            return {"aborted": True}
        else:
            return {"timeout": True}

    except MidiAppError as e:
        return Response(
            content=f'{{"error": "{e.short_message}"}}',
            media_type="application/json",
            status_code=400,
        )
    finally:
        _active_recordings.pop(port, None)


@router.post("/record/abort")
async def abort_recording(request: Request):
    """Abort an active recording on a port."""
    data = await request.json()
    port = data.get("port", "")

    recorder = _active_recordings.get(port)
    if recorder:
        await recorder.abort()
        return {"aborted": True}
    return {"aborted": False}


@router.get("/resolve-note")
async def resolve_note_route(note: str = ""):
    """Resolve a note input to number and name."""
    if not note:
        return Response(status_code=400)

    note = note.strip()

    try:
        notes = parse_notes_input(note)
        if notes:
            note_num = notes[0]
            return {"num": note_num, "name": note_to_name(note_num)}
    except Exception:
        pass

    return Response(status_code=400)
