import mido
from typing import List

from midi_event_handler.core.config import (
    get_configured_inputs, get_configured_outputs
)

def resolve_ports_status(configured: List[str], available: List[str]) -> List[dict]:
    status = []
    for name in configured:
        matched = next((a for a in available if name in a), None)
        status.append({
            "friendly_name": name,
            "real_name": matched or "Unavailable",
            "available": matched is not None
        })
    return status

def get_ports_status():
    configured_inputs = get_configured_inputs()
    configured_outputs = get_configured_outputs()
    available_inputs = mido.get_input_names()
    available_outputs = mido.get_output_names()

    return {
        "inputs": resolve_ports_status(configured_inputs, available_inputs),
        "outputs": resolve_ports_status(configured_outputs, available_outputs)
    }
