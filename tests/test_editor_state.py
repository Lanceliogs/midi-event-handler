"""Tests for EditorState class."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from midi_event_handler.core.editor import EditorState
from midi_event_handler.core.config import Mapping, empty_mapping
from midi_event_handler.core.events.models import MidiEvent, MidiChord


class TestEditorState:
    """Tests for EditorState class."""

    def test_empty_mapping(self):
        state = EditorState()
        assert state.mapping == empty_mapping()
        assert state.inputs == []
        assert state.outputs == []
        assert state.event_types == []
        assert state.events == []

    def test_dirty_after_modification(self):
        state = EditorState()
        assert not state.dirty

        state.add_input("input1")
        assert state.dirty

    def test_not_dirty_after_same_modification(self):
        state = EditorState()
        state.add_input("input1")
        state._original = Mapping.from_dict(state.mapping.to_dict())

        assert not state.dirty

        state.add_input("input2")
        assert state.dirty

        state.delete_input("input2")
        assert not state.dirty

    def test_add_input(self):
        state = EditorState()
        assert state.add_input("input1") is True
        assert state.inputs == ["input1"]

        # Duplicate should fail
        assert state.add_input("input1") is False
        assert state.inputs == ["input1"]

    def test_update_input(self):
        state = EditorState()
        state.add_input("old_name")

        assert state.update_input("old_name", "new_name") is True
        assert state.inputs == ["new_name"]

        # Non-existent should fail
        assert state.update_input("nonexistent", "foo") is False

    def test_delete_input(self):
        state = EditorState()
        state.add_input("input1")
        state.add_input("input2")

        assert state.delete_input("input1") is True
        assert state.inputs == ["input2"]

        # Non-existent should fail
        assert state.delete_input("nonexistent") is False

    def test_add_output(self):
        state = EditorState()
        assert state.add_output("output1") is True
        assert state.outputs == ["output1"]

    def test_add_event_type(self):
        state = EditorState()
        assert state.add_event_type("light") is True
        assert state.event_types == ["light"]

    def test_update_event_type_cascades(self):
        state = EditorState()
        state.add_event_type("old_type")

        event = MidiEvent(
            name="test_event",
            type="old_type",
            chord=MidiChord(port="port1", notes=[60]),
        )
        state.add_event(event)

        state.update_event_type("old_type", "new_type")

        assert state.event_types == ["new_type"]
        assert state.events[0].type == "new_type"

    def test_delete_event_type_cascades(self):
        state = EditorState()
        state.add_event_type("light")
        state.add_event_type("music")

        event1 = MidiEvent(name="e1", type="light", chord=MidiChord(port="p", notes=[60]))
        event2 = MidiEvent(name="e2", type="music", chord=MidiChord(port="p", notes=[61]))
        event3 = MidiEvent(name="e3", type="light", chord=MidiChord(port="p", notes=[62]))

        state.add_event(event1)
        state.add_event(event2)
        state.add_event(event3)

        deleted = state.delete_event_type("light")

        assert deleted == 2
        assert len(state.events) == 1
        assert state.events[0].name == "e2"

    def test_add_event(self):
        state = EditorState()
        event = MidiEvent(
            name="test_event",
            type="light",
            chord=MidiChord(port="port1", notes=[60, 64, 67]),
        )

        assert state.add_event(event) is True
        assert len(state.events) == 1
        assert state.events[0].name == "test_event"

        # Duplicate name should fail
        assert state.add_event(event) is False

    def test_get_event(self):
        state = EditorState()
        event = MidiEvent(name="test", type="light", chord=MidiChord(port="p", notes=[60]))
        state.add_event(event)

        found = state.get_event("test")
        assert found is not None
        assert found.name == "test"

        assert state.get_event("nonexistent") is None

    def test_get_events_by_type(self):
        state = EditorState()
        e1 = MidiEvent(name="e1", type="light", chord=MidiChord(port="p", notes=[60]))
        e2 = MidiEvent(name="e2", type="music", chord=MidiChord(port="p", notes=[61]))
        e3 = MidiEvent(name="e3", type="light", chord=MidiChord(port="p", notes=[62]))

        state.add_event(e1)
        state.add_event(e2)
        state.add_event(e3)

        light_events = state.get_events_by_type("light")
        assert len(light_events) == 2

    def test_update_event(self):
        state = EditorState()
        event = MidiEvent(name="test", type="light", chord=MidiChord(port="p", notes=[60]))
        state.add_event(event)

        updated = MidiEvent(name="test_renamed", type="music", chord=MidiChord(port="p2", notes=[61]))
        assert state.update_event("test", updated) is True

        assert len(state.events) == 1
        assert state.events[0].name == "test_renamed"
        assert state.events[0].type == "music"

    def test_delete_event(self):
        state = EditorState()
        event = MidiEvent(name="test", type="light", chord=MidiChord(port="p", notes=[60]))
        state.add_event(event)

        assert state.delete_event("test") is True
        assert len(state.events) == 0

        assert state.delete_event("nonexistent") is False

    def test_to_yaml(self):
        state = EditorState()
        state.add_input("input1")

        yaml_str = state.to_yaml()
        assert "inputs:" in yaml_str
        assert "input1" in yaml_str

    def test_compute_diff(self):
        state = EditorState()
        state.add_input("input1")
        state._original = Mapping.from_dict(state.mapping.to_dict())

        state.add_input("input2")
        state.delete_input("input1")

        diff = state.compute_diff()

        assert "input2" in diff["inputs"]["added"]
        assert "input1" in diff["inputs"]["removed"]

    def test_has_changes(self):
        state = EditorState()
        assert not state.has_changes()

        state.add_input("input1")
        assert state.has_changes()

    def test_save_to_runtime(self):
        state = EditorState()
        state.add_input("input1")

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_path = Path(tmpdir) / "mapping.yaml"

            with patch(
                "midi_event_handler.core.editor.state.RUNTIME_MAPPING_PATH",
                runtime_path,
            ):
                result = state.save_to_runtime()

                assert result is True
                assert runtime_path.exists()
                assert "input1" in runtime_path.read_text()
                assert not state.dirty

    def test_load_from_runtime(self):
        state = EditorState()

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_path = Path(tmpdir) / "mapping.yaml"
            runtime_path.write_text("inputs:\n  - testinput\noutputs: []\nevent_types: []\nevents: []\n")

            with patch(
                "midi_event_handler.core.editor.state.RUNTIME_MAPPING_PATH",
                runtime_path,
            ):
                result = state.load_from_runtime()

                assert result is True
                assert state.inputs == ["testinput"]
                assert not state.dirty

    def test_load_from_runtime_missing_file(self):
        state = EditorState()

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_path = Path(tmpdir) / "nonexistent.yaml"

            with patch(
                "midi_event_handler.core.editor.state.RUNTIME_MAPPING_PATH",
                runtime_path,
            ):
                result = state.load_from_runtime()

                assert result is False
                assert state.inputs == []


class TestRenameDuplicates:
    """Tests for EditorState.rename_duplicates()."""

    def test_no_duplicates(self):
        """Should return 0 when no duplicates exist."""
        state = EditorState()
        state.add_event(MidiEvent(name="a", type="t", chord=MidiChord(port="p", notes=[60])))
        state.add_event(MidiEvent(name="b", type="t", chord=MidiChord(port="p", notes=[61])))

        assert state.rename_duplicates() == 0
        assert [e.name for e in state.events] == ["a", "b"]

    def test_rename_two_duplicates(self):
        """Second occurrence should get ~1 suffix."""
        state = EditorState()
        state.mapping.events = [
            MidiEvent(name="foo", type="t", chord=MidiChord(port="p", notes=[60])),
            MidiEvent(name="foo", type="t", chord=MidiChord(port="p", notes=[61])),
        ]

        renamed = state.rename_duplicates()

        assert renamed == 1
        assert [e.name for e in state.events] == ["foo", "foo~1"]

    def test_rename_three_duplicates(self):
        """Third occurrence should get ~2 suffix."""
        state = EditorState()
        state.mapping.events = [
            MidiEvent(name="bar", type="t", chord=MidiChord(port="p", notes=[60])),
            MidiEvent(name="bar", type="t", chord=MidiChord(port="p", notes=[61])),
            MidiEvent(name="bar", type="t", chord=MidiChord(port="p", notes=[62])),
        ]

        renamed = state.rename_duplicates()

        assert renamed == 2
        assert [e.name for e in state.events] == ["bar", "bar~1", "bar~2"]

    def test_rename_mixed(self):
        """Only duplicate names should be renamed."""
        state = EditorState()
        state.mapping.events = [
            MidiEvent(name="a", type="t", chord=MidiChord(port="p", notes=[60])),
            MidiEvent(name="b", type="t", chord=MidiChord(port="p", notes=[61])),
            MidiEvent(name="a", type="t", chord=MidiChord(port="p", notes=[62])),
            MidiEvent(name="c", type="t", chord=MidiChord(port="p", notes=[63])),
            MidiEvent(name="b", type="t", chord=MidiChord(port="p", notes=[64])),
        ]

        renamed = state.rename_duplicates()

        assert renamed == 2
        assert [e.name for e in state.events] == ["a", "b", "a~1", "c", "b~1"]


class TestMapping:
    """Tests for Mapping dataclass."""

    def test_from_dict(self):
        data = {
            "inputs": ["in1"],
            "outputs": ["out1"],
            "event_types": ["light"],
            "events": [
                {
                    "name": "test",
                    "type": "light",
                    "trigger": {"port": "in1", "notes": [60, 64]},
                }
            ],
        }

        mapping = Mapping.from_dict(data)

        assert mapping.inputs == ["in1"]
        assert mapping.outputs == ["out1"]
        assert mapping.event_types == ["light"]
        assert len(mapping.events) == 1
        assert mapping.events[0].name == "test"
        assert mapping.events[0].chord.port == "in1"
        assert mapping.events[0].chord.notes == [60, 64]

    def test_to_dict(self):
        mapping = Mapping(
            inputs=["in1"],
            outputs=["out1"],
            event_types=["light"],
            events=[
                MidiEvent(
                    name="test",
                    type="light",
                    chord=MidiChord(port="in1", notes=[60, 64]),
                )
            ],
        )

        data = mapping.to_dict()

        assert data["inputs"] == ["in1"]
        assert data["events"][0]["name"] == "test"
        assert data["events"][0]["trigger"]["port"] == "in1"
        assert data["events"][0]["trigger"]["notes"] == [60, 64]

    def test_duplicate_event_names_none(self):
        """Should return empty list when no duplicates."""
        mapping = Mapping(
            events=[
                MidiEvent(name="a", type="t", chord=MidiChord(port="p", notes=[60])),
                MidiEvent(name="b", type="t", chord=MidiChord(port="p", notes=[61])),
            ]
        )
        assert mapping.duplicate_event_names() == []

    def test_duplicate_event_names_found(self):
        """Should return sorted list of duplicate names."""
        mapping = Mapping(
            events=[
                MidiEvent(name="z", type="t", chord=MidiChord(port="p", notes=[60])),
                MidiEvent(name="a", type="t", chord=MidiChord(port="p", notes=[61])),
                MidiEvent(name="z", type="t", chord=MidiChord(port="p", notes=[62])),
                MidiEvent(name="a", type="t", chord=MidiChord(port="p", notes=[63])),
            ]
        )
        assert mapping.duplicate_event_names() == ["a", "z"]

    def test_duplicate_event_names_empty(self):
        """Should return empty list for empty mapping."""
        mapping = Mapping()
        assert mapping.duplicate_event_names() == []

    def test_roundtrip(self):
        original = {
            "inputs": ["in1", "in2"],
            "outputs": ["out1"],
            "event_types": ["light", "music"],
            "events": [
                {
                    "name": "event1",
                    "type": "light",
                    "trigger": {"port": "in1", "notes": [60]},
                    "duration_min": 1,
                    "duration_max": 5,
                    "fallback_event": "event2",
                    "comment": "Test comment",
                }
            ],
        }

        mapping = Mapping.from_dict(original)
        result = mapping.to_dict()

        assert result["inputs"] == original["inputs"]
        assert result["outputs"] == original["outputs"]
        assert result["event_types"] == original["event_types"]
        assert result["events"][0]["name"] == original["events"][0]["name"]
        assert result["events"][0]["comment"] == "Test comment"
