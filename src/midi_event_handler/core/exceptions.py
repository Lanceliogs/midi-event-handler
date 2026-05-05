"""
MIDI Event Handler exceptions with user-friendly error messages.

All application-specific exceptions should be defined here with:
- An ErrorCode enum value for categorization
- Context dict for dynamic message generation
- Short message for toast display
- Detailed message for modal/help display
"""

from enum import Enum
from typing import Dict, Any


class ErrorCode(Enum):
    """Error categories for MidiAppError."""

    # Port errors
    PORT_NOT_FOUND = "port_not_found"
    PORT_BUSY = "port_busy"
    PORT_OPEN_FAILED = "port_open_failed"
    PORT_COLLISION = "port_collision"

    # Configuration errors
    NO_EVENTS = "no_events"
    NO_INPUTS = "no_inputs"
    NO_OUTPUTS = "no_outputs"

    # Mapping errors
    DUPLICATE_EVENT_NAMES = "duplicate_event_names"

    # Runtime errors
    TASK_CRASHED = "task_crashed"


# Short messages for toast display
SHORT_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.PORT_NOT_FOUND: "Port '{port}' not found",
    ErrorCode.PORT_BUSY: "Port '{port}' is busy",
    ErrorCode.PORT_OPEN_FAILED: "Cannot open port '{port}'",
    ErrorCode.PORT_COLLISION: "Port collision: {inputs} resolve to the same port",
    ErrorCode.NO_EVENTS: "No events configured",
    ErrorCode.NO_INPUTS: "No input ports configured",
    ErrorCode.NO_OUTPUTS: "No output ports configured",
    ErrorCode.DUPLICATE_EVENT_NAMES: "Duplicate event names found. Rename or delete them first.",
    ErrorCode.TASK_CRASHED: "Task '{task}' crashed",
}

# Detailed messages for modal display
DETAILED_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.PORT_NOT_FOUND: """
The {port_type} port '{port}' could not be found.

This usually means:
• The MIDI device is not connected
• The device is powered off
• The port name in your configuration doesn't match the actual device name

Available {port_type} ports:
{available_ports}

To fix this:
1. Check that your MIDI device is connected and powered on
2. Update your mapping.yaml with the correct port name
3. Restart the application
""".strip(),
    ErrorCode.PORT_BUSY: """
The {port_type} port '{port}' is already in use by another application.

Common causes:
• Another music application (DAW, MIDI monitor) has the port open
• A previous instance of this application didn't close properly
• The system MIDI service is holding the port

To fix this:
1. Close other applications that might be using MIDI
2. If the problem persists, try unplugging and reconnecting the device
3. As a last resort, restart your computer
""".strip(),
    ErrorCode.PORT_OPEN_FAILED: """
Failed to open the {port_type} port '{port}'.

Error details: {error}

This can happen when:
• The device was disconnected right as we tried to open it
• There's a driver issue with the MIDI device
• The port is in an invalid state

To fix this:
1. Unplug the MIDI device and plug it back in
2. Check if the device works in other applications
3. Try restarting the application
""".strip(),
    ErrorCode.PORT_COLLISION: """
Multiple configured inputs resolve to the same MIDI port.

Inputs: {inputs}
Resolved port: {resolved}

This happens when input names partially match the same device. Each input must resolve to a different MIDI port.

To fix this:
1. Open the Editor page
2. Rename or remove one of the conflicting inputs
3. Make sure each input name matches a different MIDI device
4. Save your mapping
""".strip(),
    ErrorCode.NO_EVENTS: """
No events are configured in your mapping.

The application needs at least one event to be useful. Events define what happens when you play specific MIDI notes.

To fix this:
1. Open the Editor page
2. Add at least one event with a trigger (MIDI notes) and messages (what to send)
3. Save your mapping
""".strip(),
    ErrorCode.NO_INPUTS: """
No input ports are configured in your mapping.

Input ports are MIDI devices that send notes TO this application (like a keyboard or pad controller).

To fix this:
1. Open the Editor page
2. Add at least one input port in the Configuration section
3. Make sure the port name matches your MIDI device
4. Save your mapping
""".strip(),
    ErrorCode.NO_OUTPUTS: """
No output ports are configured in your mapping.

Output ports are MIDI devices that RECEIVE messages from this application (like a synthesizer or lighting controller).

To fix this:
1. Open the Editor page
2. Add at least one output port in the Configuration section
3. Make sure the port name matches your target MIDI device
4. Save your mapping
""".strip(),
    ErrorCode.DUPLICATE_EVENT_NAMES: """
Multiple events share the same name, which must be unique.

Duplicate names:
{names_bullet}

Each event must have a unique name for triggers, fallbacks, and the editor to work correctly.

To fix this:
1. Use the "Rename Duplicates" button to auto-rename them (appends ~1, ~2, etc.)
2. Or manually rename/delete the duplicates in the editor
3. Save your mapping once all names are unique
""".strip(),
    ErrorCode.TASK_CRASHED: """
An internal task crashed unexpectedly.

Task: {task}
Error: {error}

This is likely a bug in the application. The application has been stopped to prevent further issues.

What you can do:
1. Try restarting the application
2. If the problem persists, check the logs for more details
3. Report this issue with the error message above
""".strip(),
}


