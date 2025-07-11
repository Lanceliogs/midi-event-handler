import asyncio
from collections import deque

import mido
from midi_event_handler.core.event_models import MidiMessage, MidiChord
from midi_event_handler.core.event_indexer import MidiEventIndex


class MIDIListener:
    def __init__(self, port_name: str, event_queue: asyncio.Queue):
        self.port_name = port_name
        self.event_queue = event_queue
        self.buffer: deque[MidiMessage] = deque()

    async def start(self):
        self.task = asyncio.create_task(self._listen())

    async def _listen(self):
        def loop():
            event_index: MidiEventIndex = MidiEventIndex.get()
            with mido.open_input(self.port_name) as port:
                for msg in port:
                    if msg.type == "note_on" and msg.velocity > 0:
                        self.buffer.append(MidiMessage.from_mido(msg, self.port_name))
                    elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                        if not self.buffer:
                            continue
                        chord = MidiChord(notes=[msg.note for msg in self.buffer])
                        self.buffer.clear()
                        event = event_index.lookup(self.port_name, chord)
                        if not event:
                            continue
                        asyncio.get_event_loop().call_soon_threadsafe(self.event_queue.put_nowait, event)      
        
        await asyncio.to_thread(loop)

