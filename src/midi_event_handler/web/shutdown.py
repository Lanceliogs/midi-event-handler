from fastapi import APIRouter, Request, HTTPException
import asyncio
import requests

from midi_event_handler.tools.connection import ConnectionManager

import logging
log = logging.getLogger(__name__)

router = APIRouter()

@router.post("/meh.api/shutdown")
async def shutdown(request: Request):
    client_host = request.client.host
    if client_host != "127.0.0.1" and client_host != "::1":
        raise HTTPException(status_code=403, detail="Forbidden: shutdown only allowed from localhost")

    log.info(f"🛑 Shutdown requested by {client_host}")
    manager = ConnectionManager("meh-app")
    await manager.shutdown()

    asyncio.get_event_loop().call_soon(lambda: asyncio.create_task(exit_gracefully()))
    return {"message": "Shutting down..."}

async def exit_gracefully():
    try:
        await asyncio.sleep(0.5)
        raise SystemExit("Graceful shutdown triggered by /shutdown")
    except SystemExit:
        raise

# --- This is what you call from the launcher ---------------------------------------------------- 
def request_shutdown(port: int):
    url = f"http://127.0.0.1:{port}/meh.api/shutdown"
    try:
        log.info(f"🛑 Sending shutdown request to {url}")
        response = requests.post(url, timeout=5)
        if response.status_code == 200:
            log.info("✅ Shutdown request accepted by the app")
        else:
            log.warning(f"⚠️ Shutdown request returned status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException:
        log.exception(f"❌ Failed to send shutdown request")
