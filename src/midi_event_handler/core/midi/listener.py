import asyncio
from collections import deque
from typing import Optional

import mido
from midi_event_handler.core.events.models import MidiMessage, MidiChord
from midi_event_handler.core.events.indexer import MidiEventIndex

import threading
import time

import logging
log = logging.getLogger(__name__)

class MidiListener:
    def __init__(self, port_name: str, chord_queue: asyncio.Queue):
        self.loop = asyncio.get_event_loop()
        self.chord_queue = chord_queue
        self.buffer: deque[MidiMessage] = deque()

        self.stop_event = threading.Event()

        self.friendly_port_name = port_name # For indexer usage
        self.port_name = "" # For real MIDI usage

        # Autocorrect with look-alikes
        available_ports: list[str] = mido.get_input_names()
        for name in available_ports:
            if port_name in name:
                self.port_name = name
                return
        log.warning(f"[Init] {port_name} does not look like a valid port.")
        log.info(f"[Init] Available input ports are: {', '.join(available_ports)}")

    async def run(self):
        def loop():
            if not self.port_name:
                log.warning("[Run] Invalid port, can't start listener")
                return
            
            log.info("[Run] Starting loop for %s", self.friendly_port_name)
            try:
                with mido.open_input(self.port_name) as port:
                    log.info("[Run] MIDI port open: %s", self.port_name)
                    while not self.stop_event.is_set():
                        for msg in port.iter_pending():
                            log.info(f"[Listener] New message: {self.port_name} / {msg}")
                            if msg.type == "note_on" and msg.velocity > 0:
                                self.buffer.append(MidiMessage.from_mido(msg, self.port_name))
                            elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                                if not self.buffer:
                                    continue
                                chord = MidiChord(
                                    notes=[msg.note for msg in self.buffer],
                                    port=self.friendly_port_name
                                )
                                self.buffer.clear()
                                self.loop.call_soon_threadsafe(
                                    self.chord_queue.put_nowait, chord
                                )
                        time.sleep(0.001)  # prevent tight CPU loop
            except Exception:
                log.exception(f"[Run] Exception caught during loop: {self.friendly_port_name}")
            finally:
                self.stop_event.clear()
                log.info(f"[Run] Listener stopped: {self.friendly_port_name}")
        
        await asyncio.to_thread(loop)

    def stop(self):
        log.info("[Stop] Requesting stop for %s", self.friendly_port_name)
        self.stop_event.set()
