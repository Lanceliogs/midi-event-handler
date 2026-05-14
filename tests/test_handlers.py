"""Tests for MIDI event handler queue / discard logic."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from midi_event_handler.core.events.handlers import MidiEventHandler
from midi_event_handler.core.events.models import MidiChord, MidiEvent


def _event(name: str, stored_priority: int | None = None) -> MidiEvent:
    return MidiEvent(
        name=name,
        type="light",
        chord=MidiChord(port="in1", notes=[60]),
        _priority=stored_priority,
    )


@pytest.fixture
def handler() -> MidiEventHandler:
    return MidiEventHandler(
        asyncio.Queue(),
        MagicMock(),
        MagicMock(),
    )


class TestShouldDiscardNextEvent:
    """Unit tests for MidiEventHandler._should_discard_next_event."""

    def test_never_discard_when_next_is_none(self, handler):
        handler.event = _event("current")
        handler.locked = True
        assert handler._should_discard_next_event(None) is False

    def test_never_discard_when_idle(self, handler):
        handler.event = None
        handler.locked = False
        assert handler._should_discard_next_event(_event("incoming")) is False

    def test_discard_when_next_equals_current_snapshot(self, handler):
        current = _event("same", stored_priority=None)
        incoming = _event("same", stored_priority=None)
        assert current is not incoming
        assert current == incoming

        handler.event = current
        handler.locked = True
        assert handler._should_discard_next_event(incoming) is True
        assert handler.locked is True

    def test_no_discard_when_unlocked_even_if_priorities_differ(self, handler):
        handler.event = _event("current", stored_priority=None)
        handler.locked = False
        incoming = _event("other", stored_priority=99)
        assert handler._should_discard_next_event(incoming) is False

    def test_discard_when_locked_and_next_priority_not_strictly_greater(self, handler):
        handler.event = _event("current", stored_priority=5)
        handler.locked = True
        same = _event("other", stored_priority=5)
        lower = _event("other2", stored_priority=3)

        assert handler._should_discard_next_event(same) is True
        assert handler.locked is True

        assert handler._should_discard_next_event(lower) is True
        assert handler.locked is True

    def test_preempt_when_locked_and_next_priority_strictly_greater(self, handler):
        handler.event = _event("current", stored_priority=1)
        handler.locked = True
        incoming = _event("incoming", stored_priority=2)

        assert handler._should_discard_next_event(incoming) is False
        assert handler.locked is False

    def test_effective_priority_zero_when_unset_on_both_under_lock(self, handler):
        """Unset _priority behaves as 0; equal effective priority → discard while locked."""
        handler.event = _event("current", stored_priority=None)
        handler.locked = True
        incoming = _event("other", stored_priority=None)
        assert incoming.priority == handler.event.priority == 0

        assert handler._should_discard_next_event(incoming) is True
        assert handler.locked is True

    def test_logs_duplicate_discard_reason(self, handler, caplog):
        caplog.set_level("INFO")

        handler.event = _event("a")
        duplicate = _event("a")

        handler.locked = True
        handler._should_discard_next_event(duplicate)

        assert any("CURRENT == NEXT" in r.message for r in caplog.records)

    def test_logs_low_priority_discard_under_lock(self, handler, caplog):
        caplog.set_level("INFO")

        handler.event = _event("current", stored_priority=5)
        handler.locked = True
        low = _event("low", stored_priority=3)

        handler._should_discard_next_event(low)

        assert any("Locked and low priority" in r.message for r in caplog.records)
