"""Tests for MidiListener class."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from midi_event_handler.core.midi.listener import MidiListener
from midi_event_handler.core.exceptions import MidiAppError, ErrorCode


class TestMidiListenerInit:
    """Tests for MidiListener initialization."""

    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_resolve_port_found(self, mock_get_inputs):
        """Should resolve partial port name to full name."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0", "Drums MIDI 2:0"]
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)

        assert listener.friendly_port_name == "Piano"
        assert listener.port_name == "Piano MIDI 1:0"

    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_resolve_port_not_found(self, mock_get_inputs):
        """Should leave port_name empty if not found."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        queue = asyncio.Queue()

        listener = MidiListener("Keyboard", queue)

        assert listener.friendly_port_name == "Keyboard"
        assert listener.port_name == ""


class TestMidiListenerOpen:
    """Tests for MidiListener.open() method."""

    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_open_port_not_found(self, mock_get_inputs):
        """Should raise MidiAppError when port not found."""
        mock_get_inputs.return_value = ["Other Port"]
        queue = asyncio.Queue()
        listener = MidiListener("Piano", queue)

        with pytest.raises(MidiAppError) as exc_info:
            listener.open()

        assert exc_info.value.code == ErrorCode.PORT_NOT_FOUND
        assert "Piano" in exc_info.value.short_message

    @patch("midi_event_handler.core.midi.listener.mido.open_input")
    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_open_success(self, mock_get_inputs, mock_open):
        """Should open port successfully."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        mock_port = MagicMock()
        mock_open.return_value = mock_port
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)
        listener.open()

        assert listener._port is mock_port
        mock_open.assert_called_once_with("Piano MIDI 1:0")

    @patch("midi_event_handler.core.midi.listener.mido.open_input")
    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_open_already_open(self, mock_get_inputs, mock_open):
        """Should not reopen if already open."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        mock_port = MagicMock()
        mock_open.return_value = mock_port
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)
        listener.open()
        listener.open()  # Second call should be no-op

        mock_open.assert_called_once()

    @patch("midi_event_handler.core.midi.listener.mido.open_input")
    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_open_port_busy(self, mock_get_inputs, mock_open):
        """Should raise PORT_BUSY error when port is in use."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        mock_open.side_effect = OSError("Port is busy")
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)

        with pytest.raises(MidiAppError) as exc_info:
            listener.open()

        assert exc_info.value.code == ErrorCode.PORT_BUSY

    @patch("midi_event_handler.core.midi.listener.mido.open_input")
    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_open_generic_error(self, mock_get_inputs, mock_open):
        """Should raise PORT_OPEN_FAILED on generic errors."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        mock_open.side_effect = Exception("Unknown error")
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)

        with pytest.raises(MidiAppError) as exc_info:
            listener.open()

        assert exc_info.value.code == ErrorCode.PORT_OPEN_FAILED


class TestMidiListenerClose:
    """Tests for MidiListener.close() method."""

    @patch("midi_event_handler.core.midi.listener.mido.open_input")
    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_close_open_port(self, mock_get_inputs, mock_open):
        """Should close an open port."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        mock_port = MagicMock()
        mock_open.return_value = mock_port
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)
        listener.open()
        listener.close()

        mock_port.close.assert_called_once()
        assert listener._port is None

    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    def test_close_not_open(self, mock_get_inputs):
        """Should handle closing when port not open."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)
        listener.close()  # Should not raise

        assert listener._port is None


class TestMidiListenerRun:
    """Tests for MidiListener.run() method."""

    @pytest.mark.asyncio
    @patch("midi_event_handler.core.midi.listener.mido.get_input_names")
    async def test_run_without_open(self, mock_get_inputs):
        """Should raise RuntimeError if port not opened."""
        mock_get_inputs.return_value = ["Piano MIDI 1:0"]
        queue = asyncio.Queue()

        listener = MidiListener("Piano", queue)

        with pytest.raises(RuntimeError) as exc_info:
            await listener.run()

        assert "not open" in str(exc_info.value).lower()
