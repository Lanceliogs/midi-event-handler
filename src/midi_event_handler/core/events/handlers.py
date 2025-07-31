import asyncio
from typing import Optional, Dict

from midi_event_handler.core.events.models import MidiEvent, MidiChord
from midi_event_handler.core.events.indexer import MidiEventIndex
from midi_event_handler.core.midi.outputs import MidiOutputManager

from midi_event_handler.tools import logtools
from midi_event_handler.tools.connection import ConnectionManager

log = logtools.get_logger(__name__)
def _log_event_state(flag: str, event: MidiEvent):
    log.debug(f"[{flag.upper()}] name={event.name} type={event.type}")

manager = ConnectionManager("meh-app")
async def notify_new_event():
    await manager.notify({"notify": "event"})

class MidiChordProcessor:
    def __init__(
            self, chord_queue: asyncio.Queue,
            event_queues: Dict[str, asyncio.Queue],
            event_index: MidiEventIndex
        ):
        self.chord_queue = chord_queue
        self.event_queues = event_queues
        self.event_index = event_index

    async def run(self):
        while True:
            chord: MidiChord = await self.chord_queue.get()
            event: MidiEvent = self.event_index.lookup_by_signature(chord.signature())
            if event:
                await self.event_queues[event.type].put(event)
            else:
                log.warning(f"No event found for chord: {chord}")


class MidiEventHandler:

    def __init__(self, event_queue: asyncio.Queue, event_index: MidiEventIndex, midiout: MidiOutputManager):
        self.event_queue = event_queue
        self.event_index = event_index
        self.midiout = midiout

        self.event: Optional[MidiEvent] = None
        self.locked: bool = False
        self._min_duration_task: Optional[asyncio.Task] = None
        self._fallback_scheduler_task: Optional[asyncio.Task] = None

    async def _end_current_event(self):
        _log_event_state("END", self.event)
        if not self.event:
            return
        self.midiout.send_multiple(self.event.end_messages)
        # Should NOT happen
        if self._min_duration_task and not self._min_duration_task.done():
            self._min_duration_task.cancel()
        # Will happen if the full duration is not expanded
        if self._fallback_scheduler_task and not self._fallback_scheduler_task.done():
            self._fallback_scheduler_task.cancel()

    async def _start_next_event(self):
        _log_event_state("START", self.event)
        self.midiout.send_multiple(self.event.start_messages)
        if self.event.duration_min:
            self.locked = True
            self._min_duration_task = asyncio.create_task(self._unlock_after_min_duration())
            await asyncio.sleep(0.001)
        if self.event.duration_max:
            self._fallback_scheduler_task = asyncio.create_task(self._schedule_fallback_event())
            await asyncio.sleep(0.001)

    async def _unlock_after_min_duration(self):
        await asyncio.sleep(self.event.duration_min)
        self.locked = False

    async def _schedule_fallback_event(self):
        try:
            await asyncio.sleep(self.event.duration_max)
            fallback_event = self.event_index.lookup_by_name(self.event.fallback_event)
            log.info(f"[FALLBACK] Sending fallback event: {fallback_event.name}")
            await self.event_queue.put(fallback_event)
        except asyncio.CancelledError:
            log.info(f"[CANCELLED] Fallback task was cancelled")

    async def _cleanup_tasks(self):
        if self._min_duration_task and not self._min_duration_task.done():
            self._min_duration_task.cancel()
        if self._fallback_scheduler_task and not self._fallback_scheduler_task.done():
            self._fallback_scheduler_task.cancel()
        await asyncio.gather(self._min_duration_task, self._fallback_scheduler_task, return_exceptions=True)

    async def run(self):
        log.debug(f"[STARTED] handler main task running")
        try:
            while True:
                next_event: MidiEvent = await self.event_queue.get()
                _log_event_state("NEXT", next_event)
                if self.locked or not next_event:
                    _log_event_state("DISCARDED", next_event)
                    continue
                await self._end_current_event()
                self.event = next_event
                await notify_new_event()
                await self._start_next_event()
        except asyncio.CancelledError:
            log.debug(f"[CANCELLED] Handler main task stopped")
        finally:
            await self._cleanup_tasks()

