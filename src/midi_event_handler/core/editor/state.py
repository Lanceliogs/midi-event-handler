"""
Editor State - manages in-memory mapping for the editor.
"""

import copy
import yaml
from collections import Counter
from typing import Optional, List

from midi_event_handler.core.config import RUNTIME_MAPPING_PATH, Mapping, empty_mapping
from midi_event_handler.core.events.models import MidiEvent

import logging

log = logging.getLogger(__name__)


class EditorState:
    """In-memory working copy of mapping for the editor."""

    def __init__(self):
        self.mapping: Mapping = empty_mapping()
        self._original: Mapping = empty_mapping()

    def load_from_runtime(self) -> bool:
        """Load mapping from runtime file into editor state."""
        if not RUNTIME_MAPPING_PATH.exists():
            log.warning("No runtime mapping file found")
            self.mapping = empty_mapping()
            self._original = copy.deepcopy(self.mapping)
            return False

        try:
            with RUNTIME_MAPPING_PATH.open("r") as f:
                data = yaml.safe_load(f) or {}
            self.mapping = Mapping.from_dict(data)
            self._original = copy.deepcopy(self.mapping)
            log.info("Loaded mapping into editor state")
            return True
        except Exception:
            log.exception("Failed to load mapping into editor state")
            self.mapping = empty_mapping()
            self._original = copy.deepcopy(self.mapping)
            return False

    @property
    def dirty(self) -> bool:
        """Check if there are unsaved changes."""
        return self.mapping != self._original

    def save_to_runtime(self) -> bool:
        """Save current mapping to runtime file."""
        try:
            RUNTIME_MAPPING_PATH.parent.mkdir(exist_ok=True)
            with RUNTIME_MAPPING_PATH.open("w") as f:
                yaml.dump(self.mapping.to_dict(), f, default_flow_style=False, sort_keys=False)
            self._original = copy.deepcopy(self.mapping)
            log.info("Saved mapping to runtime file")
            return True
        except Exception:
            log.exception("Failed to save mapping to runtime file")
            return False

    def to_yaml(self) -> str:
        """Export current mapping as YAML string."""
        return yaml.dump(self.mapping.to_dict(), default_flow_style=False, sort_keys=False)

    # ==========================================================================
    # Accessors
    # ==========================================================================

    @property
    def inputs(self) -> List[str]:
        return self.mapping.inputs

    @property
    def outputs(self) -> List[str]:
        return self.mapping.outputs

    @property
    def event_types(self) -> List[str]:
        return self.mapping.event_types

    @property
    def events(self) -> List[MidiEvent]:
        return self.mapping.events

    def get_event(self, name: str) -> Optional[MidiEvent]:
        return self.mapping.get_event(name)

    def get_events_by_type(self, event_type: str) -> List[MidiEvent]:
        return self.mapping.get_events_by_type(event_type)

    # ==========================================================================
    # Input mutations
    # ==========================================================================

    def add_input(self, name: str) -> bool:
        if name not in self.mapping.inputs:
            self.mapping.inputs.append(name)
            return True
        return False

    def update_input(self, old_name: str, new_name: str) -> bool:
        if old_name in self.mapping.inputs:
            idx = self.mapping.inputs.index(old_name)
            self.mapping.inputs[idx] = new_name
            return True
        return False

    def delete_input(self, name: str) -> bool:
        if name in self.mapping.inputs:
            self.mapping.inputs.remove(name)
            return True
        return False

    # ==========================================================================
    # Output mutations
    # ==========================================================================

    def add_output(self, name: str) -> bool:
        if name not in self.mapping.outputs:
            self.mapping.outputs.append(name)
            return True
        return False

    def update_output(self, old_name: str, new_name: str) -> bool:
        if old_name in self.mapping.outputs:
            idx = self.mapping.outputs.index(old_name)
            self.mapping.outputs[idx] = new_name
            return True
        return False

    def delete_output(self, name: str) -> bool:
        if name in self.mapping.outputs:
            self.mapping.outputs.remove(name)
            return True
        return False

    # ==========================================================================
    # Event type mutations
    # ==========================================================================

    def add_event_type(self, name: str) -> bool:
        if name not in self.mapping.event_types:
            self.mapping.event_types.append(name)
            return True
        return False

    def update_event_type(self, old_name: str, new_name: str) -> bool:
        if old_name in self.mapping.event_types:
            idx = self.mapping.event_types.index(old_name)
            self.mapping.event_types[idx] = new_name
            # Update events that use this type
            for event in self.mapping.events:
                if event.type == old_name:
                    event.type = new_name
            return True
        return False

    def delete_event_type(self, name: str) -> int:
        """Delete event type and cascade delete events. Returns count deleted."""
        if name in self.mapping.event_types:
            self.mapping.event_types.remove(name)
            original_count = len(self.mapping.events)
            self.mapping.events = [e for e in self.mapping.events if e.type != name]
            return original_count - len(self.mapping.events)
        return 0

    # ==========================================================================
    # Event mutations
    # ==========================================================================

    def add_event(self, event: MidiEvent) -> bool:
        if not any(e.name == event.name for e in self.mapping.events):
            self.mapping.events.append(event)
            return True
        return False

    def update_event(self, original_name: str, event: MidiEvent) -> bool:
        for i, e in enumerate(self.mapping.events):
            if e.name == original_name:
                # Preserve messages from original if not provided
                if not event.start_messages:
                    event.start_messages = e.start_messages
                if not event.end_messages:
                    event.end_messages = e.end_messages
                self.mapping.events[i] = event
                return True
        return False

    def delete_event(self, name: str) -> bool:
        original_len = len(self.mapping.events)
        self.mapping.events = [e for e in self.mapping.events if e.name != name]
        return len(self.mapping.events) < original_len

    def rename_duplicates(self) -> int:
        """Auto-rename duplicate events by appending ~1, ~2, etc. Returns count renamed."""
        seen: dict[str, int] = {}
        renamed = 0
        for event in self.mapping.events:
            if event.name in seen:
                seen[event.name] += 1
                event.name = f"{event.name}~{seen[event.name]}"
                renamed += 1
            else:
                seen[event.name] = 0
        return renamed

    # ==========================================================================
    # Diff computation
    # ==========================================================================

    def compute_diff(self) -> dict:
        """Compute diff between original and current mapping."""
        diff = {
            "inputs": {"added": [], "removed": []},
            "outputs": {"added": [], "removed": []},
            "event_types": {"added": [], "removed": []},
            "events": {"added": [], "removed": [], "modified": []},
        }

        # List diffs (Counter-based to detect duplicate additions/removals)
        for key in ["inputs", "outputs", "event_types"]:
            orig = Counter(getattr(self._original, key))
            curr = Counter(getattr(self.mapping, key))
            added = curr - orig
            removed = orig - curr
            diff[key]["added"] = sorted(added.elements())
            diff[key]["removed"] = sorted(removed.elements())

        # Events diff (by name)
        orig_events = {e.name: e for e in self._original.events}
        curr_events = {e.name: e for e in self.mapping.events}

        orig_names = set(orig_events.keys())
        curr_names = set(curr_events.keys())

        diff["events"]["added"] = sorted(curr_names - orig_names)
        diff["events"]["removed"] = sorted(orig_names - curr_names)

        # Check for modified (compare via dict representation)
        for name in orig_names & curr_names:
            if orig_events[name].to_dict() != curr_events[name].to_dict():
                diff["events"]["modified"].append(name)
        diff["events"]["modified"].sort()

        return diff

    def has_changes(self) -> bool:
        """Check if there are any changes from original."""
        diff = self.compute_diff()
        for key in ["inputs", "outputs", "event_types"]:
            if diff[key]["added"] or diff[key]["removed"]:
                return True
        if diff["events"]["added"] or diff["events"]["removed"] or diff["events"]["modified"]:
            return True
        return False


# Singleton instance
editor_state = EditorState()
