# Error Handling & Task Monitoring Refactor

## Problem Statement

Currently, the `MidiApp` class has weak error handling:
1. Port resolution failures are logged but not propagated
2. Port opening failures can crash or silently fail
3. Tasks are fire-and-forget - no monitoring for early termination
4. Users have no way to know *why* the app failed to start or stopped unexpectedly

## Goals

1. **Explicit error reporting** on start failure with specific reasons
2. **Task monitoring** to detect unexpected terminations
3. **Real-time error notifications** via WebSocket → toast
4. **Graceful degradation** - app stops cleanly when a critical task dies

---

## Step 1: Define Exception System and Result Types ✓

Created a comprehensive exception system with user-friendly messages.

**File:** `src/midi_event_handler/core/exceptions.py`

```python
class ErrorCode(Enum):
    PORT_NOT_FOUND = "port_not_found"
    PORT_BUSY = "port_busy"
    PORT_OPEN_FAILED = "port_open_failed"
    NO_EVENTS = "no_events"
    NO_INPUTS = "no_inputs"
    NO_OUTPUTS = "no_outputs"
    TASK_CRASHED = "task_crashed"

class MidiAppError(Exception):
    def __init__(self, code: ErrorCode, **context):
        self.code = code
        self.context = context
    
    @property
    def short_message(self) -> str:
        """For toast display"""
    
    @property
    def detailed_message(self) -> str:
        """For modal display - includes troubleshooting steps"""

# Convenience factories
def port_not_found(port: str, port_type: str, available: list) -> MidiAppError
def port_busy(port: str, port_type: str) -> MidiAppError
def port_open_failed(port: str, port_type: str, error: str) -> MidiAppError
def task_crashed(task: str, error: str) -> MidiAppError
```

**File:** `src/midi_event_handler/core/app.py`

```python
@dataclass
class StartResult:
    success: bool
    errors: List[MidiAppError] = field(default_factory=list)

    def add_error(self, error: MidiAppError):
        self.errors.append(error)
        self.success = False

    @property
    def error_message(self) -> Optional[str]:
        """For toast - short version"""

    @property
    def error_details(self) -> List[Dict[str, Any]]:
        """For JSON/template - full details"""
```

---

## Step 2: Split Port Lifecycle in MidiListener

Separate port opening from the run loop. The port is opened explicitly and kept open until `close()` is called.

**File:** `src/midi_event_handler/core/midi/listener.py`

Current issue: `run()` uses a context manager to open the port, logs and returns silently if port is invalid.

```python
class PortOpenError(Exception):
    """Raised when a MIDI port cannot be opened."""
    pass

class MidiListener:
    def __init__(self, port_name: str, chord_queue: asyncio.Queue):
        self.loop = asyncio.get_running_loop()
        self.chord_queue = chord_queue
        self.buffer: deque[MidiMessage] = deque()
        self.stop_event = threading.Event()
        
        self.friendly_port_name = port_name
        self.port_name = ""  # Resolved name
        self._port = None    # The open mido port
        self._resolve_port(port_name)

    def _resolve_port(self, port_name: str):
        """Resolve friendly name to actual MIDI port name."""
        available_ports = mido.get_input_names()
        for name in available_ports:
            if port_name in name:
                self.port_name = name
                return

    def open(self) -> None:
        """
        Open the MIDI port. Raises PortOpenError on failure.
        Must be called before run().
        """
        if not self.port_name:
            available = mido.get_input_names()
            raise PortOpenError(
                f"Input '{self.friendly_port_name}' not found. "
                f"Available: {', '.join(available) or 'none'}"
            )
        try:
            self._port = mido.open_input(self.port_name)
            log.info(f"[Open] Port opened: {self.port_name}")
        except Exception as e:
            raise PortOpenError(
                f"Cannot open input '{self.friendly_port_name}': {e}"
            )

    def close(self) -> None:
        """Close the MIDI port if open."""
        if self._port:
            try:
                self._port.close()
            except Exception:
                pass
            self._port = None
            log.info(f"[Close] Port closed: {self.friendly_port_name}")

    async def run(self):
        """
        Run the listener loop. Port must be opened first via open().
        """
        if not self._port:
            raise RuntimeError(f"Port not open: {self.friendly_port_name}")

        def loop():
            log.info(f"[Run] Starting loop for {self.friendly_port_name}")
            try:
                while not self.stop_event.is_set():
                    for msg in self._port.iter_pending():
                        # ... existing message handling ...
                    time.sleep(0.001)
            except Exception:
                log.exception(f"[Run] Exception in listener: {self.friendly_port_name}")
                raise  # Re-raise so task monitor can catch it
            finally:
                self.stop_event.clear()
                log.info(f"[Run] Listener stopped: {self.friendly_port_name}")
        
        await asyncio.to_thread(loop)

    def stop(self):
        """Request the listener loop to stop."""
        log.info(f"[Stop] Requesting stop for {self.friendly_port_name}")
        self.stop_event.set()
```

