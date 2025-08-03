import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

from midi_event_handler.core.config import *
from midi_event_handler.core.events.models import MidiEvent, dump_event
from midi_event_handler.core.events.handlers import MidiEventHandler, MidiChordProcessor
from midi_event_handler.core.events.indexer import MidiEventIndex
from midi_event_handler.core.midi.listener import MidiListener
from midi_event_handler.core.midi.outputs import MidiOutputManager
from midi_event_handler.core.midi.utils import get_ports_status

from midi_event_handler.tools import logtools
log = logtools.get_logger(__name__)

from midi_event_handler.tools.connection import ConnectionManager
manager = ConnectionManager("meh-app")

async def notify_app_state():
    await manager.notify({"notify": "state"})

def notify_app_state_nowait():
    manager.notify_nowait({"notify": "state"})


class MidiApp:
    def __init__(self):
        self.running = False
        self._tasks: List[asyncio.Task] = []

        self._setup_from_mapping()

    def _setup_from_mapping(self):
        self.chord_queue = asyncio.Queue()
        self.event_queues = {t: asyncio.Queue() for t in get_event_types()}
        self.index = MidiEventIndex(get_event_list())
        self.outputs = MidiOutputManager()

        self.listeners = [
            MidiListener(name, self.chord_queue)
            for name in get_configured_inputs()
        ]

        self.handlers = {
            t: MidiEventHandler(self.event_queues[t], self.index, self.outputs)
            for t in self.event_queues
        }

        self.chord_processor = MidiChordProcessor(
            chord_queue=self.chord_queue,
            event_queues=self.event_queues,
            event_index=self.index
        )

        log.info(f"[Setup] Listeners: {', '.join(get_configured_inputs())}")
        log.info(f"[Setup] Events: {len(get_event_list())}")
        log.info(f"[Setup] Outputs: {', '.join(get_configured_outputs())}")


    def reload_mapping(self):
        if self.running:
            log.warning("[Reload-Mapping] Can't reload while the app is running!")
            return
        load_mapping_yaml()
        self._setup_from_mapping()

        notify_app_state_nowait()

    async def start(self):
        if self.running:
            log.info("[Start] Already running")
            return
        
        # Check if all ports are available
        port_status = get_ports_status()
        ports = port_status.get("inputs", []) + port_status.get("outputs", [])
        ready = all([p.get("available") for p in ports ])
        if not ready:
            log.warning("[Start] Some ports are not available")
            return

        self.running = True

        self.outputs.register_multiple(get_configured_outputs())

        self._tasks = [
            asyncio.create_task(handler.run())
            for handler in self.handlers.values()
        ] + [
            asyncio.create_task(listener.run())
            for listener in self.listeners
        ] + [
            asyncio.create_task(self.chord_processor.run())
        ]
        log.info("[Start] Tasks spawned!")

        await notify_app_state()

    async def stop(self):
        if not self.running:
            log.info("[Stop] Not running")
            return
        self.running = False

        log.info("[Stop] Shutting down the listerner threads...")
        [ l.stop() for l in self.listeners ]
        await asyncio.sleep(0.100)
        
        log.info("[Stop] Cancelling the tasks...")
        [ t.cancel() for t in self._tasks if not t.done() ]
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self.outputs.close_all()
        log.info("[Stop] Stopped!")

        await notify_app_state()

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "active_events": { t: dump_event(h.event) for t, h in self.handlers.items() },
            "midi_ports": get_ports_status(),
            "tasks": len(self._tasks)
        }