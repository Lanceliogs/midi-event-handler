from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Union, ClassVar
from collections import defaultdict
import yaml

from midi_event_handler.core.events.models import MidiEvent, MidiChord, MidiMessage
from midi_event_handler.core.config.loader import get_event_list

import logging
log = logging.getLogger(__name__)

class MidiEventIndex:

    def __init__(self, events: Optional[List[MidiEvent]] = None):
        self._signature_map: Dict[Tuple[str, Tuple[int, ...]], List[MidiEvent]] = {}
        self._name_map: Dict[str, MidiEvent] = {}
        self._events: List[MidiEvent] = []
        if events:
            self.load(events)

    def load(self, events: List[MidiEvent]):
        self._signature_map.clear()
        self._name_map.clear()
        self._events = events

        for event in events:
            if not event.chord_signature() in self._signature_map:
                self._signature_map[event.chord_signature()] = []
            self._signature_map[event.chord_signature()].append(event)
            self._name_map[event.name] = event

    def lookup_by_signature(self, signature: Tuple[str, Tuple[int, ...]]) -> List[MidiEvent]:
        return self._signature_map.get(signature, [])

    def lookup_by_name(self, name: str) -> Optional[MidiEvent]:
        return self._name_map.get(name)
