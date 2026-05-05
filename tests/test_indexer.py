"""Tests for MidiEventIndex."""

import pytest
from midi_event_handler.core.events.models import MidiEvent, MidiChord
from midi_event_handler.core.events.indexer import MidiEventIndex
from midi_event_handler.core.exceptions import MidiAppError, ErrorCode


def make_event(name: str, event_type: str, notes: list, port: str = "input1") -> MidiEvent:
    """Helper to create test events."""
    chord = MidiChord(notes=notes, port=port)
    return MidiEvent(name=name, type=event_type, chord=chord)


class TestMidiEventIndex:
    """Tests for MidiEventIndex class."""

    def test_empty_index(self):
        index = MidiEventIndex()

        assert index.lookup_by_name("anything") is None
        assert index.lookup_by_signature(("input1", (60,))) == []

    def test_load_events(self):
        events = [
            make_event("event1", "light", [60]),
            make_event("event2", "music", [64]),
        ]
        index = MidiEventIndex(events)

        assert index.lookup_by_name("event1") == events[0]
        assert index.lookup_by_name("event2") == events[1]

    def test_lookup_by_name(self):
        event = make_event("my_event", "light", [60])
        index = MidiEventIndex([event])

        assert index.lookup_by_name("my_event") == event
        assert index.lookup_by_name("nonexistent") is None

    def test_lookup_by_signature(self):
        event = make_event("event1", "light", [60, 64], port="input1")
        index = MidiEventIndex([event])

        sig = ("input1", (60, 64))
        result = index.lookup_by_signature(sig)

        assert len(result) == 1
        assert result[0] == event

    def test_lookup_by_signature_not_found(self):
        event = make_event("event1", "light", [60])
        index = MidiEventIndex([event])

        result = index.lookup_by_signature(("input1", (64,)))
        assert result == []

    def test_multiple_events_same_signature(self):
        """Multiple events can have the same chord signature."""
        event1 = make_event("event1", "light", [60])
        event2 = make_event("event2", "music", [60])  # Same chord, different type
        index = MidiEventIndex([event1, event2])

        sig = ("input1", (60,))
        result = index.lookup_by_signature(sig)

        assert len(result) == 2
        assert event1 in result
        assert event2 in result

    def test_different_ports_different_signatures(self):
        event1 = make_event("event1", "light", [60], port="input1")
        event2 = make_event("event2", "light", [60], port="input2")
        index = MidiEventIndex([event1, event2])

        result1 = index.lookup_by_signature(("input1", (60,)))
        result2 = index.lookup_by_signature(("input2", (60,)))

        assert len(result1) == 1
        assert result1[0].name == "event1"
        assert len(result2) == 1
        assert result2[0].name == "event2"

    def test_reload_clears_previous(self):
        event1 = make_event("event1", "light", [60])
        index = MidiEventIndex([event1])

        assert index.lookup_by_name("event1") is not None

        event2 = make_event("event2", "music", [64])
        index.load([event2])

        assert index.lookup_by_name("event1") is None
        assert index.lookup_by_name("event2") is not None

    def test_chord_notes_order_independent(self):
        """Looking up by signature should work regardless of note order in chord."""
        event = make_event("event1", "light", [67, 60, 64])  # Will be sorted to [60, 64, 67]
        index = MidiEventIndex([event])

        # The signature should use sorted notes
        sig = ("input1", (60, 64, 67))
        result = index.lookup_by_signature(sig)

        assert len(result) == 1
        assert result[0].name == "event1"

    def test_duplicate_names_rejected(self):
        """Loading events with duplicate names should raise MidiAppError."""
        events = [
            make_event("same_name", "light", [60]),
            make_event("same_name", "music", [64]),
        ]

        with pytest.raises(MidiAppError) as exc_info:
            MidiEventIndex(events)

        assert exc_info.value.code == ErrorCode.DUPLICATE_EVENT_NAMES
        assert "Duplicate event names" in exc_info.value.short_message

    def test_duplicate_names_rejected_on_reload(self):
        """Reloading with duplicate names should also raise."""
        index = MidiEventIndex([make_event("ok", "light", [60])])

        events = [
            make_event("dup", "light", [60]),
            make_event("unique", "music", [61]),
            make_event("dup", "music", [62]),
        ]

        with pytest.raises(MidiAppError) as exc_info:
            index.load(events)

        assert exc_info.value.code == ErrorCode.DUPLICATE_EVENT_NAMES
