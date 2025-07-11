from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Union, ClassVar
from collections import defaultdict
import yaml

from midi_event_handler.core.event_models import MidiEvent, MidiMessage, MidiChord

from midi_event_handler.tools import logtools
log = logtools.get_logger(__name__)

class MidiEventIndex:
    _index_by_signatures: Dict[Tuple[str, Tuple[int, ...]], List[MidiEvent]] = {}
    _index_by_names: Dict[str, List[MidiEvent]] = {}

    @staticmethod
    def from_events(events: List[MidiEvent]) -> "MidiEventIndex":
        MidiEventIndex._index_by_signatures.clear()
        MidiEventIndex._index_by_names.clear()
        for event in events:
            key = event.chord_signature()
            MidiEventIndex._index_by_signatures[key].append(event)
            MidiEventIndex._index_by_names[event.name].append(event)

    @staticmethod
    def from_yaml(path: Union[str, Path]):
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        events = []
        for e in raw["events"]:
            chord = MidiChord(
                notes=e["trigger"]["notes"],
                port=e["trigger"]["port"]
            )
            start = [MidiMessage(**m) for m in e.get("start_messages", [])]
            end = [MidiMessage(**m) for m in e.get("end_messages", [])]
            
            event = MidiEvent(
                name=e["name"],
                type=e["type"],
                port=e["port"],
                chord=chord,
                start_messages=start,
                end_messages=end,
                duration_min=e.get("duration_min"),
                duration_max=e.get("duration_max"),
                fallback_event=e.get("fallback_event"),
            )
            events.append(event)

        MidiEventIndex.from_events(events)

    @staticmethod
    def lookup_by_chord(chord: MidiChord) -> Optional[MidiEvent]:
        return MidiEventIndex._index_by_signatures.get(chord.signature())
    
    @staticmethod
    def lookup_by_name(name: str) -> Optional[MidiEvent]:
        return MidiEventIndex._index_by_names.get(name)

