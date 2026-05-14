"""Tests for core event models."""

import mido
from midi_event_handler.core.events.models import (
    MidiMessage,
    MidiChord,
    MidiEvent,
)


class TestMidiMessage:
    """Tests for MidiMessage dataclass."""

    def test_create_message(self):
        msg = MidiMessage(type="note_on", note=60, velocity=100, port="input1")
        assert msg.type == "note_on"
        assert msg.note == 60
        assert msg.velocity == 100
        assert msg.port == "input1"

    def test_from_mido(self):
        mido_msg = mido.Message("note_on", note=64, velocity=80)
        msg = MidiMessage.from_mido(mido_msg, "testport")

        assert msg.type == "note_on"
        assert msg.note == 64
        assert msg.velocity == 80
        assert msg.port == "testport"

    def test_to_mido(self):
        msg = MidiMessage(type="note_off", note=72, velocity=0, port="output1")
        mido_msg = msg.to_mido()

        assert mido_msg.type == "note_off"
        assert mido_msg.note == 72
        assert mido_msg.velocity == 0


class TestMidiChord:
    """Tests for MidiChord dataclass."""

    def test_create_chord(self):
        chord = MidiChord(notes=[60, 64, 67], port="input1")
        assert chord.notes == [60, 64, 67]
        assert chord.port == "input1"

    def test_notes_sorted(self):
        """Notes should be sorted on creation."""
        chord = MidiChord(notes=[67, 60, 64], port="input1")
        assert chord.notes == [60, 64, 67]

    def test_signature(self):
        chord = MidiChord(notes=[60, 64, 67], port="input1")
        sig = chord.signature()

        assert sig == ("input1", (60, 64, 67))
        assert isinstance(sig[1], tuple)  # Should be tuple, not list

    def test_signature_consistent(self):
        """Same notes in different order should have same signature."""
        chord1 = MidiChord(notes=[60, 64, 67], port="input1")
        chord2 = MidiChord(notes=[67, 60, 64], port="input1")

        assert chord1.signature() == chord2.signature()

    def test_signature_different_ports(self):
        """Different ports should have different signatures."""
        chord1 = MidiChord(notes=[60], port="input1")
        chord2 = MidiChord(notes=[60], port="input2")

        assert chord1.signature() != chord2.signature()

    def test_contains(self):
        chord = MidiChord(notes=[60, 64, 67], port="input1")

        assert chord.contains(60)
        assert chord.contains(64)
        assert chord.contains(67)
        assert not chord.contains(61)
        assert not chord.contains(0)

    def test_str(self):
        chord = MidiChord(notes=[60, 64], port="input1")
        s = str(chord)

        assert "input1" in s
        assert "60" in s
        assert "64" in s


class TestMidiEvent:
    """Tests for MidiEvent dataclass."""

    def test_create_minimal_event(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(name="test_event", type="light", chord=chord)

        assert event.name == "test_event"
        assert event.type == "light"
        assert event.chord == chord
        assert event.start_messages == []
        assert event.end_messages == []
        assert event.duration_min is None
        assert event.duration_max is None
        assert event.fallback_event is None
        assert event.comment is None
        assert event._priority is None
        assert event.priority == 0
        assert "priority" not in event.to_dict()

    def test_create_full_event(self):
        chord = MidiChord(notes=[60, 64], port="input1")
        start_msg = MidiMessage(type="note_on", note=100, velocity=127, port="output1")
        end_msg = MidiMessage(type="note_off", note=100, velocity=0, port="output1")

        event = MidiEvent(
            name="full_event",
            type="music",
            chord=chord,
            start_messages=[start_msg],
            end_messages=[end_msg],
            duration_min=5,
            duration_max=30,
            fallback_event="default_event",
        )

        assert event.name == "full_event"
        assert len(event.start_messages) == 1
        assert len(event.end_messages) == 1
        assert event.duration_min == 5
        assert event.duration_max == 30
        assert event.fallback_event == "default_event"

    def test_event_with_comment(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(
            name="commented_event",
            type="light",
            chord=chord,
            comment="This is a test comment",
        )

        assert event.comment == "This is a test comment"

    def test_chord_signature(self):
        chord = MidiChord(notes=[60, 64], port="input1")
        event = MidiEvent(name="test", type="light", chord=chord)

        assert event.chord_signature() == chord.signature()

    def test_equality_by_dict(self):
        chord = MidiChord(notes=[60], port="input1")

        event1 = MidiEvent(name="same_name", type="light", chord=chord)
        event2 = MidiEvent(name="same_name", type="light", chord=chord)
        assert event1 == event2

    def test_inequality_different_content(self):
        chord1 = MidiChord(notes=[60], port="input1")
        chord2 = MidiChord(notes=[64], port="input2")

        event1 = MidiEvent(name="same_name", type="light", chord=chord1)
        event2 = MidiEvent(name="same_name", type="music", chord=chord2)
        event3 = MidiEvent(name="different_name", type="light", chord=chord1)

        assert event1 != event2  # Same name, different content
        assert event1 != event3  # Different name

    def test_equality_with_non_event(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(name="test", type="light", chord=chord)

        assert event != "not an event"
        assert event is not None

    def test_repr(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(name="test_event", type="light", chord=chord)
        r = repr(event)

        assert "test_event" in r
        assert "light" in r

    def test_to_dict(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(name="test", type="light", chord=chord)
        d = event.to_dict()

        assert isinstance(d, dict)
        assert d["name"] == "test"
        assert d["type"] == "light"
        assert d["trigger"]["notes"] == [60]
        assert d["trigger"]["port"] == "input1"

    def test_to_dict_without_priority_key_when_unspecified(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(name="test", type="light", chord=chord)
        assert "priority" not in event.to_dict()

    def test_to_dict_includes_explicit_priority_zero(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(name="test", type="light", chord=chord, _priority=0)
        assert event.to_dict().get("priority") == 0

    def test_priority_property_and_setter(self):
        chord = MidiChord(notes=[60], port="input1")
        event = MidiEvent(name="test", type="light", chord=chord)
        assert event.priority == 0
        event.priority = None
        assert event._priority is None
        event.priority = 5
        assert event._priority == 5
        assert event.priority == 5

    def test_from_dict_omitted_priority_vs_explicit(self):
        base = {"name": "x", "type": "light", "trigger": {"port": "input1", "notes": [60]}}

        e1 = MidiEvent.from_dict({**base})
        assert e1._priority is None
        assert e1.priority == 0
        assert "priority" not in e1.to_dict()

        e2 = MidiEvent.from_dict({**base, "priority": 3})
        assert e2._priority == 3
        assert e2.to_dict().get("priority") == 3

        e3 = MidiEvent.from_dict({**base, "priority": 0})
        assert e3._priority == 0
        assert e3.to_dict().get("priority") == 0

        e4 = MidiEvent.from_dict({**base, "priority": None})
        assert e4._priority is None
