"""
MIDI note conversion utilities.
"""

import re
from typing import List, Tuple

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_to_name(note: int, middle_c: int = 60) -> str:
    """
    Convert MIDI note number to name (e.g., 60 -> 'C4').

    Args:
        note: MIDI note number (0-127)
        middle_c: Which MIDI note is middle C (default 60 = C4)
    """
    octave_offset = (middle_c - 60) // 12
    octave = (note // 12) - 1 - octave_offset
    return f"{NOTE_NAMES[note % 12]}{octave}"


FLAT_TO_SHARP = {
    "CB": "B",
    "DB": "C#",
    "EB": "D#",
    "FB": "E",
    "GB": "F#",
    "AB": "G#",
    "BB": "A#",
}


def name_to_note(name: str, middle_c: int = 60) -> int:
    """
    Convert note name to MIDI number (e.g., 'C4' -> 60).

    Args:
        name: Note name like 'C4', 'F#3', 'Bb2', 'Db4'
        middle_c: Which MIDI note is middle C (default 60 = C4)
    """
    name = name.strip().upper().replace("♯", "#").replace("♭", "B")

    # Match note with optional sharp/flat and octave
    match = re.match(r"^([A-G][#B]?)(-?\d+)$", name)
    if not match:
        raise ValueError(f"Invalid note name: {name}")

    note_name, octave_str = match.groups()
    octave = int(octave_str)

    # Convert flats to sharps
    if note_name.endswith("B") and len(note_name) == 2:
        note_name = FLAT_TO_SHARP.get(note_name, note_name)
        # Cb -> B means we need to go down an octave
        if note_name == "B" and match.group(1) == "CB":
            octave -= 1

    octave_offset = (middle_c - 60) // 12
    base = NOTE_NAMES.index(note_name)
    return base + (octave + 1 + octave_offset) * 12


def format_note_badge(note: int, middle_c: int = 60) -> Tuple[int, str]:
    """
    Format a note for badge display.
    Returns (note_number, note_name).
    """
    return (note, note_to_name(note, middle_c))


def format_notes_badges(notes: List[int], middle_c: int = 60) -> List[Tuple[int, str]]:
    """
    Format multiple notes for badge display.
    """
    return [format_note_badge(n, middle_c) for n in notes]


def parse_notes_input(text: str, middle_c: int = 60) -> List[int]:
    """
    Parse user input that can contain note numbers or names.
    Accepts comma or space separated values.

    Examples:
        "60, 64, 67" -> [60, 64, 67]
        "C4, E4, G4" -> [60, 64, 67]
        "60 C#4 67" -> [60, 61, 67]
    """
    parts = re.split(r"[,\s]+", text.strip())
    notes = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
            notes.append(int(part))
        else:
            try:
                notes.append(name_to_note(part, middle_c))
            except ValueError:
                raise ValueError(f"Invalid note: {part}")

    return notes
