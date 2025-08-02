import mido
from typing import Dict, Optional, List

from midi_event_handler.core.events.models import MidiMessage
from midi_event_handler.tools import logtools

log = logtools.get_logger(__name__)

class MidiOutputManager:
    def __init__(self, names: Optional[List[str]] = None):
        self._outputs: Dict[str, mido.ports.BaseOutput] = {}
        if names:
            self.register_multiple(names)

    def register_all(self):
        for name in mido.get_output_names():
            self.register(name)

    def register_multiple(self, names: List[str]):
        for name in names:
            self.register(name)

    def register(self, name: str):
        available_outputs = mido.get_output_names()
        real_name = ""
        # Autocorrect name with look-alikes if possible 
        for output in available_outputs:
            if name in output:
                log.info(f"{name} -> {output}")
                real_name = output
                break
        if not real_name:
            log.warning(f"[Register] Can't register port as output: {name}")
        if name not in self._outputs:
            self._outputs[name] = mido.open_output(real_name)

    def get(self, name: str) -> Optional[mido.ports.BaseOutput]:
        return self._outputs.get(name)

    def send(self, message: MidiMessage):
        port = self.get(message.port)
        if port:
            port.send(message.to_mido())
        else:
            raise RuntimeError(f"MIDI output port '{message.port}' not registered")
        
    def send_multiple(self, messages: MidiMessage):
        log.info(f"[SendMultiple] Sending {len(messages)} message(s)")
        for msg in messages:
            try:
                self.send(msg)
            except:
                log.exception("[SendMultiple] Exception while sending message!")

    def close_all(self):
        for port in self._outputs.values():
            port.close()
        self._outputs.clear()

    def get_open_ports(self) -> List[str]:
        return list(self._outputs.keys())
    