from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

import mido
from midi_event_handler.core.midi.outputs import MidiOutputManager

from midi_event_handler.tools import logtools

log = logtools.get_logger(__name__)

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

    def chord_signature(self) -> Tuple[str, Tuple[int, ...]]:
        return self.keys.signature()
