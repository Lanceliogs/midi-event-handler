import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional

from midi_event_handler.core.events.models import MidiChord, MidiEvent, MidiMessage
from midi_event_handler.tools import logtools

log = logtools.get_logger(__name__)

RUNTIME_MAPPING_PATH = Path(".runtime/mapping.yaml")
_raw: Optional[Dict] = None

def load_mapping_yaml(path: Optional[Path]):
    global _raw

    path = path or RUNTIME_MAPPING_PATH
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")

    log.info("Loading mapping file: %s", path)
    with path.open("r") as f:
        _raw = yaml.safe_load(f)


def get_configured_inputs() -> List[str]:
    return _raw.get("inputs", [])


def get_configured_outputs() -> List[str]:
    return _raw.get("outputs", [])


def get_event_types() -> List[str]:
    return _raw.get("event_types", [])


def get_event_list() -> List[MidiEvent]:
    events = []

    for e in _raw.get("events", []):
        chord = MidiChord(
            notes=e["trigger"]["notes"],
            port=e["trigger"]["port"]
        )

        start = [MidiMessage(**m) for m in e.get("start_messages", [])]
        end = [MidiMessage(**m) for m in e.get("end_messages", [])]

        event = MidiEvent(
            name=e["name"],
            type=e["type"],
            chord=chord,
            start_messages=start,
            end_messages=end,
            duration_min=e.get("duration_min"),
            duration_max=e.get("duration_max"),
            fallback_event=e.get("fallback_event"),
        )
        events.append(event)

    return events
