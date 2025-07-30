import os
from pathlib import Path
from midi_event_handler.core.config.loader import *

test_mapping_path = Path(__file__).parent / "test_mapping.yaml"
load_mapping_yaml(test_mapping_path) # test load from env 

from fastapi.testclient import TestClient
from midi_event_handler.web.app import app
client = TestClient(app)

def test_mapping():
    assert "InputDevice2" in get_configured_inputs()
    assert get_event_types() == ["light", "music"]
    events = get_event_list()
    assert len(events) == 3
    assert events[0].chord.notes == [127, 131]

def test_get_status():
    response = client.get("/status")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

