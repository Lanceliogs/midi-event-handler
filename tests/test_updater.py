"""Tests for updater filename pattern."""

import pytest
from midi_event_handler.tools.updater import FILENAME_PATTERN


@pytest.mark.parametrize(
    "filename",
    [
        "meh-0.5.1-setup.exe",
        "meh-v0.5.1-setup.exe",
        "meh-0.5.1.40f8b6b-setup.exe",
        "meh-v0.5.1.40f8b6b-setup.exe",
        "meh-0.5.1.40f8b6b.dirty-setup.exe",
        "meh-v0.5.1.40f8b6b.dirty-setup.exe",
        "meh-1.0.0-setup.exe",
        "meh-v1.0.0-setup.exe",
        "midi-event-handler-setup_0.5.0.exe",
        "midi-event-handler-setup_v0.5.0.exe",
        "midi-event-handler-setup_1.2.3-beta.exe",
        "midi-event-handler-setup_v1.2.3-beta.exe",
    ],
)
def test_filename_pattern_matches(filename):
    assert FILENAME_PATTERN.fullmatch(filename)


@pytest.mark.parametrize(
    "filename",
    [
        "meh-setup.exe",
        "other-app-0.5.1-setup.exe",
        "meh-0.5.1-setup.msi",
        "meh-0.5.1.exe",
        "readme.txt",
    ],
)
def test_filename_pattern_rejects(filename):
    assert not FILENAME_PATTERN.fullmatch(filename)
