from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from vibecheck.bridge import SessionBridge, SessionManager
from vibecheck.events import AssistantEvent


class RecordingConnectionManager:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def broadcast(self, session_id: str, event) -> None:
        payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else dict(event)
        self.events.append((session_id, payload))


@pytest.mark.asyncio
async def test_session_bridge_approval_flow_broadcasts_and_resolves() -> None:
    manager = RecordingConnectionManager()
    bridge = SessionBridge("s1", connection_manager=manager)

    task = asyncio.create_task(bridge.request_approval("tc-1", "bash", {"command": "npm test"}))
    await asyncio.sleep(0)

    assert bridge.state == "waiting_approval"
    assert bridge.resolve_approval("tc-1", approved=True, edited_args={"command": "npm test -- -u"})
    result = await task

    assert result["approved"] is True
    assert result["edited_args"] == {"command": "npm test -- -u"}
    assert bridge.state == "running"
    assert any(event["type"] == "approval_request" for _, event in manager.events)
    assert any(event["type"] == "approval_resolution" for _, event in manager.events)


@pytest.mark.asyncio
async def test_session_bridge_input_flow_resolves() -> None:
    bridge = SessionBridge("s2")

    task = asyncio.create_task(bridge.request_input("req-1", "continue?", ["yes", "no"]))
    await asyncio.sleep(0)

    assert bridge.state == "waiting_input"
    assert bridge.resolve_input("req-1", "yes")
    assert await task == "yes"
    assert bridge.state == "running"


def test_session_bridge_backlog_is_capped() -> None:
    bridge = SessionBridge("s3")
    for i in range(60):
        bridge.add_event(AssistantEvent(content=f"message-{i}"))

    backlog = bridge.backlog()
    assert len(backlog) == 50
    assert backlog[0].content == "message-10"
    assert backlog[-1].content == "message-59"


def test_session_manager_discover_attach_detach_and_fleet_status(tmp_path: Path) -> None:
    logs_root = tmp_path / "logs" / "session"
    session_a = logs_root / "session_a"
    session_b = logs_root / "session_b"
    session_a.mkdir(parents=True)
    session_b.mkdir(parents=True)

    (session_a / "meta.json").write_text(
        json.dumps({"session_id": "a", "start_time": "2026-02-28T00:00:00Z"}),
        encoding="utf-8",
    )
    (session_b / "meta.json").write_text(
        json.dumps({"session_id": "b", "start_time": "2026-02-28T01:00:00Z"}),
        encoding="utf-8",
    )

    manager = SessionManager(logs_root=logs_root)
    discovered = manager.discover()
    assert {item["id"] for item in discovered} == {"a", "b"}

    bridge_a = manager.attach("a")
    bridge_a.state = "running"
    bridge_b = manager.attach("b")
    bridge_b.state = "waiting_input"

    summary = manager.fleet_status()
    assert summary["total"] == 2
    assert summary["running"] == 1
    assert summary["waiting"] == 1
    assert summary["idle"] == 0

    manager.detach("a")
    assert "a" not in manager.sessions


def test_session_manager_get_raises_for_unknown_session() -> None:
    manager = SessionManager(logs_root=Path("/tmp/does-not-matter"))
    with pytest.raises(KeyError):
        manager.get("missing")
