"""
JSON API routes: /meh/api/*
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.requests import Request
from fastapi.responses import Response
from pathlib import Path
import shutil
import mido
import os

from midi_event_handler.core.config import RUNTIME_PATH, get_current_version
from midi_event_handler.core.app import MidiApp
from midi_event_handler.core.editor import editor_state

import logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/meh/api", tags=["api"])

# Shared MidiApp instance - will be set by main app
midiapp: MidiApp = None

def set_midiapp(app: MidiApp):
    global midiapp
    midiapp = app


@router.post("/upload-mapping")
async def upload_mapping(file: UploadFile = File(...)):
    if midiapp.running:
        return Response(
            content='',
            status_code=400,
            headers={"X-Toast": "Stop the app before loading a new mapping", "X-Toast-Type": "error"}
        )
    if not (file.filename.endswith(".yaml") or file.filename.endswith(".yml")):
        return Response(
            content='',
            status_code=400,
            headers={"X-Toast": "File must be .yaml or .yml", "X-Toast-Type": "error"}
        )

    RUNTIME_PATH.mkdir(exist_ok=True)
    mapping_path = RUNTIME_PATH / "mapping.yaml"

    try:
        with mapping_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        midiapp.reload_mapping()
    except Exception as e:
        log.exception("Failed to upload or reload mapping")
        return Response(
            content='',
            status_code=500,
            headers={"X-Toast": f"Failed to load mapping: {str(e)}", "X-Toast-Type": "error"}
        )

    return Response(
        content='',
        headers={"X-Toast": f"Loaded {file.filename}", "X-Toast-Type": "success"}
    )


@router.post("/start")
async def start_show():
    import json
    
    if midiapp.running:
        return Response(
            content='',
            headers={"X-Toast": "Already running", "X-Toast-Type": "warning"}
        )
    
    if editor_state.dirty:
        return Response(
            content='',
            status_code=400,
            headers={"X-Toast": "Save changes before starting", "X-Toast-Type": "error"}
        )
    
    try:
        result = await midiapp.start()
        
        if result.success:
            return Response(
                content='',
                headers={"X-Toast": "MIDI app started", "X-Toast-Type": "success"}
            )
        else:
            # Build detailed error response for toast details button
            error_data = {
                "running": False,
                "errors": result.error_details,
            }
            
            return Response(
                content=json.dumps(error_data),
                media_type="application/json",
                status_code=400,
                headers={
                    "X-Toast": result.error_message,
                    "X-Toast-Type": "error",
                },
            )
    except Exception as e:
        log.exception("Failed to start MIDI app")
        return Response(
            content='',
            status_code=500,
            headers={"X-Toast": f"Unexpected error: {str(e)}", "X-Toast-Type": "error"}
        )


@router.post("/stop")
async def stop_show():
    if not midiapp.running:
        return Response(
            content='',
            headers={"X-Toast": "Already stopped", "X-Toast-Type": "warning"}
        )
    
    try:
        await midiapp.stop()
        return Response(
            content='',
            headers={"X-Toast": "MIDI app stopped", "X-Toast-Type": "success"}
        )
    except Exception as e:
        log.exception("Failed to stop MIDI app")
        return Response(
            content='',
            status_code=500,
            headers={"X-Toast": f"Failed to stop: {str(e)}", "X-Toast-Type": "error"}
        )


@router.get("/status")
async def get_status():
    return midiapp.get_status()


@router.get("/ports")
async def get_ports():
    """Get all available MIDI ports."""
    return {
        "inputs": mido.get_input_names(),
        "outputs": mido.get_output_names()
    }


@router.post("/restart")
async def request_restart():
    Path(".runtime").mkdir(exist_ok=True)
    Path(".runtime/restart.flag").touch()
    return Response(
        content='',
        headers={"X-Toast": "Restarting...", "X-Toast-Type": "info"}
    )


@router.get("/healthz")
async def healthz(version: str = Depends(get_current_version)):
    return {
        "alive": True,
        "version": version,
        "pid": os.getpid()
    }


@router.get("/logs")
async def get_logs(lines: int = 500):
    """Get recent log entries."""
    from midi_event_handler.core.config import LOG_FILE_PATH
    
    if not LOG_FILE_PATH.exists():
        return {"logs": "", "lines": 0}
    
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        
        # Return last N lines
        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "logs": "".join(recent),
            "lines": len(recent),
            "total_lines": len(all_lines),
        }
    except Exception as e:
        log.exception("Failed to read logs")
        return {"logs": f"Error reading logs: {e}", "lines": 0}


@router.get("/logs/download")
async def download_logs():
    """Download log file."""
    from midi_event_handler.core.config import LOG_FILE_PATH
    from fastapi.responses import FileResponse
    
    if not LOG_FILE_PATH.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    return FileResponse(
        path=LOG_FILE_PATH,
        filename="meh-app.log",
        media_type="text/plain",
    )
