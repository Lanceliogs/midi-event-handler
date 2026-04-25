"""
MIDI Recorder - captures a chord from an input port with timeout.

Usage:
    recorder = MidiRecorder("PortName", timeout=5.0)
    chord = await recorder.record()  # Returns list of notes or None on timeout
"""

import asyncio
from typing import Optional, List

from midi_event_handler.core.midi.listener import MidiListener
from midi_event_handler.core.exceptions import MidiAppError

import logging
log = logging.getLogger(__name__)


class MidiRecorder:
    """
    Records a single chord from a MIDI input port.
    
    Creates a temporary listener, waits for a chord, and returns it.
    Automatically cleans up resources.
    """
    
    def __init__(self, port_name: str, timeout: float = 5.0):
        self.port_name = port_name
        self.timeout = timeout
        self._listener: Optional[MidiListener] = None
        self._queue: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None
    
    async def record(self) -> Optional[List[int]]:
        """
        Record a chord from the MIDI port.
        
        Returns:
            List of note numbers if a chord was captured, None on timeout.
            
        Raises:
            MidiAppError: If port cannot be opened.
        """
        self._queue = asyncio.Queue()
        self._listener = MidiListener(self.port_name, self._queue)
        
        try:
            # Open port (raises MidiAppError on failure)
            self._listener.open()
            log.info(f"[Recorder] Started recording on {self.port_name}")
            
            # Start listener task
            self._task = asyncio.create_task(self._listener.run())
            
            # Wait for chord with timeout
            try:
                chord = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=self.timeout
                )
                log.info(f"[Recorder] Captured chord: {chord.notes}")
                return sorted(chord.notes)
            except asyncio.TimeoutError:
                log.info(f"[Recorder] Timeout after {self.timeout}s")
                return None
                
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """Stop listener and close port."""
        if self._listener:
            self._listener.stop()
            
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self._listener:
            self._listener.close()
            self._listener = None
        
        log.info(f"[Recorder] Cleanup complete for {self.port_name}")
