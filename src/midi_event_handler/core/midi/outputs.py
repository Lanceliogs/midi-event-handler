import mido
from typing import Dict, Optional, List

from midi_event_handler.core.events.models import MidiMessage
from midi_event_handler.core.exceptions import (
    port_not_found,
    port_busy,
    port_open_failed,
)
from midi_event_handler.tools.connection import broadcast_error

import logging

log = logging.getLogger(__name__)


class MidiOutputManager:
    """
    Manages MIDI output ports for sending messages.

    Usage:
        manager = MidiOutputManager()
        manager.register("PortName")  # Raises MidiAppError on failure
        manager.send(message)
        manager.close_all()
    """

    def __init__(self, names: Optional[List[str]] = None):
        self._outputs: Dict[str, mido.ports.BaseOutput] = {}
        if names:
            for name in names:
                self.register(name)

    def register_all(self) -> None:
        """Register all available output ports."""
        for name in mido.get_output_names():
            self.register(name)

    def register(self, name: str) -> None:
        """
        Register and open an output port.

        Args:
            name: Friendly port name (will be matched against available ports)

        Raises:
            MidiAppError: If port not found or cannot be opened.
        """
        if name in self._outputs:
            return  # Already registered

        available_outputs = mido.get_output_names()
        real_name = ""

        # Find matching port name
        for output in available_outputs:
            if name in output:
                real_name = output
                break

        if not real_name:
            raise port_not_found(
                port=name,
                port_type="output",
                available=available_outputs,
            )

        try:
            self._outputs[name] = mido.open_output(real_name)
            log.info(f"[Register] '{name}' -> '{real_name}'")
        except OSError as e:
            error_str = str(e).lower()
            if "busy" in error_str or "use" in error_str:
                raise port_busy(port=name, port_type="output")
            raise port_open_failed(port=name, port_type="output", error=str(e))
        except Exception as e:
            raise port_open_failed(port=name, port_type="output", error=str(e))

    def get(self, name: str) -> Optional[mido.ports.BaseOutput]:
        return self._outputs.get(name)

    def get_real_name(self, name: str) -> Optional[str]:
        port = self.get(name)
        if port:
            return port.name
        return None

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
            except Exception as e:
                log.exception("[SendMultiple] Exception while sending message!")
                broadcast_error(short=f"MIDI send failed: {msg.port}", exc=e)

    def close_all(self):
        for port in self._outputs.values():
            port.close()
        self._outputs.clear()

    def get_open_ports(self) -> List[str]:
        return list(self._outputs.keys())
