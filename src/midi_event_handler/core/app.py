import asyncio
from typing import List, Optional
from pathlib import Path

from midi_event_handler.core.config import *
from midi_event_handler.core.events.handlers import MidiEventHandler, MidiChordProcessor
from midi_event_handler.core.events.indexer import MidiEventIndex
from midi_event_handler.core.midi.listener import MidiListener
from midi_event_handler.core.midi.outputs import MidiOutputs


class MidiApp:
    def __init__(self, config_path: Path):
        self.running = False
        self._tasks: List[asyncio.Task] = []

        self.chord_queue = asyncio.Queue()
        self.event_queues = {t: asyncio.Queue() for t in get_event_types(config_path)}
        self.index = MidiEventIndex(get_event_list(config_path))
        self.outputs = MidiOutputs.from_config(config_path)

        self.listeners = [
            MidiListener(name, self.chord_queue)
            for name in get_configured_inputs(config_path)
        ]

        self.handlers = {
            t: MidiEventHandler(self.event_queues[t])
            for t in self.event_queues
        }

        self.chord_processor = MidiChordProcessor(
            chord_queue=self.chord_queue,
            event_queues=self.event_queues,
            event_index=self.index
        )

    async def start(self):
        if self.running:
            return
        self.running = True

        self._tasks = [
            asyncio.create_task(handler.start())
            for handler in self.handlers.values()
        ] + [
            asyncio.create_task(listener.run())
            for listener in self.listeners
        ] + [
            asyncio.create_task(self.chord_processor.run())
        ]

    async def stop(self):
        if not self.running:
            return
        self.running = False

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
