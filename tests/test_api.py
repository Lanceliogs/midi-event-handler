"""Tests for API endpoints."""

import os
import asyncio
from pathlib import Path

# Create event loop before importing app (MidiApp needs it at init time)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from midi_event_handler.core.config.loader import *

test_mapping_path = Path(__file__).parent / "test_mapping.yaml"
load_mapping_yaml(test_mapping_path)

from fastapi.testclient import TestClient
from midi_event_handler.web.app import app
client = TestClient(app)


class TestConfigLoader:
    """Tests for config loading."""
    
    def test_configured_inputs(self):
        assert "InputDevice2" in get_configured_inputs()
    
    def test_event_types(self):
        assert get_event_types() == ["light", "music"]
    
    def test_events_loaded(self):
        events = get_event_list()
        assert len(events) == 3
        assert events[0].chord.notes == [127, 131]


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    def test_get_status(self):
        response = client.get("/meh/api/status")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert "running" in response.json()
    
    def test_get_ports(self):
        response = client.get("/meh/api/ports")
        assert response.status_code == 200
        data = response.json()
        assert "inputs" in data
        assert "outputs" in data
    
    def test_healthz(self):
        response = client.get("/meh/api/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True
        assert "version" in data
        assert "pid" in data


class TestUIEndpoints:
    """Tests for UI endpoints."""
    
    def test_dashboard(self):
        response = client.get("/meh/ui/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_editor(self):
        response = client.get("/meh/ui/editor")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_help(self):
        response = client.get("/meh/ui/help")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_root_redirect(self):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/meh/ui/dashboard" in response.headers["location"]


class TestEditorAPI:
    """Tests for editor-specific endpoints."""
    
    def test_get_mapping(self):
        response = client.get("/meh/ui/editor/api/mapping")
        assert response.status_code == 200
        data = response.json()
        assert "mapping" in data
        assert "dirty" in data
    
    def test_download_mapping(self):
        response = client.get("/meh/ui/editor/api/mapping/download")
        assert response.status_code == 200
        assert "application/x-yaml" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")
    
    def test_input_new_modal(self):
        response = client.get("/meh/ui/editor/input/new")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Port Name" in response.text
    
    def test_output_new_modal(self):
        response = client.get("/meh/ui/editor/output/new")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_event_type_new_modal(self):
        response = client.get("/meh/ui/editor/event-type/new")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_event_new_modal(self):
        response = client.get("/meh/ui/editor/event/new")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_resolve_port_input(self):
        response = client.get("/meh/ui/editor/resolve-port?name=loop&type=input")
        assert response.status_code == 200
    
    def test_resolve_port_empty(self):
        response = client.get("/meh/ui/editor/resolve-port?name=&type=input")
        assert response.status_code == 200
        assert response.text == ""

