"""Tests for config loader module."""

import pytest
from pathlib import Path
from unittest.mock import patch
import yaml


class TestConfigLoaderFromMapping:
    """Tests for config loading from the test mapping file."""

    def test_configured_inputs(self):
        from midi_event_handler.core.config import loader

        loader.load_mapping_yaml(Path(__file__).parent / "test_mapping.yaml")
        assert "InputDevice2" in loader.get_configured_inputs()

    def test_event_types(self):
        from midi_event_handler.core.config import loader

        loader.load_mapping_yaml(Path(__file__).parent / "test_mapping.yaml")
        assert loader.get_event_types() == ["light", "music"]

    def test_events_loaded(self):
        from midi_event_handler.core.config import loader

        loader.load_mapping_yaml(Path(__file__).parent / "test_mapping.yaml")
        events = loader.get_event_list()
        assert len(events) == 3
        assert events[0].chord.notes == [127, 131]


class TestLoadMappingYaml:
    """Tests for mapping YAML loading."""

    def test_load_valid_mapping(self, temp_yaml_file):
        from midi_event_handler.core.config import loader

        mapping = {
            "inputs": ["input1", "input2"],
            "outputs": ["output1"],
            "event_types": ["light", "music"],
            "events": [
                {
                    "name": "test_event",
                    "type": "light",
                    "trigger": {"port": "input1", "notes": [60, 64]},
                    "start_messages": [
                        {
                            "type": "note_on",
                            "note": 100,
                            "velocity": 127,
                            "port": "output1",
                        }
                    ],
                    "end_messages": [
                        {
                            "type": "note_off",
                            "note": 100,
                            "velocity": 0,
                            "port": "output1",
                        }
                    ],
                    "duration_min": 5,
                    "duration_max": 30,
                    "fallback_event": "default",
                }
            ],
        }

        temp_yaml_file.write_text(yaml.dump(mapping))
        loader.load_mapping_yaml(temp_yaml_file)

        assert loader.get_configured_inputs() == ["input1", "input2"]
        assert loader.get_configured_outputs() == ["output1"]
        assert loader.get_event_types() == ["light", "music"]

        events = loader.get_event_list()
        assert len(events) == 1
        assert events[0].name == "test_event"
        assert events[0].type == "light"
        assert events[0].chord.notes == [60, 64]
        assert events[0].chord.port == "input1"
        assert events[0].duration_min == 5
        assert events[0].duration_max == 30
        assert events[0].fallback_event == "default"

    def test_load_missing_file(self):
        from midi_event_handler.core.config import loader

        with pytest.raises(FileNotFoundError):
            loader.load_mapping_yaml(Path("/nonexistent/path.yaml"))

    def test_empty_mapping(self, temp_yaml_file):
        from midi_event_handler.core.config import loader

        mapping = {"inputs": [], "outputs": [], "event_types": [], "events": []}

        temp_yaml_file.write_text(yaml.dump(mapping))
        loader.load_mapping_yaml(temp_yaml_file)

        assert loader.get_configured_inputs() == []
        assert loader.get_configured_outputs() == []
        assert loader.get_event_types() == []
        assert loader.get_event_list() == []

    def test_event_with_minimal_fields(self, temp_yaml_file):
        from midi_event_handler.core.config import loader

        mapping = {
            "inputs": ["input1"],
            "outputs": [],
            "event_types": ["light"],
            "events": [
                {
                    "name": "minimal_event",
                    "type": "light",
                    "trigger": {"port": "input1", "notes": [60]},
                }
            ],
        }

        temp_yaml_file.write_text(yaml.dump(mapping))
        loader.load_mapping_yaml(temp_yaml_file)
        events = loader.get_event_list()

        assert len(events) == 1
        assert events[0].name == "minimal_event"
        assert events[0].start_messages == []
        assert events[0].end_messages == []
        assert events[0].duration_min is None
        assert events[0].duration_max is None
        assert events[0].fallback_event is None


class TestGetCurrentVersion:
    """Tests for version retrieval."""

    def test_version_from_file(self, temp_yaml_file):
        from midi_event_handler.core.config import loader

        temp_yaml_file.write_text("v1.2.3-test")
        with patch.object(loader, "VERSION_PATH", temp_yaml_file):
            version = loader.get_current_version()
            assert version == "v1.2.3-test"

    def test_version_fallback(self):
        from midi_event_handler.core.config import loader

        with patch.object(loader, "VERSION_PATH", Path("/nonexistent/version.txt")):
            version = loader.get_current_version()
            assert version and len(version) > 0
