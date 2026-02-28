from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from vibecheck.auth import is_psk_valid, load_psk


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        connections = self.active_connections.setdefault(session_id, set())
        connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        empty_sessions: list[str] = []
        for session_id, connections in self.active_connections.items():
            if websocket in connections:
                connections.remove(websocket)
            if not connections:
                empty_sessions.append(session_id)

        for session_id in empty_sessions:
            self.active_connections.pop(session_id, None)

    async def broadcast(self, session_id: str, event: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self.active_connections.get(session_id, set())):
            try:
                await websocket.send_json(event)
            except RuntimeError:
                stale.append(websocket)

        for websocket in stale:
            await self.disconnect(websocket)


async def _send_heartbeats(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(30)
        try:
            await websocket.send_json(
                {
                    "type": "heartbeat",
                    "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                }
            )
        except Exception:
            return


router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/events/{session_id}")
async def events(websocket: WebSocket, session_id: str) -> None:
    expected_psk = load_psk()
    provided_psk = websocket.query_params.get("psk")
    if not is_psk_valid(provided_psk, expected_psk):
        await websocket.close(code=4401)
        return

    await manager.connect(session_id, websocket)
    await websocket.send_json({"type": "connected", "session_id": session_id})
    heartbeat_task = asyncio.create_task(_send_heartbeats(websocket))

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(Exception):
            await heartbeat_task
        await manager.disconnect(websocket)
