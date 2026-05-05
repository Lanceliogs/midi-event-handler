import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import logging

from midi_event_handler.core.config import (
    get_event_types,
    get_event_list,
    get_configured_inputs,
    get_configured_outputs,
    get_app_config,
    load_mapping_yaml,
)
from midi_event_handler.core.events.handlers import MidiEventHandler, MidiChordProcessor
from midi_event_handler.core.events.indexer import MidiEventIndex
from midi_event_handler.core.midi.listener import MidiListener
from midi_event_handler.core.midi.outputs import MidiOutputManager
from midi_event_handler.core.midi.utils import get_ports_status
from midi_event_handler.core.exceptions import MidiAppError, port_collision
from midi_event_handler.tools.connection import ConnectionManager

log = logging.getLogger(__name__)

manager = ConnectionManager("meh-app")


async def notify_app_state():
    await manager.notify({"notify": "state"})


def notify_app_state_nowait():
    manager.notify_nowait({"notify": "state"})


@dataclass
class StartResult:
    """Result of MidiApp.start() with success status and error details."""

    success: bool
    errors: List[MidiAppError] = field(default_factory=list)

    def add_error(self, error: MidiAppError):
        """Add an error to the result."""
        self.errors.append(error)
        self.success = False

    @property
    def error_message(self) -> Optional[str]:
        """Combined short message for toast display."""
        if not self.errors:
            return None
        if len(self.errors) == 1:
            return self.errors[0].short_message
        return f"{len(self.errors)} errors occurred. Click for details."

    @property
    def has_details(self) -> bool:
        """Whether detailed error info is available."""
        return len(self.errors) > 0

    @property
    def error_details(self) -> List[Dict[str, Any]]:
        """Errors as list of dicts for JSON/template use."""
        return [e.to_dict() for e in self.errors]


