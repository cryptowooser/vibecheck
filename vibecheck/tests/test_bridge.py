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


class FakeApprovalResponse:
    YES = "yes"
    NO = "no"


class FakeToolArgs:
    def __init__(self, command: str) -> None:
        self.command = command

    def model_dump(self, mode: str = "json") -> dict[str, str]:
        _ = mode
        return {"command": self.command}


class FakeChoice:
    def __init__(self, label: str) -> None:
        self.label = label


class FakeQuestion:
    def __init__(self, question: str, options: list[FakeChoice]) -> None:
        self.question = question
        self.options = options


class FakeAskUserQuestionArgs:
    def __init__(self) -> None:
        self.questions = [
            FakeQuestion("Continue?", [FakeChoice("yes"), FakeChoice("no")]),
        ]


class FakeAnswer:
    def __init__(self, question: str, answer: str, is_other: bool = False) -> None:
        self.question = question
        self.answer = answer
        self.is_other = is_other


class FakeAskUserQuestionResult:
    def __init__(self, answers: list[FakeAnswer], cancelled: bool = False) -> None:
        self.answers = answers
        self.cancelled = cancelled


class FakeToolResult:
    def __init__(self, answer: str, command: str) -> None:
        self.answer = answer
        self.command = command

    def model_dump(self, mode: str = "json") -> dict[str, str]:
        _ = mode
        return {"answer": self.answer, "command": self.command}


class FakeObservedMessage:
    def __init__(self, role: str, content: str, message_id: str) -> None:
        self.role = role
        self.content = content
        self.message_id = message_id


class FakeUserMessageEvent:
    def __init__(self, content: str, message_id: str) -> None:
        self.content = content
        self.message_id = message_id


class FakeToolCallEvent:
    def __init__(self, tool_name: str, args: FakeToolArgs, tool_call_id: str) -> None:
        self.tool_name = tool_name
        self.args = args
        self.tool_call_id = tool_call_id


class FakeToolResultEvent:
    def __init__(self, tool_call_id: str, result: FakeToolResult | None = None, error: str | None = None) -> None:
        self.tool_call_id = tool_call_id
        self.result = result
        self.error = error


class FakeAssistantEvent:
    def __init__(self, content: str, message_id: str | None = None) -> None:
        self.content = content
        self.message_id = message_id


class FakeVibeConfig:
    @classmethod
    def load(cls):
        return cls()


class FakeAgentLoop:
    def __init__(self, _config, message_observer=None, enable_streaming: bool = False) -> None:
        _ = enable_streaming
        self.message_observer = message_observer
        self.approval_callback = None
        self.user_input_callback = None

    def set_approval_callback(self, callback) -> None:
        self.approval_callback = callback

    def set_user_input_callback(self, callback) -> None:
        self.user_input_callback = callback

    async def act(self, msg: str):
        yield FakeUserMessageEvent(content=msg, message_id="m-user-1")
        if self.message_observer:
            self.message_observer(
                FakeObservedMessage(
                    role="assistant",
                    content="observer-ping",
                    message_id="m-observer-1",
                )
            )

        args = FakeToolArgs("ls -la")
        yield FakeToolCallEvent(tool_name="bash", args=args, tool_call_id="tc-1")
        approval, _feedback = await self.approval_callback("bash", args, "tc-1")
        if approval == FakeApprovalResponse.NO:
            yield FakeToolResultEvent(tool_call_id="tc-1", error="denied")
            return

        response = await self.user_input_callback(FakeAskUserQuestionArgs())
        answer = response.answers[0].answer
        yield FakeToolResultEvent(
            tool_call_id="tc-1",
            result=FakeToolResult(answer=answer, command=args.command),
        )
        yield FakeAssistantEvent(content=f"done {answer}", message_id="m-assistant-1")


async def _wait_until(predicate, *, attempts: int = 100) -> None:
    for _ in range(attempts):
        if predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition was not met in time")


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


