import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from asyncio import Queue

from midi_event_handler.tools import logtools

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
        self._queue.put_nowait(item)

    async def notify(self, item):
        await self._queue.put(item)

    async def manage_until_death(self, ws: WebSocket):
        log = logtools.get_logger()
        log.info(f"Connection added to manager: {self._name}")
        await ws.accept()
        self._websockets.add(ws)

        if self._task is None or self._task.done():
            asyncio.create_task(self._manage_forever())

        while ws in self._websockets:
            try:
                await ws.send_json({"alive": True})
                await asyncio.sleep(3)
            except WebSocketDisconnect:
                self._websockets.discard(ws)
                log.info(f"Connection removed from manager: {self._name}")
    
    async def _manage_forever(self):
        log = logtools.get_logger()
        log.info(f"Starting task ({self._name})")
        while self._websockets:
            item = await self._queue.get()
            websockets = self._websockets.copy()
            for ws in websockets:
                try:
                    await ws.send_json(item)
                except WebSocketDisconnect:
                    self._websockets.discard(ws)
                    log.info(f"Connection removed from manager: {self._name}")
        
                    