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
        self._abort_event: asyncio.Event = asyncio.Event()
    
    async def record(self) -> Optional[List[int]]:
        """
        Record a chord from the MIDI port.
        
        Returns:
            List of note numbers if a chord was captured, None on timeout/abort.
            
        Raises:
            MidiAppError: If port cannot be opened.
        """
        if self._abort_event.is_set():
            return None
            
        self._queue = asyncio.Queue()
        self._listener = MidiListener(self.port_name, self._queue)
        
        try:
            # Open port (raises MidiAppError on failure)
            self._listener.open()
            log.info(f"[Recorder] Started recording on {self.port_name}")
            
            # Start listener task
            self._task = asyncio.create_task(self._listener.run())
            
            # Wait for chord, abort, or timeout
            queue_task = asyncio.create_task(self._queue.get())
            abort_task = asyncio.create_task(self._abort_event.wait())
            
            try:
                done, pending = await asyncio.wait(
                    [queue_task, abort_task],
                    timeout=self.timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Check what completed
                if abort_task in done:
                    log.info(f"[Recorder] Recording aborted")
                    return None
                elif queue_task in done:
                    chord = queue_task.result()
                    log.info(f"[Recorder] Captured chord: {chord.notes}")
                    return sorted(chord.notes)
                else:
                    # Timeout - nothing in done
                    log.info(f"[Recorder] Timeout after {self.timeout}s")
                    return None
                    
            except asyncio.CancelledError:
                log.info(f"[Recorder] Recording cancelled")
                return None
                
        finally:
            await self._cleanup()
    
    @property
    def was_aborted(self) -> bool:
        """Check if recording was aborted."""
        return self._abort_event.is_set()
    
    async def abort(self):
        """Abort the recording in progress."""
        if self._abort_event.is_set():
            return
        log.info(f"[Recorder] Aborting recording on {self.port_name}")
        self._abort_event.set()
    
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
