from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple
import mido

import logging

log = logging.getLogger(__name__)


@dataclass
class MidiMessage:
    type: str
    note: int
    velocity: int
    port: str

    @classmethod
    def from_mido(cls, message: mido.Message, port: str) -> "MidiMessage":
        return cls(
            type=message.type,
            note=message.note,
            velocity=message.velocity,
            port=port,
        )

    def to_mido(self) -> mido.Message:
        return mido.Message(
            type=self.type,
            note=self.note,
            velocity=self.velocity,
        )


@dataclass
class MidiChord:
    notes: List[int]
    port: str

    def __post_init__(self):
        object.__setattr__(self, "notes", sorted(self.notes))

    def __str__(self):
        return f"{self.port} - Chord({', '.join(map(str, self.notes))})"

    def signature(self) -> Tuple[str, Tuple[int, ...]]:
        return (self.port, tuple(self.notes))

    def contains(self, note: int) -> bool:
        return note in self.notes


@dataclass
class MidiEvent:
    name: str
    type: str
    chord: MidiChord
    start_messages: List[MidiMessage] = field(default_factory=list)
    end_messages: List[MidiMessage] = field(default_factory=list)
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None
    fallback_event: Optional[str] = None
    comment: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MidiEvent":
        """Create MidiEvent from YAML-style dictionary.

        Raises TypeError/ValueError on malformed data (caught by Mapping.from_dict).
        """
        if not data.get("name"):
            raise ValueError("Event is missing a 'name' field")

        trigger = data.get("trigger", {})
        chord = MidiChord(notes=trigger.get("notes", []), port=trigger.get("port", ""))

        start = [MidiMessage(**m) for m in data.get("start_messages", [])]
        end = [MidiMessage(**m) for m in data.get("end_messages", [])]

        return cls(
            name=data.get("name", ""),
            type=data.get("type", ""),
            chord=chord,
            start_messages=start,
            end_messages=end,
            duration_min=data.get("duration_min"),
            duration_max=data.get("duration_max"),
            fallback_event=data.get("fallback_event"),
            comment=data.get("comment"),
        )

    def to_dict(self) -> dict:
        """Convert to YAML-style dictionary."""
        d = {
            "name": self.name,
            "type": self.type,
            "trigger": {
                "port": self.chord.port,
                "notes": list(self.chord.notes),
            },
        }

        if self.start_messages:
            d["start_messages"] = [asdict(m) for m in self.start_messages]
        if self.end_messages:
            d["end_messages"] = [asdict(m) for m in self.end_messages]
        if self.duration_min is not None:
            d["duration_min"] = self.duration_min
        if self.duration_max is not None:
            d["duration_max"] = self.duration_max
        if self.fallback_event:
            d["fallback_event"] = self.fallback_event
        if self.comment:
            d["comment"] = self.comment

        return d

    def chord_signature(self) -> Tuple[str, Tuple[int, ...]]:
        return self.chord.signature()

    def __repr__(self):
        return f"<MidiEvent: name={self.name} type={self.type}>"

    def __eq__(self, other: "MidiEvent") -> bool:
        if not isinstance(other, MidiEvent):
            return False
        return self.to_dict() == other.to_dict()


def empty_event() -> MidiEvent:
    """Create an empty event for forms."""
    return MidiEvent(
        name="",
        type="",
        chord=MidiChord(notes=[], port=""),
    )
