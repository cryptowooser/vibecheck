from __future__ import annotations

import asyncio
from dataclasses import dataclass
import inspect
from importlib import import_module
import json
from collections import deque
from pathlib import Path
import sys
from typing import Any, Callable, Literal
from uuid import uuid4

from vibecheck.events import (
    ApprovalRequestEvent,
    ApprovalResolutionEvent,
    AssistantEvent,
    Event,
    InputRequestEvent,
    InputResolutionEvent,
    StateChangeEvent,
    ToolCallEvent,
    ToolResultEvent,
    UserMessageEvent,
)

BridgeState = Literal["idle", "running", "waiting_approval", "waiting_input", "disconnected"]
AttachMode = Literal["live", "replay", "observe_only", "managed"]
EventListener = Callable[[Event], object]


@dataclass(frozen=True, slots=True)
class VibeRuntime:
    agent_loop_cls: type
    vibe_config_cls: type
    approval_yes: object
    approval_no: object
    ask_result_cls: type | None
    answer_cls: type | None


def _import_vibe_module(module_name: str):
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parent.parent
        fallback = repo_root / "reference" / "mistral-vibe"
        fallback_str = str(fallback)
        if fallback.exists() and fallback_str not in sys.path:
            sys.path.append(fallback_str)
        return import_module(module_name)


def load_vibe_runtime() -> VibeRuntime:
    try:
        agent_loop_module = _import_vibe_module("vibe.core.agent_loop")
        config_module = _import_vibe_module("vibe.core.config")
        types_module = _import_vibe_module("vibe.core.types")
        ask_module = _import_vibe_module("vibe.core.tools.builtins.ask_user_question")
    except Exception as exc:  # pragma: no cover - exercised in integration envs
        raise RuntimeError(
            "Mistral Vibe runtime is not available. Install `vibe` or provide "
            "`reference/mistral-vibe` in this workspace."
        ) from exc

    return VibeRuntime(
        agent_loop_cls=agent_loop_module.AgentLoop,
        vibe_config_cls=config_module.VibeConfig,
        approval_yes=types_module.ApprovalResponse.YES,
        approval_no=types_module.ApprovalResponse.NO,
        ask_result_cls=getattr(ask_module, "AskUserQuestionResult", None),
        answer_cls=getattr(ask_module, "Answer", None),
    )


