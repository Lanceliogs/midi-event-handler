import mido
from typing import Dict, Optional

class MidiOutputs:
    _outputs: Dict[str, mido.ports.BaseOutput] = {}

    @staticmethod
    def register_all():
        """Opens and registers all available output ports by name."""
        for name in mido.get_output_names():
            if name not in MidiOutputs._outputs:
                MidiOutputs._outputs[name] = mido.open_output(name)

    @staticmethod
    def register(name: str):
        """Register a specific port by name."""
        if name not in MidiOutputs._outputs:
            MidiOutputs._outputs[name] = mido.open_output(name)

    @staticmethod
    def get(name: str) -> Optional[mido.ports.BaseOutput]:
        """Get an open MIDI output port by name."""
        return MidiOutputs._outputs.get(name)

    @staticmethod
    def send(name: str, message: mido.Message):
        """Send a MIDI message to the named output port."""
        port = MidiOutputs.get(name)
        if port is not None:
            port.send(message)
        else:
            raise RuntimeError(f"MIDI output port '{name}' not registered")

    @staticmethod
    def close_all():
        """Closes all open output ports."""
        for port in MidiOutputs._outputs.values():
            port.close()
        MidiOutputs._outputs.clear()
