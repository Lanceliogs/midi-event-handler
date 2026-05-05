import asyncio
from collections import deque
from typing import Optional

import mido
from midi_event_handler.core.events.models import MidiMessage, MidiChord
from midi_event_handler.core.exceptions import (
    port_not_found,
    port_open_failed,
)
from midi_event_handler.core.midi.utils import resolve_port
from midi_event_handler.tools.connection import broadcast_error

import threading
import time

import logging

log = logging.getLogger(__name__)


class MidiListener:
    """
    Listens for MIDI messages on an input port and queues chords for processing.

    Lifecycle:
        listener = MidiListener("PortName", queue)
        listener.open()      # Raises MidiAppError if port unavailable
        task = asyncio.create_task(listener.run())
        # ... later ...
        listener.stop()      # Signal loop to exit
        await task           # Wait for loop to finish
        listener.close()     # Close the port
    """

    def __init__(self, port_name: str, chord_queue: asyncio.Queue):
        self.chord_queue = chord_queue
        self.buffer: deque[MidiMessage] = deque()
        self.stop_event = threading.Event()

        self.friendly_port_name = port_name  # For display/indexer usage
        self.port_name = ""  # Resolved real MIDI port name
        self._port: Optional[mido.ports.BaseInput] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None  # Set at run time

        self._resolve_port(port_name)

    def _resolve_port(self, port_name: str) -> None:
        """Resolve friendly name to actual MIDI port name."""
        resolved = resolve_port(port_name, mido.get_input_names())
        if resolved:
            self.port_name = resolved
            log.info(f"[Resolve] '{port_name}' -> '{resolved}'")
        else:
            log.warning(f"[Resolve] '{port_name}' not found in available ports")

    def open(self) -> None:
        """
        Open the MIDI port.

        Raises:
            MidiAppError: If port not found or cannot be opened.
        """
        if self._port is not None:
            return  # Already open

        if not self.port_name:
            available = mido.get_input_names()
            raise port_not_found(
                port=self.friendly_port_name,
                port_type="input",
                available=available,
            )

        try:
            self._port = mido.open_input(self.port_name)
            log.info(f"[Open] Port opened: {self.port_name}")
        except OSError as e:
            error_str = str(e).lower()
            if "busy" in error_str or "use" in error_str:
                from midi_event_handler.core.exceptions import port_busy

                raise port_busy(
                    port=self.friendly_port_name,
                    port_type="input",
                )
            raise port_open_failed(
                port=self.friendly_port_name,
                port_type="input",
                error=str(e),
            )
        except Exception as e:
            raise port_open_failed(
                port=self.friendly_port_name,
                port_type="input",
                error=str(e),
            )

    def close(self) -> None:
        """Close the MIDI port if open."""
        if self._port is not None:
            try:
                self._port.close()
                log.info(f"[Close] Port closed: {self.friendly_port_name}")
            except Exception:
                log.exception(f"[Close] Error closing port: {self.friendly_port_name}")
            finally:
                self._port = None

    async def run(self) -> None:
        """
        Run the listener loop. Port must be opened first via open().

        Raises:
            RuntimeError: If port not opened.
            MidiAppError: If an error occurs during listening.
        """
        if self._port is None:
            raise RuntimeError(f"Port not open: {self.friendly_port_name}. Call open() first.")

        # Capture the running loop for thread-safe callbacks
        self._loop = asyncio.get_running_loop()

        def loop():
            log.info(f"[Run] Starting loop for {self.friendly_port_name}")
            try:
                while not self.stop_event.is_set():
                    for msg in self._port.iter_pending():
                        log.debug(f"[Listener] {self.friendly_port_name}: {msg}")
                        if msg.type == "note_on" and msg.velocity > 0:
                            self.buffer.append(MidiMessage.from_mido(msg, self.port_name))
                        elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                            if not self.buffer:
                                continue
                            chord = MidiChord(
                                notes=[m.note for m in self.buffer],
                                port=self.friendly_port_name,
                            )
                            self.buffer.clear()
                            self._loop.call_soon_threadsafe(self.chord_queue.put_nowait, chord)
                    time.sleep(0.001)  # prevent tight CPU loop
            except Exception as e:
                log.exception(f"[Run] Exception in listener: {self.friendly_port_name}")
                broadcast_error(short=f"Listener error: {self.friendly_port_name}", exc=e)
                raise  # Re-raise so task monitor can catch it
            finally:
                self.stop_event.clear()
                log.info(f"[Run] Listener loop stopped: {self.friendly_port_name}")

        await asyncio.to_thread(loop)

    def stop(self) -> None:
        """Signal the listener loop to stop."""
        log.info(f"[Stop] Requesting stop for {self.friendly_port_name}")
        self.stop_event.set()
