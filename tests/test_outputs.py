"""Tests for MidiOutputManager class."""

import pytest
from unittest.mock import patch, MagicMock

from midi_event_handler.core.midi.outputs import MidiOutputManager
from midi_event_handler.core.exceptions import MidiAppError, ErrorCode


class TestMidiOutputManagerRegister:
    """Tests for MidiOutputManager.register() method."""

    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_register_port_not_found(self, mock_get_outputs):
        """Should raise MidiAppError when port not found."""
        mock_get_outputs.return_value = ["Other Port"]
        manager = MidiOutputManager()

        with pytest.raises(MidiAppError) as exc_info:
            manager.register("Lights")

        assert exc_info.value.code == ErrorCode.PORT_NOT_FOUND
        assert "Lights" in exc_info.value.short_message
        assert "output" in exc_info.value.context["port_type"]

    @patch("midi_event_handler.core.midi.outputs.mido.open_output")
    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_register_success(self, mock_get_outputs, mock_open):
        """Should register port successfully."""
        mock_get_outputs.return_value = ["Lights MIDI 1:0"]
        mock_port = MagicMock()
        mock_open.return_value = mock_port

        manager = MidiOutputManager()
        manager.register("Lights")

        assert "Lights" in manager._outputs
        mock_open.assert_called_once_with("Lights MIDI 1:0")

    @patch("midi_event_handler.core.midi.outputs.mido.open_output")
    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_register_already_registered(self, mock_get_outputs, mock_open):
        """Should not re-register if already registered."""
        mock_get_outputs.return_value = ["Lights MIDI 1:0"]
        mock_port = MagicMock()
        mock_open.return_value = mock_port

        manager = MidiOutputManager()
        manager.register("Lights")
        manager.register("Lights")  # Second call should be no-op

        mock_open.assert_called_once()

    @patch("midi_event_handler.core.midi.outputs.mido.open_output")
    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_register_port_busy(self, mock_get_outputs, mock_open):
        """Should raise PORT_BUSY error when port is in use."""
        mock_get_outputs.return_value = ["Lights MIDI 1:0"]
        mock_open.side_effect = OSError("Port is busy")

        manager = MidiOutputManager()

        with pytest.raises(MidiAppError) as exc_info:
            manager.register("Lights")

        assert exc_info.value.code == ErrorCode.PORT_BUSY

    @patch("midi_event_handler.core.midi.outputs.mido.open_output")
    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_register_generic_error(self, mock_get_outputs, mock_open):
        """Should raise PORT_OPEN_FAILED on generic errors."""
        mock_get_outputs.return_value = ["Lights MIDI 1:0"]
        mock_open.side_effect = Exception("Unknown error")

        manager = MidiOutputManager()

        with pytest.raises(MidiAppError) as exc_info:
            manager.register("Lights")

        assert exc_info.value.code == ErrorCode.PORT_OPEN_FAILED


class TestMidiOutputManagerOperations:
    """Tests for MidiOutputManager other methods."""

    @patch("midi_event_handler.core.midi.outputs.mido.open_output")
    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_get_registered_port(self, mock_get_outputs, mock_open):
        """Should return registered port."""
        mock_get_outputs.return_value = ["Lights MIDI 1:0"]
        mock_port = MagicMock()
        mock_open.return_value = mock_port

        manager = MidiOutputManager()
        manager.register("Lights")

        assert manager.get("Lights") is mock_port

    def test_get_unregistered_port(self):
        """Should return None for unregistered port."""
        manager = MidiOutputManager()

        assert manager.get("Unknown") is None

    @patch("midi_event_handler.core.midi.outputs.mido.open_output")
    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_close_all(self, mock_get_outputs, mock_open):
        """Should close all registered ports."""
        mock_get_outputs.return_value = ["Lights MIDI 1:0", "Synth MIDI 2:0"]
        mock_port1 = MagicMock()
        mock_port2 = MagicMock()
        mock_open.side_effect = [mock_port1, mock_port2]

        manager = MidiOutputManager()
        manager.register("Lights")
        manager.register("Synth")
        manager.close_all()

        mock_port1.close.assert_called_once()
        mock_port2.close.assert_called_once()
        assert len(manager._outputs) == 0

    @patch("midi_event_handler.core.midi.outputs.mido.open_output")
    @patch("midi_event_handler.core.midi.outputs.mido.get_output_names")
    def test_get_open_ports(self, mock_get_outputs, mock_open):
        """Should return list of registered port names."""
        mock_get_outputs.return_value = ["Lights MIDI 1:0", "Synth MIDI 2:0"]
        mock_open.return_value = MagicMock()

        manager = MidiOutputManager()
        manager.register("Lights")
        manager.register("Synth")

        ports = manager.get_open_ports()

        assert "Lights" in ports
        assert "Synth" in ports
