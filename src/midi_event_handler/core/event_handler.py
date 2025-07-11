import asyncio
from typing import Optional

from midi_event_handler.core.event_models import MidiEvent
from midi_event_handler.core.event_indexer import MidiEventIndex

from midi_event_handler.tools import logtools 

log = logtools.get_logger(__name__)


class MidiEventHandler:

    def __init__(self):
        self.event_queue = asyncio.Queue()
        self.event: Optional[MidiEvent] = None
        self.locked: bool = False
        self._min_duration_task: Optional[asyncio.Task] = None
        self.fallback_scheduler_task: Optional[asyncio.Task] = None

    @property
    def queue(self) -> asyncio.Queue:
        """Access the event queue to push events. E.g. Listeners need this queue :)"""
        return self.event_queue

    async def _end_current_event(self):
        if not self.event:
            return
        self.event.send_end_messages()
        # Should NOT happen
        if self._min_duration_task and not self._min_duration_task.done():
            self._min_duration_task.cancel()
        # Will happen if the full duration is not expanded
        if self.fallback_scheduler_task and not self.fallback_scheduler_task.done():
            self.fallback_scheduler_task.cancel()

    async def _start_next_event(self):
        self.event.send_start_messages()
        if self.event.duration_min:
            self.locked = True
            self._min_duration_task = asyncio.create_task(self._unlock_after_min_duration())
            await asyncio.sleep(0.001)
        if self.event.duration_max:
            self.fallback_scheduler_task = asyncio.create_task(self._schedule_fallback_event())
            await asyncio.sleep(0.001)

    async def _unlock_after_min_duration(self):
        await asyncio.sleep(self.event.duration_min)
        self.locked = False

    async def _schedule_fallback_event(self):
        try:
            await asyncio.sleep(self.event.duration_max)
            fallback_event = MidiEventIndex.lookup_by_name(self.event.fallback_event)
            log.info(f"[FALLBACK] Sending fallback event: {fallback_event.name}")
            await self.event_queue.put(fallback_event)
        except asyncio.CancelledError:
            log.info(f"[CANCELLED] Fallback task was cancelled")

    async def start(self):
        while True:
            next_event: MidiEvent = await self.event_queue.get()
            if self.locked or not next_event:
                continue
            await self._end_current_event()
            self.event = next_event
            await self._start_next_event()