class SessionBridge:
    def __init__(
        self,
        session_id: str,
        connection_manager=None,
        attach_mode: AttachMode = "managed",
    ) -> None:
        self.session_id = session_id
        self.state: BridgeState = "idle"
        self.attach_mode: AttachMode = attach_mode
        self.pending_approval: dict[str, asyncio.Future] = {}
        self.pending_input: dict[str, asyncio.Future] = {}
        self.pending_approval_context: dict[str, dict[str, object]] = {}
        self.pending_input_context: dict[str, dict[str, object]] = {}
        self.event_backlog: deque[Event] = deque(maxlen=50)
        self.connection_manager = connection_manager
        self.messages_to_inject: list[str] = []
        self._event_listeners: set[EventListener] = set()

        self._background_tasks: set[asyncio.Task[object]] = set()
        self._message_queue: asyncio.Queue[str] = asyncio.Queue()
        self._message_worker_task: asyncio.Task[None] | None = None
        self._run_lock = asyncio.Lock()
        self._agent_loop: object | None = None
        self._vibe_runtime: VibeRuntime | None = None
        self._observed_message_ids: set[str] = set()
        self._message_observer_hooked = False

    @property
    def controllable(self) -> bool:
        return self.attach_mode != "observe_only"

    def add_event_listener(self, listener: EventListener) -> None:
        self._event_listeners.add(listener)

    def remove_event_listener(self, listener: EventListener) -> None:
        self._event_listeners.discard(listener)

    async def _notify_event_listeners(self, event: Event) -> None:
        for listener in list(self._event_listeners):
            try:
                result = listener(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                continue

    def _notify_event_listeners_background(self, event: Event) -> None:
        if not self._event_listeners:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            for listener in list(self._event_listeners):
                try:
                    result = listener(event)
                    if inspect.isawaitable(result):
                        continue
                except Exception:
                    continue
            return

        task = loop.create_task(self._notify_event_listeners(event))
        self._track_task(task)

    async def _broadcast(self, event: Event) -> None:
        self.add_event(event)
        await self._notify_event_listeners(event)
        if self.connection_manager:
            await self.connection_manager.broadcast(self.session_id, event)

    def _track_task(self, task: asyncio.Task[object]) -> None:
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _broadcast_background(self, event: Event) -> None:
        self.add_event(event)
        self._notify_event_listeners_background(event)
        if not self.connection_manager:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = loop.create_task(self.connection_manager.broadcast(self.session_id, event))
        self._track_task(task)

    def add_event(self, event: Event) -> None:
        self.event_backlog.append(event)

    def backlog(self, limit: int = 50) -> list[Event]:
        return list(self.event_backlog)[-limit:]

    def _set_state(self, state: BridgeState) -> None:
        if self.state == state:
            return
        self.state = state
        self._broadcast_background(
            StateChangeEvent(
                state=state,
                attach_mode=self.attach_mode,
                controllable=self.controllable,
            )
        )

    async def request_approval(self, call_id: str, tool_name: str, args: dict) -> dict:
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self.pending_approval[call_id] = future
        self.pending_approval_context[call_id] = {"tool_name": tool_name, "args": args}
        self._set_state("waiting_approval")
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
        self._set_state("running")
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
        self._set_state("waiting_input")
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
        self._set_state("running")
        self._broadcast_background(InputResolutionEvent(request_id=request_id, response=response))
        return True

    def _message_to_dict(self, value: object) -> dict:
        if hasattr(value, "model_dump"):
            return dict(value.model_dump(mode="json"))
        if isinstance(value, dict):
            return dict(value)
        return {"value": str(value)}

    def _extract_input_question(self, args: object) -> tuple[str, list[str], list[str]]:
        default_question = "Input requested"
        options: list[str] = []
        all_questions: list[str] = []

        questions = getattr(args, "questions", None)
        if not isinstance(questions, list) or not questions:
            return default_question, options, all_questions

        first = questions[0]
        if isinstance(getattr(first, "question", None), str):
            default_question = first.question

        for item in questions:
            text = getattr(item, "question", None)
            if isinstance(text, str) and text:
                all_questions.append(text)

        raw_options = getattr(first, "options", None)
        if isinstance(raw_options, list):
            for option in raw_options:
                label = getattr(option, "label", None)
                options.append(str(label) if label is not None else str(option))

        return default_question, options, all_questions

    def _build_input_result(self, answer_text: str, question_texts: list[str]) -> object:
        runtime = self._vibe_runtime
        if runtime is None or runtime.ask_result_cls is None or runtime.answer_cls is None:
            return {"response": answer_text}

        prompts = question_texts or ["Input requested"]
        answers = [
            runtime.answer_cls(question=prompt, answer=answer_text, is_other=False)
            for prompt in prompts
        ]
        return runtime.ask_result_cls(answers=answers, cancelled=False)

    def _apply_edited_args(self, args: object, edited_args: dict[str, object]) -> bool:
        if not edited_args:
            return True

        # Prefer full schema re-validation for Pydantic argument models.
        validator = getattr(args.__class__, "model_validate", None)
        dump = getattr(args, "model_dump", None)
        if callable(validator) and callable(dump):
            try:
                current = dump(mode="python")
                if isinstance(current, dict):
                    merged = {**current, **edited_args}
                    validated = validator(merged)
                    updated = validated.model_dump(mode="python")
                    if isinstance(updated, dict):
                        for key, value in updated.items():
                            if hasattr(args, key):
                                setattr(args, key, value)
                        return True
            except Exception:
                return False
            return False

        # Best effort for plain python argument holders used in tests/mocks.
        existing: dict[str, object] = {}
        for key in edited_args:
            if not hasattr(args, key):
                continue
            existing[key] = getattr(args, key)

        try:
            for key, value in edited_args.items():
                if key in existing:
                    setattr(args, key, value)
        except Exception:
            for key, value in existing.items():
                try:
                    setattr(args, key, value)
                except Exception:
                    pass
            return False

        return bool(existing)

    async def _approval_callback(
        self, tool_name: str, args: object, tool_call_id: str
    ) -> tuple[object, str | None]:
        approval = await self.request_approval(
            call_id=tool_call_id,
            tool_name=tool_name,
            args=self._message_to_dict(args),
        )
        runtime = self._vibe_runtime
        yes = runtime.approval_yes if runtime else "y"
        no = runtime.approval_no if runtime else "n"

        edited_args = approval.get("edited_args")
        if approval.get("approved") and isinstance(edited_args, dict):
            if not self._apply_edited_args(args, edited_args):
                return (no, "edited_args failed validation")

        feedback = None
        if edited_args is not None:
            feedback = json.dumps(edited_args, ensure_ascii=True)
        return (yes if approval.get("approved") else no, feedback)

    async def _user_input_callback(self, args: object) -> object:
        question, options, prompts = self._extract_input_question(args)
        request_id = f"req-{uuid4().hex[:8]}"
        response = await self.request_input(request_id=request_id, question=question, options=options)
        return self._build_input_result(response, prompts)

    def _on_message_observed(self, message: object) -> None:
        message_id = getattr(message, "message_id", None)
        if isinstance(message_id, str):
            if message_id in self._observed_message_ids:
                return
            self._observed_message_ids.add(message_id)

        role = getattr(message, "role", None)
        role_value = getattr(role, "value", role)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content:
            return

        if role_value == "assistant":
            self._broadcast_background(AssistantEvent(content=content))
        elif role_value == "user":
            self._broadcast_background(UserMessageEvent(content=content))

    def _convert_vibe_event(self, raw_event: object) -> Event | None:
        kind = raw_event.__class__.__name__

        if kind.endswith("UserMessageEvent"):
            message_id = getattr(raw_event, "message_id", None)
            if isinstance(message_id, str):
                if message_id in self._observed_message_ids:
                    return None
                self._observed_message_ids.add(message_id)
            content = getattr(raw_event, "content", "")
            return UserMessageEvent(content=str(content))

        if kind.endswith("AssistantEvent"):
            message_id = getattr(raw_event, "message_id", None)
            if isinstance(message_id, str):
                if message_id in self._observed_message_ids:
                    return None
                self._observed_message_ids.add(message_id)
            content = getattr(raw_event, "content", "")
            return AssistantEvent(content=str(content))

        if kind.endswith("ToolCallEvent"):
            return ToolCallEvent(
                tool_name=str(getattr(raw_event, "tool_name", "tool")),
                args=self._message_to_dict(getattr(raw_event, "args", {})),
                call_id=str(getattr(raw_event, "tool_call_id", "")),
            )

        if kind.endswith("ToolResultEvent"):
            call_id = str(getattr(raw_event, "tool_call_id", ""))
            error = getattr(raw_event, "error", None)
            if isinstance(error, str) and error:
                return ToolResultEvent(call_id=call_id, output=error, is_error=True)

            result = getattr(raw_event, "result", None)
            if hasattr(result, "model_dump"):
                output = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
            elif result is None:
                output = ""
            else:
                output = str(result)
            return ToolResultEvent(call_id=call_id, output=output, is_error=False)

        return None

    def _wire_callbacks(self, agent_loop: object) -> None:
        if hasattr(agent_loop, "set_approval_callback"):
            agent_loop.set_approval_callback(self._approval_callback)
        if hasattr(agent_loop, "set_user_input_callback"):
            agent_loop.set_user_input_callback(self._user_input_callback)

    def _wire_message_observer(self, agent_loop: object) -> None:
        if self._message_observer_hooked:
            return

        existing = getattr(agent_loop, "message_observer", None)

        def chained(message: object) -> None:
            self._on_message_observed(message)
            if callable(existing) and existing is not self._on_message_observed:
                existing(message)

        try:
            setattr(agent_loop, "message_observer", chained)
            self._message_observer_hooked = True
        except Exception:
            self._message_observer_hooked = False

    def attach_to_loop(
        self,
        agent_loop: object,
        vibe_runtime: VibeRuntime | None = None,
    ) -> None:
        self._agent_loop = agent_loop
        self._message_observer_hooked = False
        if vibe_runtime is not None:
            self._vibe_runtime = vibe_runtime
        self.attach_mode = "live"
        self._wire_callbacks(agent_loop)
        self._wire_message_observer(agent_loop)

    def _ensure_agent_loop(self) -> None:
        if self._agent_loop is not None:
            return

        runtime = load_vibe_runtime()
        config = runtime.vibe_config_cls.load()
        try:
            agent_loop = runtime.agent_loop_cls(
                config,
                message_observer=self._on_message_observed,
                enable_streaming=False,
            )
        except TypeError:
            agent_loop = runtime.agent_loop_cls(
                config,
                message_observer=self._on_message_observed,
            )

        self.attach_mode = "managed"
        self._message_observer_hooked = False
        self._wire_callbacks(agent_loop)
        self._wire_message_observer(agent_loop)
        self._agent_loop = agent_loop
        self._vibe_runtime = runtime

    async def _run_agent_turn(self, content: str) -> None:
        if self._agent_loop is None:
            return

        self._set_state("running")
        async with self._run_lock:
            try:
                async for raw_event in self._agent_loop.act(content):
                    event = self._convert_vibe_event(raw_event)
                    if event is not None:
                        await self._broadcast(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - integration behavior
                await self._broadcast(
                    AssistantEvent(content=f"Bridge failed to process agent event: {exc}")
                )

    async def _message_worker(self) -> None:
        while True:
            content = await self._message_queue.get()
            try:
                await self._run_agent_turn(content)
            finally:
                self._message_queue.task_done()
                if (
                    self.state == "running"
                    and not self.pending_approval
                    and not self.pending_input
                    and self._message_queue.empty()
                ):
                    self._set_state("idle")

    def _ensure_message_worker(self) -> None:
        if self._message_worker_task is not None and not self._message_worker_task.done():
            return
        loop = asyncio.get_running_loop()
        task: asyncio.Task[None] = loop.create_task(self._message_worker())
        self._message_worker_task = task
        self._track_task(task)

    async def start_session(self, message: str, working_dir: Path | None = None) -> None:
        _ = working_dir
        self._ensure_agent_loop()
        self._message_queue.put_nowait(message)
        self._ensure_message_worker()
        await self._message_queue.join()

    def inject_message(self, content: str) -> bool:
        self.messages_to_inject.append(content)
        if not self.controllable:
            self._set_state("idle")
            return False

        if self._agent_loop is None:
            try:
                self._ensure_agent_loop()
            except RuntimeError:
                self._broadcast_background(UserMessageEvent(content=content))
                self._set_state("idle")
                return False

        self._set_state("running")
        self._message_queue.put_nowait(content)
        try:
            self._ensure_message_worker()
        except RuntimeError:
            # If no running loop is available, keep the message queued for the next
            # async context and still reflect the message in UI immediately.
            self._broadcast_background(UserMessageEvent(content=content))
            self._set_state("idle")
            return False
        return True

    def stop(self) -> None:
        if self._message_worker_task and not self._message_worker_task.done():
            self._message_worker_task.cancel()
        self._message_worker_task = None

        for task in list(self._background_tasks):
            task.cancel()
        self._background_tasks.clear()

        self.pending_approval.clear()
        self.pending_input.clear()
        self.pending_approval_context.clear()
        self.pending_input_context.clear()
        self._set_state("disconnected")

    def state_payload(self) -> dict:
        payload: dict[str, object] = {
            "state": self.state,
            "attach_mode": self.attach_mode,
            "controllable": self.controllable,
        }
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
                    "attach_mode": (
                        self.sessions[session_id].attach_mode
                        if session_id in self.sessions
                        else "observe_only"
                    ),
                    "controllable": (
                        self.sessions[session_id].controllable
                        if session_id in self.sessions
                        else False
                    ),
                }
            )
        return discovered

    def _message_count(self, session_dir: Path) -> int:
        messages_file = session_dir / "messages.jsonl"
        if not messages_file.exists():
            return 0
        return sum(1 for _ in messages_file.open("r", encoding="utf-8"))

    def attach(
        self,
        session_id: str,
        attach_mode: AttachMode | None = None,
    ) -> SessionBridge:
        if session_id in self.sessions:
            bridge = self.sessions[session_id]
            if attach_mode is not None:
                bridge.attach_mode = attach_mode
            return bridge

        mode = attach_mode
        if mode is None:
            mode = "observe_only" if any(item["id"] == session_id for item in self.discover()) else "managed"

        bridge = SessionBridge(
            session_id=session_id,
            connection_manager=self.connection_manager,
            attach_mode=mode,
        )
        self.sessions[session_id] = bridge
        return bridge

    def detach(self, session_id: str) -> None:
        bridge = self.sessions.pop(session_id, None)
        if bridge is not None:
            bridge.stop()

    async def start_session(
        self,
        session_id: str,
        message: str,
        working_dir: Path | None = None,
    ) -> SessionBridge:
        bridge = self.attach(session_id, attach_mode="managed")
        await bridge.start_session(message=message, working_dir=working_dir)
        return bridge

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
                    "attach_mode": bridge.attach_mode,
                    "controllable": bridge.controllable,
                }
            else:
                discovered[session_id]["status"] = bridge.state
                discovered[session_id]["attach_mode"] = bridge.attach_mode
                discovered[session_id]["controllable"] = bridge.controllable
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
                "attach_mode": bridge.attach_mode,
                "controllable": bridge.controllable,
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
            "attach_mode": "observe_only",
            "controllable": False,
            "pending_approval": [],
            "pending_input": [],
            "backlog": [],
            "started_at": discovered["started_at"],
            "last_activity": discovered["last_activity"],
            "message_count": discovered["message_count"],
        }


session_manager = SessionManager()