class MidiApp:
    def __init__(self):
        self.running = False
        self._tasks: List[asyncio.Task] = []
        self._monitor_task: Optional[asyncio.Task] = None

        # Show tracking
        self.started_at: Optional[float] = None
        self.trigger_counts: Dict[str, int] = defaultdict(int)
        self.event_log: List[Dict[str, Any]] = []  # Recent events
        self.max_log_size = 50
        self.last_activity: Dict[str, float] = {}  # Last MIDI input per port

        self._mapping_error: Optional[MidiAppError] = None
        self._setup_from_mapping()

    def _setup_from_mapping(self):
        self._mapping_error = None
        self.chord_queue = asyncio.Queue()
        self.event_queues = {t: asyncio.Queue() for t in get_event_types()}
        self.outputs = MidiOutputManager()

        try:
            self.index = MidiEventIndex(get_event_list())
        except MidiAppError as e:
            log.warning(f"[Setup] Mapping error: {e.short_message}")
            self._mapping_error = e
            self.index = MidiEventIndex()

        self.listeners = [MidiListener(name, self.chord_queue) for name in get_configured_inputs()]

        self.handlers = {
            t: MidiEventHandler(self.event_queues[t], self.index, self.outputs, self.log_event)
            for t in self.event_queues
        }

        self.chord_processor = MidiChordProcessor(
            chord_queue=self.chord_queue,
            event_queues=self.event_queues,
            event_index=self.index,
            on_activity=self.record_activity,
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

    async def start(self) -> StartResult:
        """
        Start the MIDI event handler.

        Returns:
            StartResult with success status and any errors.
        """
        if self.running:
            log.info("[Start] Already running")
            return StartResult(success=True)

        result = StartResult(success=True)

        # Step 0: Check for mapping errors (e.g. duplicate event names)
        if self._mapping_error:
            result.add_error(self._mapping_error)
            return result

        # Step 0b: Check for port collisions (multiple inputs resolving to same port)
        resolved_map: Dict[str, List[str]] = defaultdict(list)
        for listener in self.listeners:
            if listener.port_name:
                resolved_map[listener.port_name].append(listener.friendly_port_name)
        for resolved, friendly_names in resolved_map.items():
            if len(friendly_names) > 1:
                log.error(f"[Start] Port collision: {friendly_names} -> {resolved}")
                result.add_error(port_collision(friendly_names, resolved))
        if not result.success:
            return result

        # Step 1: Try to open all input ports
        log.info("[Start] Opening input ports...")
        for listener in self.listeners:
            try:
                listener.open()
            except MidiAppError as e:
                log.error(f"[Start] Failed to open input: {e.short_message}")
                result.add_error(e)

        # Step 2: Try to register all output ports
        log.info("[Start] Registering output ports...")
        for name in get_configured_outputs():
            try:
                self.outputs.register(name)
            except MidiAppError as e:
                log.error(f"[Start] Failed to register output: {e.short_message}")
                result.add_error(e)

        # If any port failed, clean up and return
        if not result.success:
            log.error(f"[Start] Failed with {len(result.errors)} error(s), cleaning up...")
            for listener in self.listeners:
                listener.close()
            self.outputs.close_all()
            return result

        # All ports OK - spawn tasks
        self.running = True
        self.started_at = time.time()
        self.trigger_counts.clear()
        self.event_log.clear()
        self.last_activity.clear()

        self._tasks = (
            [
                asyncio.create_task(handler.run(), name=f"handler-{event_type}")
                for event_type, handler in self.handlers.items()
            ]
            + [
                asyncio.create_task(listener.run(), name=f"listener-{listener.friendly_port_name}")
                for listener in self.listeners
            ]
            + [asyncio.create_task(self.chord_processor.run(), name="chord-processor")]
        )

        # Start task monitor
        self._monitor_task = asyncio.create_task(self._monitor_tasks(), name="task-monitor")

        log.info(f"[Start] Spawned {len(self._tasks)} tasks + monitor")
        await notify_app_state()

        return result

    async def _monitor_tasks(self) -> None:
        """
        Watch for task crashes (exceptions).

        NOTE: Runtime port disconnection cannot be detected reliably with mido/rtmidi.
        If a port is disconnected, iter_pending() silently returns nothing and the
        port stays in the available list as a ghost. User must notice and restart.
        """
        from midi_event_handler.core.exceptions import task_crashed

        log.info("[Monitor] Task monitor started")

        while self.running and self._tasks:
            # Wait for any task to complete or timeout
            done, pending = await asyncio.wait(self._tasks, timeout=5.0, return_when=asyncio.FIRST_COMPLETED)

            if not self.running:
                break

            # Check for crashed tasks
            for task in done:
                if task.cancelled():
                    continue

                exc = task.exception()
                if exc:
                    task_name = task.get_name()
                    error_msg = str(exc)
                    log.error(f"[Monitor] Task '{task_name}' crashed: {error_msg}")

                    # Create error and notify via WebSocket
                    error = task_crashed(task=task_name, error=error_msg)
                    await self._emergency_stop(error)
                    return

            # Remove completed tasks from list
            self._tasks = [t for t in self._tasks if not t.done()]

        log.info("[Monitor] Task monitor exiting")

    async def _emergency_stop(self, error: MidiAppError) -> None:
        """Stop the app due to an error and notify the user via WebSocket."""
        log.error(f"[Emergency] Stopping due to: {error.short_message}")

        # Notify via WebSocket for toast display
        await manager.notify(
            {
                "toast": error.short_message,
                "toast_type": "error",
                "toast_detail": error.detailed_message,
            }
        )

        # Stop the app
        await self.stop()

    async def stop(self) -> None:
        """Stop the MIDI event handler and clean up resources."""
        if not self.running:
            log.info("[Stop] Not running")
            return

        self.running = False
        self.started_at = None

        # Signal listeners to stop
        log.info("[Stop] Stopping listeners...")
        for listener in self.listeners:
            listener.stop()
        await asyncio.sleep(0.100)

        # Cancel monitor task first (it watches _tasks)
        if self._monitor_task and not self._monitor_task.done():
            log.info("[Stop] Cancelling monitor task...")
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self._monitor_task = None

        # Cancel all tasks
        log.info("[Stop] Cancelling tasks...")
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Close all ports
        log.info("[Stop] Closing ports...")
        for listener in self.listeners:
            listener.close()
        self.outputs.close_all()

        log.info("[Stop] Stopped!")
        await notify_app_state()

    def get_status(self) -> Dict[str, Any]:
        now = time.time()

        # Build handler states with timing info
        handler_states = {}
        for event_type, handler in self.handlers.items():
            state = {
                "active": handler.event is not None,
                "locked": handler.locked,
                "event": handler.event.to_dict() if handler.event else None,
            }
            # Add timing info if event is active
            if handler.event and hasattr(handler, "_event_started_at") and handler._event_started_at:
                elapsed = now - handler._event_started_at
                state["elapsed"] = round(elapsed, 1)
                state["event_started_at"] = handler._event_started_at
                if handler.event.duration_max:
                    remaining = handler.event.duration_max - elapsed
                    state["remaining"] = max(0, round(remaining, 1))
            handler_states[event_type] = state

        # Get activity thresholds from config
        app_config = get_app_config()
        warning_threshold = app_config.get("activity_warning", 60)
        danger_threshold = app_config.get("activity_danger", 300)

        # Build port activity status
        ports_status = get_ports_status()
        for port_info in ports_status["inputs"]:
            port_name = port_info["friendly_name"]
            last_active = self.last_activity.get(port_name)
            if last_active and self.running:
                inactive_seconds = now - last_active
                port_info["last_activity"] = last_active
                port_info["inactive_seconds"] = round(inactive_seconds, 1)
                if inactive_seconds < warning_threshold:
                    port_info["activity_status"] = "active"
                elif inactive_seconds < danger_threshold:
                    port_info["activity_status"] = "warning"
                else:
                    port_info["activity_status"] = "danger"
            else:
                port_info["activity_status"] = "unknown" if self.running else None

        return {
            "running": self.running,
            "started_at": self.started_at,
            "uptime": round(now - self.started_at, 1) if self.started_at else None,
            "handlers": handler_states,
            "midi_ports": ports_status,
            "trigger_counts": dict(sorted(self.trigger_counts.items(), key=lambda x: x[1], reverse=True)),
            "event_log": self.event_log[-20:],  # Last 20 events
            "tasks": len(self._tasks),
        }

    def log_event(self, event_name: str, action: str):
        """Log an event action for the dashboard."""
        self.trigger_counts[event_name] += 1 if action == "start" else 0
        self.event_log.append(
            {
                "event": event_name,
                "action": action,
                "timestamp": time.time(),
            }
        )
        if len(self.event_log) > self.max_log_size:
            self.event_log.pop(0)

    def record_activity(self, port: str):
        """Record MIDI activity on a port."""
        self.last_activity[port] = time.time()

    async def trigger_event(self, event_name: str) -> bool:
        """Manually trigger an event by name. Returns True if triggered."""
        if not self.running:
            log.warning(f"[Trigger] Cannot trigger event '{event_name}' - app not running")
            return False

        event = self.index.lookup_by_name(event_name)
        if not event:
            log.warning(f"[Trigger] Event not found: {event_name}")
            return False

        if event.type not in self.event_queues:
            log.warning(f"[Trigger] Unknown event type: {event.type}")
            return False

        log.info(f"[Trigger] Manually triggering event: {event_name}")
        await self.event_queues[event.type].put(event)
        return True

    async def stop_event(self, event_name: str) -> bool:
        """Manually stop an event by name. Returns True if stopped."""
        if not self.running:
            log.warning(f"[Trigger] Cannot stop event '{event_name}' - app not running")
            return False

        event = self.index.lookup_by_name(event_name)
        if not event:
            log.warning(f"[Trigger] Event not found: {event_name}")
            return False

        if event.type not in self.event_queues:
            log.warning(f"[Trigger] Unknown event type: {event.type}")
            return False

        # Check if this event is actually active
        handler = self.handlers.get(event.type)
        if not handler or not handler.event or handler.event.name != event_name:
            log.warning(f"[Trigger] Event '{event_name}' is not currently active")
            return False

        log.info(f"[Trigger] Manually stopping event: {event_name}")
        await self.event_queues[event.type].put(None)
        return True
