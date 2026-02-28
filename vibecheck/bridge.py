from __future__ import annotations

import asyncio
import json
from collections import deque
from pathlib import Path
from typing import Literal

from vibecheck.events import (
    ApprovalRequestEvent,
    ApprovalResolutionEvent,
    Event,
    InputRequestEvent,
    InputResolutionEvent,
    StateChangeEvent,
    UserMessageEvent,
)

BridgeState = Literal["idle", "running", "waiting_approval", "waiting_input", "disconnected"]


class SessionBridge:
    def __init__(self, session_id: str, connection_manager=None) -> None:
        self.session_id = session_id
        self.state: BridgeState = "idle"
        self.pending_approval: dict[str, asyncio.Future] = {}
        self.pending_input: dict[str, asyncio.Future] = {}
        self.pending_approval_context: dict[str, dict[str, object]] = {}
        self.pending_input_context: dict[str, dict[str, object]] = {}
        self.event_backlog: deque[Event] = deque(maxlen=50)
        self.connection_manager = connection_manager
        self.messages_to_inject: list[str] = []

    async def _broadcast(self, event: Event) -> None:
        self.add_event(event)
        if self.connection_manager:
            await self.connection_manager.broadcast(self.session_id, event)

    def _broadcast_background(self, event: Event) -> None:
        self.add_event(event)
        if not self.connection_manager:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.connection_manager.broadcast(self.session_id, event))

    def add_event(self, event: Event) -> None:
        self.event_backlog.append(event)

    def backlog(self, limit: int = 50) -> list[Event]:
        return list(self.event_backlog)[-limit:]

    async def request_approval(self, call_id: str, tool_name: str, args: dict) -> dict:
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self.pending_approval[call_id] = future
        self.pending_approval_context[call_id] = {"tool_name": tool_name, "args": args}
        self.state = "waiting_approval"
        await self._broadcast(ApprovalRequestEvent(call_id=call_id, tool_name=tool_name, args=args))
        result = await future
        return result

    def resolve_approval(self, call_id: str, approved: bool, edited_args: dict | None = None) -> bool:
        future = self.pending_approval.pop(call_id, None)
        self.pending_approval_context.pop(call_id, None)
        if future is None:
            return False
        if not future.done():
            future.set_result({"approved": approved, "edited_args": edited_args})
        self.state = "running"
        self._broadcast_background(
            ApprovalResolutionEvent(call_id=call_id, approved=approved, edited_args=edited_args)
        )
        return True

    async def request_input(self, request_id: str, question: str, options: list[str] | None = None) -> str:
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self.pending_input[request_id] = future
        self.pending_input_context[request_id] = {
            "question": question,
            "options": list(options or []),
        }
        self.state = "waiting_input"
        await self._broadcast(
            InputRequestEvent(request_id=request_id, question=question, options=options or [])
        )
        result = await future
        return result

    def resolve_input(self, request_id: str, response: str) -> bool:
        future = self.pending_input.pop(request_id, None)
        self.pending_input_context.pop(request_id, None)
        if future is None:
            return False
        if not future.done():
            future.set_result(response)
        self.state = "running"
        self._broadcast_background(InputResolutionEvent(request_id=request_id, response=response))
        return True

    def inject_message(self, content: str) -> None:
        self.messages_to_inject.append(content)
        self.state = "running"
        self._broadcast_background(UserMessageEvent(content=content))

    def state_payload(self) -> dict:
        payload: dict[str, object] = {"state": self.state}
        if self.pending_approval:
            call_id = next(iter(self.pending_approval.keys()))
            context = self.pending_approval_context.get(call_id, {})
            pending = {"call_id": call_id}
            if "tool_name" in context:
                pending["tool_name"] = context["tool_name"]
            if "args" in context:
                pending["args"] = context["args"]
            payload["pending_approval"] = pending
        if self.pending_input:
            request_id = next(iter(self.pending_input.keys()))
            context = self.pending_input_context.get(request_id, {})
            pending = {"request_id": request_id}
            if "question" in context:
                pending["question"] = context["question"]
            if "options" in context:
                pending["options"] = context["options"]
            payload["pending_input"] = pending
        return payload