class MidiAppError(Exception):
    """
    Application exception with user-friendly messages.

    Usage:
        raise MidiAppError(
            ErrorCode.PORT_NOT_FOUND,
            port="Piano",
            port_type="input",
            available_ports=["Port A", "Port B"]
        )
    """

    def __init__(self, code: ErrorCode, **context):
        self.code = code
        self.context = context
        super().__init__(self.short_message)

    @property
    def short_message(self) -> str:
        """Short message for toast display."""
        template = SHORT_MESSAGES.get(self.code, str(self.code))
        try:
            return template.format(**self.context)
        except KeyError:
            return template

    @property
    def detailed_message(self) -> str:
        """Detailed message for modal display."""
        template = DETAILED_MESSAGES.get(self.code, self.short_message)

        # Format available_ports as a bullet list if present
        ctx = self.context.copy()
        if "available_ports" in ctx:
            ports = ctx["available_ports"]
            if isinstance(ports, list):
                if ports:
                    ctx["available_ports"] = "\n".join(f"  • {p}" for p in ports)
                else:
                    ctx["available_ports"] = "  (none detected)"

        try:
            return template.format(**ctx)
        except KeyError as e:
            return f"{self.short_message}\n\n(Missing context: {e})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "code": self.code.value,
            "short": self.short_message,
            "detail": self.detailed_message,
            "context": self.context,
        }


# Convenience factory functions for common errors


def port_not_found(port: str, port_type: str, available: list) -> MidiAppError:
    """Create a PORT_NOT_FOUND error."""
    return MidiAppError(
        ErrorCode.PORT_NOT_FOUND,
        port=port,
        port_type=port_type,
        available_ports=available,
    )


def port_busy(port: str, port_type: str) -> MidiAppError:
    """Create a PORT_BUSY error."""
    return MidiAppError(
        ErrorCode.PORT_BUSY,
        port=port,
        port_type=port_type,
    )


def port_open_failed(port: str, port_type: str, error: str) -> MidiAppError:
    """Create a PORT_OPEN_FAILED error."""
    return MidiAppError(
        ErrorCode.PORT_OPEN_FAILED,
        port=port,
        port_type=port_type,
        error=error,
    )


def port_collision(inputs: list, resolved: str) -> MidiAppError:
    """Create a PORT_COLLISION error."""
    return MidiAppError(
        ErrorCode.PORT_COLLISION,
        inputs=", ".join(f"'{n}'" for n in inputs),
        resolved=resolved,
    )


def duplicate_event_names(names: list) -> MidiAppError:
    """Create a DUPLICATE_EVENT_NAMES error."""
    formatted = ", ".join(names)
    bullet_list = "\n".join(f"  • {n}" for n in names)
    return MidiAppError(
        ErrorCode.DUPLICATE_EVENT_NAMES,
        names=formatted,
        names_bullet=bullet_list,
    )


def task_crashed(task: str, error: str) -> MidiAppError:
    """Create a TASK_CRASHED error."""
    return MidiAppError(
        ErrorCode.TASK_CRASHED,
        task=task,
        error=error,
    )
