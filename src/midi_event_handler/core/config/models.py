"""
Configuration models.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field

from midi_event_handler.core.events.models import MidiEvent

log = logging.getLogger(__name__)


@dataclass
class Mapping:
    """Complete mapping configuration."""

    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)
    events: list[MidiEvent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Mapping":
        """Load mapping from YAML-style dictionary."""
        events = []
        skipped = 0
        for i, e in enumerate(data.get("events", [])):
            try:
                events.append(MidiEvent.from_dict(e))
            except Exception as exc:
                log.warning(f"Skipping invalid event at index {i}: {exc}")
                skipped += 1
        if skipped:
            log.warning(f"Skipped {skipped} invalid event(s) while loading mapping")

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

    def get_event(self, name: str) -> MidiEvent | None:
        """Find event by name."""
        for e in self.events:
            if e.name == name:
                return e
        return None

    def get_events_by_type(self, event_type: str) -> list[MidiEvent]:
        """Get all events of a given type."""
        return [e for e in self.events if e.type == event_type]

    def get_event_names(self) -> list[str]:
        """Get list of all event names."""
        return [e.name for e in self.events]

    def _duplicates(self, items: list[str]) -> list[str]:
        """Return items that appear more than once."""
        counts = Counter(items)
        return sorted(name for name, count in counts.items() if count > 1)

    def duplicate_inputs(self) -> list[str]:
        return self._duplicates(self.inputs)

    def duplicate_outputs(self) -> list[str]:
        return self._duplicates(self.outputs)

    def duplicate_event_types(self) -> list[str]:
        return self._duplicates(self.event_types)

    def duplicate_event_names(self) -> list[str]:
        return self._duplicates([e.name for e in self.events])

    def __eq__(self, other: "Mapping") -> bool:
        """Compare mappings for equality."""
        if not isinstance(other, Mapping):
            return False
        return self.to_dict() == other.to_dict()


def empty_mapping() -> Mapping:
    """Create an empty mapping."""
    return Mapping()
