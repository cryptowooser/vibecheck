from __future__ import annotations

import asyncio
import contextlib
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

INDEX_HTML = Path(__file__).with_name("index.html")


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.sequence = 0

    async def register(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def unregister(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def force_drop_all(self) -> int:
        dropped = 0
        for ws in list(self.clients):
            with contextlib.suppress(RuntimeError):
                await ws.close(code=1012, reason="manual drop")
            dropped += 1
        return dropped


hub = Hub()


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def make_event() -> dict:
    event_type = hub.sequence % 3
    hub.sequence += 1
    if event_type == 0:
        return {
            "type": "assistant",
            "content": "I am still working on your request.",
            "timestamp": now_iso(),
        }
    if event_type == 1:
        return {
            "type": "tool_call",
            "tool_name": "bash",
            "args": {"command": "npm test"},
            "tool_call_id": f"tc-{hub.sequence:04d}",
            "timestamp": now_iso(),
        }
    return {
        "type": "tool_result",
        "tool_name": "bash",
        "tool_call_id": f"tc-{hub.sequence:04d}",
        "result": {"exit_code": 0, "stdout": "tests passed"},
        "timestamp": now_iso(),
    }


async def event_stream(ws: WebSocket) -> None:
    while True:
        await asyncio.sleep(2)
        try:
            await ws.send_json(make_event())
        except Exception:
            return


async def heartbeat_stream(ws: WebSocket) -> None:
    while True:
        await asyncio.sleep(30)
        try:
            await ws.send_json({"type": "heartbeat", "timestamp": now_iso()})
        except Exception:
            return


async def random_drop_loop() -> None:
    while True:
        await asyncio.sleep(10)
        if not hub.clients:
            continue
        if random.randint(1, 10) != 1:
            continue
        ws = random.choice(list(hub.clients))
        with contextlib.suppress(RuntimeError):
            await ws.close(code=1012, reason="random drop")


@contextlib.asynccontextmanager
async def lifespan(_app) -> AsyncIterator[None]:
    random_drop_task = asyncio.create_task(random_drop_loop())
    try:
        yield
    finally:
        random_drop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await random_drop_task


app = FastAPI(title="websocket-reconnect-prototype", lifespan=lifespan)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.post("/drop")
async def drop_connections() -> JSONResponse:
    dropped = await hub.force_drop_all()
    return JSONResponse({"status": "ok", "dropped": dropped})


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await hub.register(ws)
    sender = asyncio.create_task(event_stream(ws))
    heartbeats = asyncio.create_task(heartbeat_stream(ws))
    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        heartbeats.cancel()
        with contextlib.suppress(Exception):
            await sender
        with contextlib.suppress(Exception):
            await heartbeats
        hub.unregister(ws)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
