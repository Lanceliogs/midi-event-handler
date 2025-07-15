import asyncio
from collections import deque

import mido
from midi_event_handler.core.events.models import MidiMessage, MidiChord
from midi_event_handler.core.events.indexer import MidiEventIndex


class MidiListener:
    def __init__(self, port_name: str, chord_queue: asyncio.Queue):
        self.port_name = port_name
        self.chord_queue = chord_queue
        self.buffer: deque[MidiMessage] = deque()

    async def start(self):
        self.task = asyncio.create_task(self._listen())

    async def _listen(self):
        def loop():
            with mido.open_input(self.port_name) as port:
                for msg in port:
                    if msg.type == "note_on" and msg.velocity > 0:
                        self.buffer.append(MidiMessage.from_mido(msg, self.port_name))
                    elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                        if not self.buffer:
                            continue
                        chord = MidiChord(
                            notes=[msg.note for msg in self.buffer],
                            port=self.buffer[0].port
                        )
                        self.buffer.clear()
                        asyncio.get_event_loop().call_soon_threadsafe(self.chord_queue.put_nowait, chord)      
        
        await asyncio.to_thread(loop)

