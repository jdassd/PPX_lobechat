from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class Room:
    map_id: str
    version: int = 0
    connections: dict[str, WebSocket] = field(default_factory=dict)


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def connect(self, map_id: str, client_id: str, ws: WebSocket) -> Room:
        await ws.accept()
        async with self._lock:
            if map_id not in self.rooms:
                self.rooms[map_id] = Room(map_id=map_id)
            room = self.rooms[map_id]
            room.connections[client_id] = ws
        return room

    async def disconnect(self, map_id: str, client_id: str):
        async with self._lock:
            room = self.rooms.get(map_id)
            if room:
                room.connections.pop(client_id, None)
                if not room.connections:
                    del self.rooms[map_id]

    async def broadcast(self, room: Room, message: dict, exclude_client: str | None = None):
        disconnected = []
        for cid, ws in room.connections.items():
            if cid == exclude_client:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(cid)
        for cid in disconnected:
            room.connections.pop(cid, None)

    def get_room(self, map_id: str) -> Room | None:
        return self.rooms.get(map_id)

    def next_version(self, room: Room) -> int:
        room.version += 1
        return room.version


manager = ConnectionManager()
