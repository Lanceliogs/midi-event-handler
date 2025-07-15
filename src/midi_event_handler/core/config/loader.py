import yaml
import os
from pathlib import Path
from typing import Dict, List

from midi_event_handler.core.events.models import MidiChord, MidiEvent, MidiMessage


# Load mapping.yaml once
_config_path = Path(os.getenv("MEHAPP_MAPPING_YAML", "mapping.yaml"))
with _config_path.open("r") as f:
    _raw: Dict = yaml.safe_load(f)


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
