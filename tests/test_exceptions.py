"""Tests for the exceptions module."""

from midi_event_handler.core.exceptions import (
    ErrorCode,
    MidiAppError,
    port_not_found,
    port_busy,
    port_open_failed,
    task_crashed,
    duplicate_event_names,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_codes_exist(self):
        """All expected error codes should exist."""
        assert ErrorCode.PORT_NOT_FOUND.value == "port_not_found"
        assert ErrorCode.PORT_BUSY.value == "port_busy"
        assert ErrorCode.PORT_OPEN_FAILED.value == "port_open_failed"
        assert ErrorCode.NO_EVENTS.value == "no_events"
        assert ErrorCode.NO_INPUTS.value == "no_inputs"
        assert ErrorCode.NO_OUTPUTS.value == "no_outputs"
        assert ErrorCode.DUPLICATE_EVENT_NAMES.value == "duplicate_event_names"
        assert ErrorCode.TASK_CRASHED.value == "task_crashed"


class TestMidiAppError:
    """Tests for MidiAppError exception."""

    def test_basic_error(self):
        """Error should store code and context."""
        error = MidiAppError(ErrorCode.PORT_NOT_FOUND, port="Piano", port_type="input")

        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert error.context["port"] == "Piano"
        assert error.context["port_type"] == "input"

    def test_short_message(self):
        """Short message should be formatted from template."""
        error = MidiAppError(ErrorCode.PORT_NOT_FOUND, port="Piano")

        assert error.short_message == "Port 'Piano' not found"

    def test_short_message_missing_context(self):
        """Short message should handle missing context gracefully."""
        error = MidiAppError(ErrorCode.PORT_NOT_FOUND)

        # Should return template as-is if context missing
        assert "Port" in error.short_message

    def test_detailed_message(self):
        """Detailed message should include troubleshooting info."""
        error = MidiAppError(
            ErrorCode.PORT_NOT_FOUND,
            port="Piano",
            port_type="input",
            available_ports=["Port A", "Port B"],
        )

        detail = error.detailed_message
        assert "Piano" in detail
        assert "input" in detail
        assert "Port A" in detail
        assert "Port B" in detail
        assert "not connected" in detail.lower() or "not found" in detail.lower()

    def test_detailed_message_empty_ports(self):
        """Detailed message should handle empty port list."""
        error = MidiAppError(
            ErrorCode.PORT_NOT_FOUND,
            port="Piano",
            port_type="input",
            available_ports=[],
        )

        detail = error.detailed_message
        assert "none detected" in detail.lower()

    def test_to_dict(self):
        """to_dict should return serializable dict."""
        error = MidiAppError(ErrorCode.PORT_BUSY, port="Lights", port_type="output")

        d = error.to_dict()

        assert d["code"] == "port_busy"
        assert "short" in d
        assert "detail" in d
        assert d["context"]["port"] == "Lights"

    def test_str_representation(self):
        """str() should return short message."""
        error = MidiAppError(ErrorCode.PORT_BUSY, port="Piano")

        assert str(error) == error.short_message


class TestFactoryFunctions:
    """Tests for convenience factory functions."""

    def test_port_not_found(self):
        """port_not_found should create correct error."""
        error = port_not_found(
            port="Piano",
            port_type="input",
            available=["Port A", "Port B"],
        )

        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert error.context["port"] == "Piano"
        assert error.context["port_type"] == "input"
        assert error.context["available_ports"] == ["Port A", "Port B"]
        assert "Piano" in error.short_message

    def test_port_busy(self):
        """port_busy should create correct error."""
        error = port_busy(port="Lights", port_type="output")

        assert error.code == ErrorCode.PORT_BUSY
        assert error.context["port"] == "Lights"
        assert "busy" in error.short_message.lower()

    def test_port_open_failed(self):
        """port_open_failed should create correct error."""
        error = port_open_failed(
            port="Piano",
            port_type="input",
            error="Device not responding",
        )

        assert error.code == ErrorCode.PORT_OPEN_FAILED
        assert error.context["error"] == "Device not responding"
        assert "Device not responding" in error.detailed_message

    def test_task_crashed(self):
        """task_crashed should create correct error."""
        error = task_crashed(task="listener-Piano", error="Connection lost")

        assert error.code == ErrorCode.TASK_CRASHED
        assert error.context["task"] == "listener-Piano"
        assert error.context["error"] == "Connection lost"
        assert "listener-Piano" in error.short_message

    def test_duplicate_event_names(self):
        """duplicate_event_names should create correct error."""
        error = duplicate_event_names(["foo", "bar"])

        assert error.code == ErrorCode.DUPLICATE_EVENT_NAMES
        assert "Duplicate event names" in error.short_message
        assert "foo" not in error.short_message
        assert "foo" in error.detailed_message
        assert "bar" in error.detailed_message
        assert "unique" in error.detailed_message.lower()


class TestStartResult:
    """Tests for StartResult dataclass."""

    def test_success_result(self):
        """Successful result should have no errors."""
        from midi_event_handler.core.app import StartResult

        result = StartResult(success=True)

        assert result.success is True
        assert len(result.errors) == 0
        assert result.error_message is None
        assert result.has_details is False

    def test_add_error(self):
        """Adding error should set success to False."""
        from midi_event_handler.core.app import StartResult

        result = StartResult(success=True)
        error = port_not_found("Piano", "input", [])

        result.add_error(error)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.has_details is True

    def test_error_message_single(self):
        """Single error should show its short message."""
        from midi_event_handler.core.app import StartResult

        result = StartResult(success=True)
        result.add_error(port_not_found("Piano", "input", []))

        assert "Piano" in result.error_message

    def test_error_message_multiple(self):
        """Multiple errors should show count."""
        from midi_event_handler.core.app import StartResult

        result = StartResult(success=True)
        result.add_error(port_not_found("Piano", "input", []))
        result.add_error(port_busy("Lights", "output"))

        assert "2 errors" in result.error_message

    def test_error_details(self):
        """error_details should return list of dicts."""
        from midi_event_handler.core.app import StartResult

        result = StartResult(success=True)
        result.add_error(port_not_found("Piano", "input", []))

        details = result.error_details

        assert len(details) == 1
        assert details[0]["code"] == "port_not_found"
        assert "short" in details[0]
        assert "detail" in details[0]
