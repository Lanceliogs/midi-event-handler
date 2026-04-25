"""Tests for config loader module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
import yaml

from midi_event_handler.core.events.models import MidiEvent, MidiChord, MidiMessage


class TestLoadMappingYaml:
    """Tests for mapping YAML loading."""
    
    def test_load_valid_mapping(self):
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
                        {"type": "note_on", "note": 100, "velocity": 127, "port": "output1"}
                    ],
                    "end_messages": [
                        {"type": "note_off", "note": 100, "velocity": 0, "port": "output1"}
                    ],
                    "duration_min": 5,
                    "duration_max": 30,
                    "fallback_event": "default"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(mapping, f)
            f.flush()
            
            loader.load_mapping_yaml(Path(f.name))
            
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
    
    def test_empty_mapping(self):
        from midi_event_handler.core.config import loader
        
        mapping = {
            "inputs": [],
            "outputs": [],
            "event_types": [],
            "events": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(mapping, f)
            f.flush()
            
            loader.load_mapping_yaml(Path(f.name))
            
            assert loader.get_configured_inputs() == []
            assert loader.get_configured_outputs() == []
            assert loader.get_event_types() == []
            assert loader.get_event_list() == []
    
    def test_event_with_minimal_fields(self):
        from midi_event_handler.core.config import loader
        
        mapping = {
            "inputs": ["input1"],
            "outputs": [],
            "event_types": ["light"],
            "events": [
                {
                    "name": "minimal_event",
                    "type": "light",
                    "trigger": {"port": "input1", "notes": [60]}
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(mapping, f)
            f.flush()
            
            loader.load_mapping_yaml(Path(f.name))
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
    
    def test_version_from_file(self):
        from midi_event_handler.core.config import loader
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("v1.2.3-test")
            f.flush()
            
            with patch.object(loader, 'VERSION_PATH', Path(f.name)):
                version = loader.get_current_version()
                assert version == "v1.2.3-test"
    
    def test_version_fallback(self):
        from midi_event_handler.core.config import loader
        
        with patch.object(loader, 'VERSION_PATH', Path("/nonexistent/version.txt")):
            # Should fall back to package metadata (without 'v' prefix) or default
            version = loader.get_current_version()
            # Package metadata returns version without 'v', e.g., "0.4.1"
            assert version and len(version) > 0