**Lifecycle:**
```
listener = MidiListener("PortName", queue)
listener.open()      # Raises PortOpenError if unavailable
task = asyncio.create_task(listener.run())
# ... later ...
listener.stop()      # Signal loop to exit
await task           # Wait for loop to finish
listener.close()     # Close the port
```

---

## Step 3: Fix Port Opening in MidiOutputManager

The current code has a bug: if the port is not found, `real_name` remains empty and `mido.open_output("")` is called, which crashes.

**File:** `src/midi_event_handler/core/midi/outputs.py`

**Current (buggy):**
```python
def register(self, name: str):
    # ...
    if not real_name:
        log.warning(f"[Register] Can't register port as output: {name}")
    if name not in self._outputs:
        self._outputs[name] = mido.open_output(real_name)  # BUG: opens "" if not found!
```

**Fixed:**
```python
class PortOpenError(Exception):
    """Raised when a MIDI port cannot be opened."""
    pass

class MidiOutputManager:
    # ... existing code ...

    def register(self, name: str) -> None:
        """
        Register and open an output port.
        Raises PortOpenError if port cannot be opened.
        """
        if name in self._outputs:
            return  # Already registered
            
        available_outputs = mido.get_output_names()
        real_name = ""
        
        for output in available_outputs:
            if name in output:
                real_name = output
                break
        
        if not real_name:
            raise PortOpenError(
                f"Output '{name}' not found. "
                f"Available: {', '.join(available_outputs) or 'none'}"
            )
        
        try:
            self._outputs[name] = mido.open_output(real_name)
            log.info(f"[Register] {name} -> {real_name}")
        except Exception as e:
            raise PortOpenError(f"Cannot open output '{name}': {e}")
```

---

## Step 4: Refactor MidiApp.start() to Return Result

**File:** `src/midi_event_handler/core/app.py`

```python
async def start(self) -> StartResult:
    if self.running:
        log.info("[Start] Already running")
        return StartResult(success=True)
    
    errors = []
    
    # Step 1: Try to open all input ports
    for listener in self.listeners:
        try:
            listener.open()
        except PortOpenError as e:
            errors.append(str(e))
    
    # Step 2: Try to register all output ports
    for name in get_configured_outputs():
        try:
            self.outputs.register(name)
        except PortOpenError as e:
            errors.append(str(e))
    
    # If any port failed, clean up and abort
    if errors:
        log.error(f"[Start] Failed to open ports: {errors}")
        for listener in self.listeners:
            listener.close()
        self.outputs.close_all()
        return StartResult(success=False, errors=errors)
    
    # All ports OK - spawn tasks
    self.running = True
    self._tasks = [
        asyncio.create_task(handler.run(), name=f"handler-{t}")
        for t, handler in self.handlers.items()
    ] + [
        asyncio.create_task(listener.run(), name=f"listener-{listener.friendly_port_name}")
        for listener in self.listeners
    ] + [
        asyncio.create_task(self.chord_processor.run(), name="chord-processor")
    ]
    
    # Start task monitor
    self._monitor_task = asyncio.create_task(self._monitor_tasks(), name="task-monitor")
    
    log.info("[Start] Tasks spawned!")
    await notify_app_state()
    
    return StartResult(success=True)
```

Also update `stop()` to close listener ports:

```python
async def stop(self):
    if not self.running:
        log.info("[Stop] Not running")
        return
    self.running = False

    log.info("[Stop] Stopping listeners...")
    for listener in self.listeners:
        listener.stop()
    await asyncio.sleep(0.100)
    
    log.info("[Stop] Cancelling tasks...")
    for task in self._tasks:
        if not task.done():
            task.cancel()
    await asyncio.gather(*self._tasks, return_exceptions=True)
    self._tasks.clear()
    
    log.info("[Stop] Closing ports...")
    for listener in self.listeners:
        listener.close()
    self.outputs.close_all()
    
    log.info("[Stop] Stopped!")
    await notify_app_state()
```

---

## Step 5: Add Task Monitor

### Important: mido/rtmidi limitation

Testing revealed that **runtime port disconnection cannot be reliably detected**:

1. `iter_pending()` does NOT raise when disconnected - silently returns nothing
2. `port.closed` stays `False`
3. Port name stays in `mido.get_input_names()` (ghost port)

See: https://github.com/mido/mido/issues/607

**Conclusion:** We can only monitor for task crashes (exceptions), not port disconnections.
Runtime disconnection → user notices manually and restarts.

**File:** `src/midi_event_handler/core/app.py`

