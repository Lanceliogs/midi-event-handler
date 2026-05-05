from __future__ import annotations

from collections import Counter

from midi_event_handler.core.events.models import MidiEvent
from midi_event_handler.core.exceptions import duplicate_event_names

import logging

log = logging.getLogger(__name__)


class MidiEventIndex:
    def __init__(self, events: list[MidiEvent] | None = None):
        self._signature_map: dict[tuple[str, tuple[int, ...]], list[MidiEvent]] = {}
        self._name_map: dict[str, MidiEvent] = {}
        self._events: list[MidiEvent] = []
        if events:
            self.load(events)

    def load(self, events: list[MidiEvent]):
        self._signature_map.clear()
        self._name_map.clear()
        self._events = events

        counts = Counter(e.name for e in events)
        dupes = sorted(name for name, count in counts.items() if count > 1)
        if dupes:
            raise duplicate_event_names(dupes)

        for event in events:
            if event.chord_signature() not in self._signature_map:
                self._signature_map[event.chord_signature()] = []
            self._signature_map[event.chord_signature()].append(event)
            self._name_map[event.name] = event

    def lookup_by_signature(self, signature: tuple[str, tuple[int, ...]]) -> list[MidiEvent]:
        return self._signature_map.get(signature, [])

    def lookup_by_name(self, name: str) -> MidiEvent | None:
        return self._name_map.get(name)
