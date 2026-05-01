"""Tests for MIDI note conversion utilities."""

import pytest
from midi_event_handler.core.midi.notes import (
    note_to_name,
    name_to_note,
    parse_notes_input,
)


class TestNoteToName:
    """Tests for note_to_name function."""

    def test_middle_c(self):
        assert note_to_name(60) == "C4"

    def test_c0(self):
        assert note_to_name(12) == "C0"

    def test_a4_concert_pitch(self):
        assert note_to_name(69) == "A4"

    def test_sharps(self):
        assert note_to_name(61) == "C#4"
        assert note_to_name(63) == "D#4"
        assert note_to_name(66) == "F#4"
        assert note_to_name(68) == "G#4"
        assert note_to_name(70) == "A#4"

    def test_low_notes(self):
        assert note_to_name(0) == "C-1"
        assert note_to_name(21) == "A0"  # Lowest piano key

    def test_high_notes(self):
        assert note_to_name(127) == "G9"
        assert note_to_name(108) == "C8"  # Highest piano key

    def test_custom_middle_c(self):
        # Yamaha style: C3 = 60
        assert note_to_name(60, middle_c=48) == "C5"
        assert note_to_name(48, middle_c=48) == "C4"


class TestNameToNote:
    """Tests for name_to_note function."""

    def test_middle_c(self):
        assert name_to_note("C4") == 60

    def test_lowercase(self):
        assert name_to_note("c4") == 60
        assert name_to_note("a#4") == 70

    def test_sharps(self):
        assert name_to_note("C#4") == 61
        assert name_to_note("D#4") == 63
        assert name_to_note("F#4") == 66
        assert name_to_note("G#4") == 68
        assert name_to_note("A#4") == 70

    def test_flats(self):
        assert name_to_note("Db4") == 61  # Same as C#4
        assert name_to_note("Eb4") == 63  # Same as D#4
        assert name_to_note("Gb4") == 66  # Same as F#4
        assert name_to_note("Ab4") == 68  # Same as G#4
        assert name_to_note("Bb4") == 70  # Same as A#4

    def test_cb_special_case(self):
        # Cb4 = B3
        assert name_to_note("Cb4") == 59

    def test_fb_special_case(self):
        # Fb4 = E4
        assert name_to_note("Fb4") == 64

    def test_negative_octave(self):
        assert name_to_note("C-1") == 0

    def test_high_octave(self):
        assert name_to_note("G9") == 127

    def test_roundtrip(self):
        """note_to_name(name_to_note(x)) should return x for natural/sharp notes."""
        for note in [60, 61, 63, 66, 68, 70, 72, 48, 84]:
            name = note_to_name(note)
            assert name_to_note(name) == note

    def test_invalid_note(self):
        with pytest.raises(ValueError):
            name_to_note("X4")
        with pytest.raises(ValueError):
            name_to_note("C")
        with pytest.raises(ValueError):
            name_to_note("4")
        with pytest.raises(ValueError):
            name_to_note("")

    def test_custom_middle_c(self):
        # Yamaha style: C3 = 60
        assert name_to_note("C4", middle_c=48) == 48
        assert name_to_note("C5", middle_c=48) == 60


class TestParseNotesInput:
    """Tests for parse_notes_input function."""

    def test_numbers_comma_separated(self):
        assert parse_notes_input("60, 64, 67") == [60, 64, 67]

    def test_numbers_space_separated(self):
        assert parse_notes_input("60 64 67") == [60, 64, 67]

    def test_note_names(self):
        assert parse_notes_input("C4, E4, G4") == [60, 64, 67]

    def test_mixed(self):
        assert parse_notes_input("60, E4, 67") == [60, 64, 67]

    def test_sharps_and_flats(self):
        assert parse_notes_input("C#4, Db4") == [61, 61]

    def test_empty_string(self):
        assert parse_notes_input("") == []

    def test_whitespace_only(self):
        assert parse_notes_input("   ") == []

    def test_extra_whitespace(self):
        assert parse_notes_input("  60 ,  64  ,  67  ") == [60, 64, 67]

    def test_single_note(self):
        assert parse_notes_input("60") == [60]
        assert parse_notes_input("C4") == [60]

    def test_invalid_note_raises(self):
        with pytest.raises(ValueError):
            parse_notes_input("60, invalid, 67")
