import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            if len(self._connections[user_id]) >= 5:
                oldest = self._connections[user_id].pop(0)
                try:
                    await oldest.close()
                except Exception:
                    pass
            self._connections[user_id].append(websocket)
        logger.info("ws.connected", user_id=user_id)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id] = [
                    ws for ws in self._connections[user_id] if ws is not websocket
                ]
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info("ws.disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, message: dict):
        async with self._lock:
            connections = self._connections.get(user_id, [])
        data = json.dumps(message, default=str)
        disconnected = []
        for ws in connections:
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.append(ws)
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    if user_id in self._connections:
                        try:
                            self._connections[user_id].remove(ws)
                        except ValueError:
                            pass

    async def broadcast(self, message: dict):
        data = json.dumps(message, default=str)
        async with self._lock:
            all_connections = []
            for conns in self._connections.values():
                all_connections.extend(conns)
        for ws in all_connections:
            try:
                await ws.send_text(data)
            except Exception:
                pass

    def get_connection_count(self, user_id: str) -> int:
        return len(self._connections.get(user_id, []))


ws_manager = ConnectionManager()
