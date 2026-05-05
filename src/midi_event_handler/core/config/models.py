"""
Configuration models.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional, List

from midi_event_handler.core.events.models import MidiEvent


@dataclass
class Mapping:
    """Complete mapping configuration."""

    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    event_types: List[str] = field(default_factory=list)
    events: List[MidiEvent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Mapping":
        """Load mapping from YAML-style dictionary."""
        events = []
        for e in data.get("events", []):
            try:
                events.append(MidiEvent.from_dict(e))
            except Exception:
                pass  # Skip invalid events

        return cls(
            inputs=list(data.get("inputs", [])),
            outputs=list(data.get("outputs", [])),
            event_types=list(data.get("event_types", [])),
            events=events,
        )

    def to_dict(self) -> dict:
        """Convert to YAML-style dictionary."""
        return {
            "inputs": self.inputs,
            "outputs": self.outputs,
            "event_types": self.event_types,
            "events": [e.to_dict() for e in self.events],
        }

    def get_event(self, name: str) -> Optional[MidiEvent]:
        """Find event by name."""
        for e in self.events:
            if e.name == name:
                return e
        return None

    def get_events_by_type(self, event_type: str) -> List[MidiEvent]:
        """Get all events of a given type."""
        return [e for e in self.events if e.type == event_type]

    def get_event_names(self) -> List[str]:
        """Get list of all event names."""
        return [e.name for e in self.events]

    def duplicate_event_names(self) -> List[str]:
        """Return names that appear more than once."""
        counts = Counter(e.name for e in self.events)
        return sorted(name for name, count in counts.items() if count > 1)

    def __eq__(self, other: "Mapping") -> bool:
        """Compare mappings for equality."""
        if not isinstance(other, Mapping):
            return False
        return self.to_dict() == other.to_dict()


def empty_mapping() -> Mapping:
    """Create an empty mapping."""
    return Mapping()
