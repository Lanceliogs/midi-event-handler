"""Tests for MIDI utilities."""

import pytest
from unittest.mock import patch


class TestResolvePortsStatus:
    """Tests for port resolution logic."""
    
    def test_resolve_matching_port(self):
        from midi_event_handler.core.midi.utils import _resolve_ports_status
        
        configured = ["loopIN"]
        available = ["loopIN 0", "loopIN 1", "other 0"]
        
        result = _resolve_ports_status(configured, available)
        
        assert len(result) == 1
        assert result[0]["friendly_name"] == "loopIN"
        assert result[0]["real_name"] == "loopIN 0"  # First match
        assert result[0]["available"] is True
    
    def test_resolve_no_match(self):
        from midi_event_handler.core.midi.utils import _resolve_ports_status
        
        configured = ["nonexistent"]
        available = ["loopIN 0", "other 0"]
        
        result = _resolve_ports_status(configured, available)
        
        assert len(result) == 1
        assert result[0]["friendly_name"] == "nonexistent"
        assert result[0]["real_name"] == "Unavailable"
        assert result[0]["available"] is False
    
    def test_resolve_multiple_configured(self):
        from midi_event_handler.core.midi.utils import _resolve_ports_status
        
        configured = ["loopIN", "loopOUT"]
        available = ["loopIN 0", "loopOUT 0", "other 0"]
        
        result = _resolve_ports_status(configured, available)
        
        assert len(result) == 2
        assert result[0]["friendly_name"] == "loopIN"
        assert result[0]["available"] is True
        assert result[1]["friendly_name"] == "loopOUT"
        assert result[1]["available"] is True
    
    def test_resolve_partial_match(self):
        """Port name is substring of available port."""
        from midi_event_handler.core.midi.utils import _resolve_ports_status
        
        configured = ["MIDI"]
        available = ["USB MIDI Interface 0", "Other Device"]
        
        result = _resolve_ports_status(configured, available)
        
        assert result[0]["available"] is True
        assert "USB MIDI Interface" in result[0]["real_name"]
    
    def test_resolve_empty_configured(self):
        from midi_event_handler.core.midi.utils import _resolve_ports_status
        
        configured = []
        available = ["port1", "port2"]
        
        result = _resolve_ports_status(configured, available)
        assert result == []
    
    def test_resolve_empty_available(self):
        from midi_event_handler.core.midi.utils import _resolve_ports_status
        
        configured = ["port1"]
        available = []
        
        result = _resolve_ports_status(configured, available)
        
        assert len(result) == 1
        assert result[0]["available"] is False


class TestGetPortsStatus:
    """Tests for get_ports_status function."""
    
    def test_returns_all_fields(self):
        from midi_event_handler.core.midi import utils
        
        with patch.object(utils, 'get_configured_inputs', return_value=["input1"]):
            with patch.object(utils, 'get_configured_outputs', return_value=["output1"]):
                with patch('mido.get_input_names', return_value=["input1 0"]):
                    with patch('mido.get_output_names', return_value=["output1 0"]):
                        result = utils.get_ports_status()
        
        assert "inputs" in result
        assert "outputs" in result
        assert "available_inputs" in result
        assert "available_outputs" in result
    
    def test_inputs_resolved(self):
        from midi_event_handler.core.midi import utils
        
        with patch.object(utils, 'get_configured_inputs', return_value=["myInput"]):
            with patch.object(utils, 'get_configured_outputs', return_value=[]):
                with patch('mido.get_input_names', return_value=["myInput 0", "otherInput 0"]):
                    with patch('mido.get_output_names', return_value=[]):
                        result = utils.get_ports_status()
        
        assert len(result["inputs"]) == 1
        assert result["inputs"][0]["friendly_name"] == "myInput"
        assert result["inputs"][0]["available"] is True
        assert result["available_inputs"] == ["myInput 0", "otherInput 0"]
    
    def test_outputs_resolved(self):
        from midi_event_handler.core.midi import utils
        
        with patch.object(utils, 'get_configured_inputs', return_value=[]):
            with patch.object(utils, 'get_configured_outputs', return_value=["myOutput"]):
                with patch('mido.get_input_names', return_value=[]):
                    with patch('mido.get_output_names', return_value=["myOutput 0"]):
                        result = utils.get_ports_status()
        
        assert len(result["outputs"]) == 1
        assert result["outputs"][0]["friendly_name"] == "myOutput"
        assert result["outputs"][0]["available"] is True