@pytest.mark.asyncio
async def test_start_session_wires_agent_loop_callbacks_and_processes_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibecheck.bridge as bridge_module

    runtime = bridge_module.VibeRuntime(
        agent_loop_cls=FakeAgentLoop,
        vibe_config_cls=FakeVibeConfig,
        approval_yes=FakeApprovalResponse.YES,
        approval_no=FakeApprovalResponse.NO,
        ask_result_cls=FakeAskUserQuestionResult,
        answer_cls=FakeAnswer,
    )
    monkeypatch.setattr(bridge_module, "load_vibe_runtime", lambda: runtime)

    manager = RecordingConnectionManager()
    bridge = SessionBridge("live-session", connection_manager=manager)

    run_task = asyncio.create_task(bridge.start_session("hello"))
    await _wait_until(lambda: "tc-1" in bridge.pending_approval)
    assert bridge.state == "waiting_approval"
    assert bridge.resolve_approval("tc-1", approved=True)

    await _wait_until(lambda: len(bridge.pending_input) == 1)
    request_id = next(iter(bridge.pending_input.keys()))
    assert bridge.resolve_input(request_id=request_id, response="yes")

    await run_task
    assert bridge.state == "idle"

    event_types = [event["type"] for _, event in manager.events]
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert any(
        event["type"] == "assistant" and "done yes" in event["content"]
        for _, event in manager.events
    )

    bridge.stop()


@pytest.mark.asyncio
async def test_inject_message_lazily_starts_agent_loop_when_runtime_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibecheck.bridge as bridge_module

    runtime = bridge_module.VibeRuntime(
        agent_loop_cls=FakeAgentLoop,
        vibe_config_cls=FakeVibeConfig,
        approval_yes=FakeApprovalResponse.YES,
        approval_no=FakeApprovalResponse.NO,
        ask_result_cls=FakeAskUserQuestionResult,
        answer_cls=FakeAnswer,
    )
    monkeypatch.setattr(bridge_module, "load_vibe_runtime", lambda: runtime)

    manager = RecordingConnectionManager()
    bridge = SessionBridge("lazy-live", connection_manager=manager)

    bridge.inject_message("from-api")
    await _wait_until(lambda: "tc-1" in bridge.pending_approval)
    assert bridge.resolve_approval("tc-1", approved=True)

    await _wait_until(lambda: len(bridge.pending_input) == 1)
    request_id = next(iter(bridge.pending_input.keys()))
    assert bridge.resolve_input(request_id=request_id, response="yes")
    await _wait_until(lambda: bridge.state == "idle")

    event_types = [event["type"] for _, event in manager.events]
    assert bridge.messages_to_inject[-1] == "from-api"
    assert "tool_call" in event_types
    assert "tool_result" in event_types

    bridge.stop()


@pytest.mark.asyncio
async def test_edited_args_are_applied_to_tool_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibecheck.bridge as bridge_module

    runtime = bridge_module.VibeRuntime(
        agent_loop_cls=FakeAgentLoop,
        vibe_config_cls=FakeVibeConfig,
        approval_yes=FakeApprovalResponse.YES,
        approval_no=FakeApprovalResponse.NO,
        ask_result_cls=FakeAskUserQuestionResult,
        answer_cls=FakeAnswer,
    )
    monkeypatch.setattr(bridge_module, "load_vibe_runtime", lambda: runtime)

    manager = RecordingConnectionManager()
    bridge = SessionBridge("edit-args", connection_manager=manager)

    run_task = asyncio.create_task(bridge.start_session("hello"))
    await _wait_until(lambda: "tc-1" in bridge.pending_approval)
    assert bridge.resolve_approval("tc-1", approved=True, edited_args={"command": "pwd"})

    await _wait_until(lambda: len(bridge.pending_input) == 1)
    request_id = next(iter(bridge.pending_input.keys()))
    assert bridge.resolve_input(request_id=request_id, response="yes")

    await run_task
    tool_results = [event for _, event in manager.events if event["type"] == "tool_result"]
    assert any('"command": "pwd"' in event["output"] for event in tool_results)

    bridge.stop()
