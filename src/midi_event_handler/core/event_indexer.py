from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Union, ClassVar
from collections import defaultdict
import yaml

from midi_event_handler.core.event_models import MidiEvent, MidiMessage, MidiChord


@dataclass
class MidiEventIndex:
    _index: Dict[Tuple[str, Tuple[int, ...]], List[MidiEvent]]

    # Global registry of named sets
    registry: ClassVar[Dict[str, "MidiEventIndex"]] = {}

    @classmethod
    def from_events(cls, events: List[MidiEvent]) -> "MidiEventIndex":
        index: Dict[Tuple[str, Tuple[int, ...]], List[MidiEvent]] = defaultdict(list)
        for event in events:
            key = event.chord_signature()
            index[key].append(event)
        return cls(index)

    @classmethod
    def from_yaml(cls, path: Union[str, Path], name: Optional[str] = "__root__") -> "MidiEventIndex":
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

        index = cls.from_events(events)

        # Optional registration
        if name:
            cls.registry[name] = index
        else:
            cls.registry["__root__"] = index

        return index

    @classmethod
    def get(cls, name: str) -> Optional["MidiEventIndex"]:
        return cls.registry.get(name)

    @classmethod
    def lookup_from(cls, name: str, chord: MidiChord) -> Optional[MidiEvent]:
        index = cls.get(name)
        if index:
            return index.lookup(chord)
        return None

    def lookup(self, chord: MidiChord) -> Optional[MidiEvent]:
        return self._index.get(chord.signature())
