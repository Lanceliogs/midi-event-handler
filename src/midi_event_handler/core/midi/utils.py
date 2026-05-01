import mido
from typing import List, Optional


def resolve_port(name: str, available: List[str]) -> Optional[str]:
    """Try to resolve a friendly port name to an available port."""
    if not name:
        return None
    return next((a for a in available if name in a), None)


def _resolve_ports_status(configured: List[str], available: List[str]) -> List[dict]:
    """Build status list for configured ports."""
    result = []
    for name in configured:
        matched = resolve_port(name, available)
        result.append(
            {
                "friendly_name": name,
                "real_name": matched or "Unavailable",
                "available": matched is not None,
            }
        )
    return result


def get_ports_status(inputs: Optional[List[str]] = None, outputs: Optional[List[str]] = None) -> dict:
    """
    Get ports status for configured inputs/outputs.

    If inputs/outputs not provided, uses global config.
    """
    if inputs is None or outputs is None:
        from midi_event_handler.core.config import (
            get_configured_inputs,
            get_configured_outputs,
        )

        inputs = inputs or get_configured_inputs()
        outputs = outputs or get_configured_outputs()

    available_inputs = mido.get_input_names()
    available_outputs = mido.get_output_names()

    return {
        "inputs": _resolve_ports_status(inputs, available_inputs),
        "outputs": _resolve_ports_status(outputs, available_outputs),
        "available_inputs": available_inputs,
        "available_outputs": available_outputs,
    }
