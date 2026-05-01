import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from midi_event_handler.core.events.models import MidiEvent

import logging

log = logging.getLogger(__name__)


# =============================================================================
# Path Constants
# =============================================================================

RUNTIME_PATH = Path(".runtime")
RUNTIME_MAPPING_PATH = RUNTIME_PATH / "mapping.yaml"
WHATSNEW_PATH = RUNTIME_PATH / "whatsnew.md"
LOG_FILE_PATH = RUNTIME_PATH / "app.log"
VERSION_PATH = Path("version.txt")


def safe_runtime_path() -> Path:
    """Ensure runtime directory exists and return it."""
    RUNTIME_PATH.mkdir(exist_ok=True)
    return RUNTIME_PATH


def is_embedded() -> bool:
    """Check if running from embedded release (vs development mode)."""
    cwd = Path.cwd()
    python_dir = cwd / "python"
    return python_dir.exists() and (python_dir / "python.exe").exists()


def get_current_version(with_commit: bool = True) -> str:
    """Get current app version from version.txt or package metadata."""
    if with_commit and VERSION_PATH.exists():
        return VERSION_PATH.read_text().strip()
    from importlib.metadata import version

    try:
        return version("midi-event-handler")
    except Exception:
        return "0.0.0"


# =============================================================================
# App Config (config.yaml) - loaded once at startup
# =============================================================================


@dataclass
class AppConfig:
    """Application configuration from config.yaml."""

    _data: Dict[str, Any] = field(default_factory=dict)

    def load(self, path: Path = Path("config.yaml")) -> None:
        """Load config from YAML file."""
        with path.open("r") as f:
            self._data = yaml.safe_load(f) or {}

    @property
    def app(self) -> dict:
        return self._data.get("app", {})

    @property
    def updates(self) -> dict:
        return self._data.get("updates", {})

    @property
    def logging(self) -> dict:
        """Get logging config, ensuring file handler is always present."""
        config = self._data.get("logging", {}).copy()

        safe_runtime_path()

        handlers = config.setdefault("handlers", {})
        if "file" not in handlers:
            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(LOG_FILE_PATH),
                "maxBytes": 1048576,
                "backupCount": 3,
                "formatter": "default",
                "level": "DEBUG",
            }

        root = config.setdefault("root", {})
        root_handlers = root.setdefault("handlers", [])
        if "file" not in root_handlers:
            root_handlers.append("file")

        return config


# Singleton instance - loaded at import time
app_config = AppConfig()
app_config.load()


# Backward-compatible accessors
def get_app_config() -> dict:
    return app_config.app


def get_updates_config() -> dict:
    return app_config.updates


def get_logging_config() -> dict:
    return app_config.logging


def default_app_conf() -> dict:
    return {"host": "127.0.0.1", "port": 8000}


# =============================================================================
# Mapping Config (mapping.yaml) - loaded/reloaded at runtime
# =============================================================================


@dataclass
class MappingConfig:
    """Mapping configuration from mapping.yaml."""

    _data: Dict[str, Any] = field(default_factory=dict)

    def load(self, path: Optional[Path] = None) -> None:
        """Load mapping from YAML file."""
        path = path or RUNTIME_MAPPING_PATH
        if not path.exists():
            raise FileNotFoundError(f"Mapping file not found: {path}")

        log.info("Loading mapping file: %s", path)
        with path.open("r") as f:
            self._data = yaml.safe_load(f) or {}

    @property
    def inputs(self) -> List[str]:
        return self._data.get("inputs", [])

    @property
    def outputs(self) -> List[str]:
        return self._data.get("outputs", [])

    @property
    def event_types(self) -> List[str]:
        return self._data.get("event_types", [])

    @property
    def events(self) -> List[MidiEvent]:
        result = []
        for e in self._data.get("events", []):
            try:
                result.append(MidiEvent.from_dict(e))
            except Exception:
                log.error("Event cannot be loaded: %s", e)
        return result


# Singleton instance
mapping_config = MappingConfig()


# Backward-compatible functions
def load_mapping_yaml(path: Optional[Path] = None) -> None:
    mapping_config.load(path)


def get_configured_inputs() -> List[str]:
    return mapping_config.inputs


def get_configured_outputs() -> List[str]:
    return mapping_config.outputs


def get_event_types() -> List[str]:
    return mapping_config.event_types


def get_event_list() -> List[MidiEvent]:
    return mapping_config.events
