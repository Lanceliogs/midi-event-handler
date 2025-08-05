import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from asyncio import Queue

import logging
log = logging.getLogger(__name__)

class ConnectionManager():

    _instances = {}

    def __new__(cls, key: str):
        if key in cls._instances:
            return cls._instances[key]
        cls._instances[key] = super().__new__(cls) 
        return cls._instances[key]

    def __init__(self, key: str):
        if hasattr(self, "initialized"):
            return
        self.initialized = True
        self._name = key
        self._websockets: set[WebSocket] = set()
        self._task: asyncio.Task | None = None
        self._queue = Queue()

    @property
    def connections_num(self):
        return len(self._websockets)
    
    def notify_nowait(self, item):
        if not item:
            return
        self._queue.put_nowait(item)

    async def notify(self, item):
        if not item:
            return
        await self._queue.put(item)

    async def manage_until_death(self, ws: WebSocket):
        log.info(f"Connected: {self._name}")
        await ws.accept()
        self._websockets.add(ws)

        if self._task is None or self._task.done():
            asyncio.create_task(self._manage_forever())

        while ws in self._websockets:
            try:
                await ws.send_json({"alive": True})
                await asyncio.sleep(3)
            except (WebSocketDisconnect, asyncio.CancelledError):
                self._websockets.discard(ws)
        
        log.info(f"Disconnected: {self._name}")

    
    async def _manage_forever(self):
        log.info(f"Starting task ({self._name})")
        while self._websockets:
            item = await self._queue.get()
            if not item:
                break # None injection break the loop
            websockets = self._websockets.copy()
            for ws in websockets:
                try:
                    await ws.send_json(item)
                except WebSocketDisconnect:
                    self._websockets.discard(ws)
                    log.info(f"Connection removed from manager: {self._name}")
        
    
    async def shutdown(self):
        log.info(f"🔻 Shutting down connection manager: {self._name}")

        await self._queue.put(None) # None injection to break the loop
        if self._task and not self._task.done():
            await asyncio.gather(self._task, return_exceptions=True)
        log.info("✅ Manager task cancelled cleanly")

        # Close all websockets
        websockets = self._websockets.copy()
        for ws in websockets:
            try:
                await ws.close()
            except Exception:
                pass
        self._websockets.clear()