```python
async def _monitor_tasks(self):
    """
    Watch for task crashes (exceptions).
    
    NOTE: Runtime port disconnection cannot be detected reliably with mido/rtmidi.
    If a port is disconnected, iter_pending() silently returns nothing and the
    port stays in the available list as a ghost. User must notice and restart.
    """
    while self.running and self._tasks:
        # Wait for any task to complete
        done, pending = await asyncio.wait(
            self._tasks,
            timeout=5.0,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        if not self.running:
            break
        
        # Check for crashed tasks
        for task in done:
            if task.cancelled():
                continue
            
            exc = task.exception()
            if exc:
                task_name = task.get_name()
                error_msg = f"Task '{task_name}' crashed: {exc}"
                log.error(f"[Monitor] {error_msg}")
                await self._emergency_stop(error_msg)
                return
        
        # Remove completed tasks from list
        self._tasks = [t for t in self._tasks if not t.done()]
    
    log.info("[Monitor] Task monitor exiting")

async def _emergency_stop(self, reason: str):
    """Stop the app due to an error and notify the user."""
    await manager.notify({
        "toast": reason,
        "toast_type": "error"
    })
    await self.stop()
```

### What this DOES detect:
- Exceptions thrown in handler/listener/processor tasks
- Programming errors, unexpected state, etc.

### What this DOES NOT detect:
- USB device unplugged (ghost port remains)
- Device powered off
- Port grabbed by another application mid-session

---

## Step 6: Update API to Handle StartResult

**File:** `src/midi_event_handler/web/routers/api.py`

```python
@router.post("/start")
async def start_show():
    if midiapp.running:
        return Response(
            content='{"running": true}',
            media_type="application/json",
            headers={"X-Toast": "Already running", "X-Toast-Type": "warning"}
        )
    
    result = await midiapp.start()
    
    if result.success:
        return Response(
            content='{"running": true}',
            media_type="application/json",
            headers={"X-Toast": "MIDI app started", "X-Toast-Type": "success"}
        )
    else:
        return Response(
            content=f'{{"running": false, "errors": {json.dumps(result.errors)}}}',
            media_type="application/json",
            status_code=400,
            headers={
                "X-Toast": result.error_message,
                "X-Toast-Type": "error"
            }
        )
```

---

## Step 7: Handle Toast Messages from WebSocket

The WebSocket can now send toast notifications for runtime errors.

**File:** `src/midi_event_handler/web/static/js/main.js`

```javascript
// In the WebSocket message handler:
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Handle toast notifications from server
    if (data.toast) {
        showToast(data.toast, data.toast_type || 'error');
    }
    
    // Handle state notifications (existing)
    if (data.notify === 'state') {
        // ... existing HTMX refresh logic
    }
};
```

---

## Implementation Order

| Step | File(s) | Risk | Dependencies |
|------|---------|------|--------------|
| 1 | `core/app.py` | Low | None |
| 2 | `core/midi/listener.py` | Medium | None |
| 3 | `core/midi/outputs.py` | Medium | None |
| 4 | `core/app.py` | High | Steps 1, 2, 3 |
| 5 | `core/app.py` | Medium | Step 4 |
| 6 | `web/routers/api.py` | Low | Step 4 |
| 7 | `web/static/js/main.js` | Low | Step 5 |

**Note:** `PortOpenError` will be defined in both `listener.py` and `outputs.py` for now. 
If we want to share it, we can create `core/midi/errors.py` later.

---

## Testing Strategy

1. **Unit tests for PortOpenError:**
   - Test with invalid port name
   - Test with busy port (if possible to simulate)

2. **Integration tests for StartResult:**
   - Test successful start (mock ports available)
   - Test start with missing input port
   - Test start with missing output port

3. **Unit tests for task monitor:**
   - Create a task that raises an exception
   - Verify `_emergency_stop` is called with correct message

**Note:** Runtime port disconnection cannot be tested - mido/rtmidi doesn't report it.

---

## Rollback Plan

Each step is isolated. If issues arise:
- Steps 1-3: Revert individual files
- Steps 4-5: Revert `core/app.py`
- Steps 6-7: Revert web layer (no core impact)

---

## Open Questions

1. Should we attempt partial start (some ports OK, some failed)?
   - **Proposed:** No, fail fast. All configured ports must be available.

2. Should task monitor auto-restart failed tasks?
   - **Proposed:** No, stop the app and let user fix the issue.

3. How long should toast messages stay visible for critical errors?
   - **Proposed:** 10 seconds for errors (vs 3 seconds for success).

## Known Limitations

**Runtime port disconnection is undetectable** with mido/rtmidi on Windows:
- Port stays in `mido.get_input_names()` as a ghost
- `port.closed` stays `False`
- `iter_pending()` silently returns nothing

This is a mido limitation, not something we can fix. User must notice and restart manually.
See: https://github.com/mido/mido/issues/607
