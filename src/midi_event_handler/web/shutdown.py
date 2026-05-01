from fastapi import APIRouter, Request, HTTPException
import requests

from midi_event_handler.tools.connection import ConnectionManager

import logging

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/meh/api/shutdown")
async def shutdown(request: Request):
    client_host = request.client.host
    if client_host != "127.0.0.1" and client_host != "::1":
        raise HTTPException(status_code=403, detail="Forbidden: shutdown only allowed from localhost")

    log.info(f"🛑 Shutdown requested by {client_host}")
    manager = ConnectionManager("meh-app")
    await manager.shutdown()

    from midi_event_handler.main import server

    if server:
        server.should_exit = True
        log.info("✅ server.should_exit set to True")

    return {"message": "Shutting down..."}


def request_shutdown(port: int) -> bool:
    """Send shutdown request to the app. Returns True if accepted."""
    url = f"http://127.0.0.1:{port}/meh/api/shutdown"
    try:
        log.info(f"🛑 Sending shutdown request to {url}")
        response = requests.post(url, timeout=5)
        if response.status_code == 200:
            log.info("✅ Shutdown request accepted by the app")
            return True
        else:
            log.warning(f"⚠️ Shutdown request returned status {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException:
        log.exception("❌ Failed to send shutdown request")
        return False