class SessionManager:
    def __init__(self, logs_root: Path | None = None, connection_manager=None) -> None:
        self.logs_root = logs_root or (Path.home() / ".vibe" / "logs" / "session")
        self.connection_manager = connection_manager
        self.sessions: dict[str, SessionBridge] = {}

    def set_connection_manager(self, connection_manager) -> None:
        self.connection_manager = connection_manager
        for bridge in self.sessions.values():
            bridge.connection_manager = connection_manager

    def discover(self) -> list[dict]:
        discovered: list[dict] = []
        if not self.logs_root.exists():
            return discovered

        for session_dir in sorted(self.logs_root.iterdir()):
            if not session_dir.is_dir():
                continue
            meta_file = session_dir / "meta.json"
            if not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            session_id = meta.get("session_id") or session_dir.name
            discovered.append(
                {
                    "id": session_id,
                    "started_at": meta.get("start_time"),
                    "last_activity": meta.get("end_time") or meta.get("start_time"),
                    "message_count": self._message_count(session_dir),
                    "status": self.sessions.get(session_id).state if session_id in self.sessions else "disconnected",
                }
            )
        return discovered

    def _message_count(self, session_dir: Path) -> int:
        messages_file = session_dir / "messages.jsonl"
        if not messages_file.exists():
            return 0
        return sum(1 for _ in messages_file.open("r", encoding="utf-8"))

    def attach(self, session_id: str) -> SessionBridge:
        if session_id in self.sessions:
            return self.sessions[session_id]
        bridge = SessionBridge(session_id=session_id, connection_manager=self.connection_manager)
        self.sessions[session_id] = bridge
        return bridge

    def detach(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def get(self, session_id: str) -> SessionBridge:
        bridge = self.sessions.get(session_id)
        if bridge is None:
            raise KeyError(session_id)
        return bridge

    def has_known_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            return True
        return any(item["id"] == session_id for item in self.discover())

    def list(self) -> list[dict]:
        discovered = {item["id"]: item for item in self.discover()}
        for session_id, bridge in self.sessions.items():
            if session_id not in discovered:
                discovered[session_id] = {
                    "id": session_id,
                    "started_at": None,
                    "last_activity": None,
                    "message_count": len(bridge.event_backlog),
                    "status": bridge.state,
                }
            else:
                discovered[session_id]["status"] = bridge.state
        return list(discovered.values())

    def fleet_status(self) -> dict[str, int]:
        listed = self.list()
        running = 0
        waiting = 0
        idle = 0
        for item in listed:
            status = item["status"]
            if status == "running":
                running += 1
            elif status in {"waiting_approval", "waiting_input"}:
                waiting += 1
            elif status == "idle":
                idle += 1
        return {"total": len(listed), "running": running, "waiting": waiting, "idle": idle}

    def session_detail(self, session_id: str) -> dict:
        bridge = self.sessions.get(session_id)
        if bridge is not None:
            return {
                "id": bridge.session_id,
                "state": bridge.state,
                "pending_approval": list(bridge.pending_approval.keys()),
                "pending_input": list(bridge.pending_input.keys()),
                "backlog": [event.model_dump(mode="json") for event in bridge.backlog()],
            }

        discovered = next((item for item in self.discover() if item["id"] == session_id), None)
        if discovered is None:
            raise KeyError(session_id)

        return {
            "id": session_id,
            "state": "disconnected",
            "pending_approval": [],
            "pending_input": [],
            "backlog": [],
            "started_at": discovered["started_at"],
            "last_activity": discovered["last_activity"],
            "message_count": discovered["message_count"],
        }


session_manager = SessionManager()
