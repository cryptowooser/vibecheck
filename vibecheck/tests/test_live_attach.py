from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import BaseModel
import pytest
import time

from vibecheck.app import create_app
from vibecheck.bridge import SessionManager, VibeRuntime


class FakeVibeConfig:
    @classmethod
    def load(cls):
        return cls()


class FakeToolArgs(BaseModel):
    command: str


class FakeUserMessageEvent:
    def __init__(self, content: str, message_id: str) -> None:
        self.content = content
        self.message_id = message_id


class FakeToolCallEvent:
    def __init__(self, tool_name: str, args: FakeToolArgs, tool_call_id: str) -> None:
        self.tool_name = tool_name
        self.args = args
        self.tool_call_id = tool_call_id


class FakeToolResult:
    def __init__(self, output: str) -> None:
        self.output = output

    def model_dump(self, mode: str = "json") -> dict[str, str]:
        _ = mode
        return {"output": self.output}


class FakeToolResultEvent:
    def __init__(self, tool_call_id: str, result: FakeToolResult | None = None, error: str | None = None) -> None:
        self.tool_call_id = tool_call_id
        self.result = result
        self.error = error


class FakeAssistantEvent:
    def __init__(self, content: str, message_id: str) -> None:
        self.content = content
        self.message_id = message_id


class FakeLiveAgentLoop:
    def __init__(self, *_args, **_kwargs) -> None:
        self.session_id = "live-session"
        self.message_observer = None
        self.approval_callback = None
        self.user_input_callback = None

    def set_approval_callback(self, callback) -> None:
        self.approval_callback = callback

    def set_user_input_callback(self, callback) -> None:
        self.user_input_callback = callback

    async def act(self, msg: str):
        yield FakeUserMessageEvent(content=msg, message_id="u-1")
        args = FakeToolArgs(command="echo hello")
        yield FakeToolCallEvent(tool_name="bash", args=args, tool_call_id="tc-live")
        decision, _feedback = await self.approval_callback("bash", args, "tc-live")
        if decision == "yes":
            yield FakeToolResultEvent(tool_call_id="tc-live", result=FakeToolResult("approved"))
        else:
            yield FakeToolResultEvent(tool_call_id="tc-live", error="denied")
        yield FakeAssistantEvent(content="done", message_id="a-1")


@pytest.fixture
def live_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, SessionManager]:
    monkeypatch.setenv("VIBECHECK_PSK", "dev-psk")

    manager = SessionManager(logs_root=tmp_path / "logs")
    runtime = VibeRuntime(
        agent_loop_cls=FakeLiveAgentLoop,
        vibe_config_cls=FakeVibeConfig,
        approval_yes="yes",
        approval_no="no",
        ask_result_cls=None,
        answer_cls=None,
    )
    loop = FakeLiveAgentLoop(FakeVibeConfig.load())
    bridge = manager.attach("live-session")
    bridge.attach_to_loop(loop, runtime)

    import vibecheck.bridge as bridge_module
    import vibecheck.routes.api as api_module
    import vibecheck.ws as ws_module

    monkeypatch.setattr(bridge_module, "session_manager", manager)
    monkeypatch.setattr(api_module, "session_manager", manager)
    monkeypatch.setattr(ws_module, "session_manager", manager)

    ws_module.manager._expected_psk = "dev-psk"
    ws_module.manager.rooms.clear()
    ws_module.manager.socket_to_session.clear()
    manager.set_connection_manager(ws_module.manager)

    app = create_app()
    client = TestClient(app)
    try:
        yield client, manager
    finally:
        client.close()
        ws_module.manager.rooms.clear()
        ws_module.manager.socket_to_session.clear()
        manager.sessions.clear()


def _read_until(websocket, predicate, *, max_messages: int = 20) -> list[dict]:
    seen: list[dict] = []
    for _ in range(max_messages):
        payload = websocket.receive_json()
        seen.append(payload)
        if predicate(seen):
            return seen
    raise AssertionError("expected websocket messages were not observed")


def _wait_until(predicate, *, timeout_seconds: float = 2.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def test_live_attach_flow_with_rest_and_websocket(live_client) -> None:
    client, _manager = live_client
    headers = {"X-PSK": "dev-psk"}

    message_response = client.post(
        "/api/sessions/live-session/message",
        headers=headers,
        json={"content": "trigger tool"},
    )
    assert message_response.status_code == 200

    _wait_until(
        lambda: "tc-live"
        in client.get("/api/sessions/live-session", headers=headers).json()["pending_approval"]
    )

    with client.websocket_connect("/ws/events/live-session?psk=dev-psk") as websocket:
        connected = websocket.receive_json()
        state = websocket.receive_json()
        backlog = _read_until(
            websocket,
            lambda msgs: any(msg.get("type") == "approval_request" for msg in msgs),
        )

    assert connected["type"] == "connected"
    assert state["type"] == "state"
    assert state["state"] in {"idle", "waiting_approval"}
    assert any(msg.get("type") == "tool_call" for msg in backlog)
    assert any(msg.get("type") == "approval_request" for msg in backlog)

    detail = client.get("/api/sessions/live-session", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["attach_mode"] == "live"
    assert detail.json()["controllable"] is True

    approve_response = client.post(
        "/api/sessions/live-session/approve",
        headers=headers,
        json={"call_id": "tc-live", "approved": True},
    )
    assert approve_response.status_code == 200

    _wait_until(
        lambda: (
            client.get("/api/sessions/live-session", headers=headers).json()["pending_approval"] == []
            and any(
                event.get("type") == "approval_resolution"
                for event in client.get("/api/sessions/live-session", headers=headers).json()["backlog"]
            )
        )
    )
