"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys

# Patch mido MIDI port discovery on Linux (CI has no ALSA).
# This must happen before any app module tries to enumerate ports at import time.
if sys.platform == "linux":
    patch("mido.get_input_names", return_value=[]).start()
    patch("mido.get_output_names", return_value=[]).start()

from midi_event_handler.core.events.models import MidiEvent, MidiChord, MidiMessage


@pytest.fixture
def sample_chord():
    """Create a sample MidiChord for testing."""
    return MidiChord(notes=[60, 64, 67], port="input1")


@pytest.fixture
def sample_message():
    """Create a sample MidiMessage for testing."""
    return MidiMessage(type="note_on", note=100, velocity=127, port="output1")


@pytest.fixture
def sample_event(sample_chord):
    """Create a sample MidiEvent for testing."""
    return MidiEvent(
        name="test_event",
        type="light",
        chord=sample_chord,
    )


@pytest.fixture
def full_event(sample_chord, sample_message):
    """Create a fully populated MidiEvent for testing."""
    end_message = MidiMessage(type="note_off", note=100, velocity=0, port="output1")
    return MidiEvent(
        name="full_event",
        type="music",
        chord=sample_chord,
        start_messages=[sample_message],
        end_messages=[end_message],
        duration_min=5,
        duration_max=30,
        fallback_event="fallback",
    )


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yield Path(f.name)
    # Cleanup happens automatically when test ends


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
