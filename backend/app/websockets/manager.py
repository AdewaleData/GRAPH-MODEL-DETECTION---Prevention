"""WebSocket connection manager — async broadcast to channel subscribers."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    DSA: hash map channel -> set of WebSocket connections.
    Async event loop schedules broadcast tasks (streaming pipeline).
    """

    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active[channel].add(websocket)
        logger.info("WS connect channel=%s total=%d", channel, len(self.active[channel]))

    async def disconnect(self, channel: str, websocket: WebSocket) -> None:
        async with self._lock:
            self.active[channel].discard(websocket)
        logger.info("WS disconnect channel=%s", channel)

    async def broadcast(self, channel: str, message: dict) -> None:
        payload = json.dumps(message, default=str)
        async with self._lock:
            sockets = list(self.active.get(channel, set()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(channel, ws)


ws_manager = ConnectionManager()
