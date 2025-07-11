from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class MidiMessage:
    type: str
    note: int
    velocity: int

@dataclass
class MidiEvent:
    name: str
    type: str
    port: str
    keys: List[int]
    start_messages: List[MidiMessage]
    end_messages: List[MidiMessage]
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None
    fallback_event: Optional[str] = None

