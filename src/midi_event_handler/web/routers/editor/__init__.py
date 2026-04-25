"""
Editor UI routes: /meh/ui/editor/*

Split into subrouters for maintainability:
- main.py: Main page and partials
- mapping.py: Mapping API (save, download)
- inputs.py: Input port CRUD
- outputs.py: Output port CRUD
- event_types.py: Event type CRUD
- events.py: Event CRUD, PAD testing, recording
"""

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from midi_event_handler.core.app import MidiApp

from . import common
from .main import router as main_router
from .mapping import router as mapping_router
from .inputs import router as inputs_router
from .outputs import router as outputs_router
from .event_types import router as event_types_router
from .events import router as events_router

router = APIRouter(prefix="/meh/ui/editor", tags=["editor"])

# Include all subrouters
router.include_router(main_router)
router.include_router(mapping_router)
router.include_router(inputs_router)
router.include_router(outputs_router)
router.include_router(event_types_router)
router.include_router(events_router)


def configure(templates: Jinja2Templates, midiapp: MidiApp):
    """Configure shared dependencies for all editor routers."""
    common.configure(templates, midiapp)
