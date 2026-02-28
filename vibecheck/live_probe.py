from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Literal

LogEventKind = Literal[
    "assistant",
    "tool_call",
    "tool_result",
    "user_message",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    session_id: str
    session_dir: Path
    started_at: str | None
    ended_at: str | None
    working_directory: str | None
    message_count: int
    last_message_mtime: float


@dataclass(frozen=True, slots=True)
class ParsedLogEvent:
    kind: LogEventKind
    message_id: str | None
    summary: str
    raw: dict[str, Any]


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _count_message_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def discover_sessions(logs_root: Path, cwd_filter: str | None = None) -> list[SessionSnapshot]:
    snapshots: list[SessionSnapshot] = []

    if not logs_root.exists() or not logs_root.is_dir():
        return snapshots

    for session_dir in logs_root.iterdir():
        if not session_dir.is_dir():
            continue

        meta_path = session_dir / "meta.json"
        messages_path = session_dir / "messages.jsonl"
        if not meta_path.exists() or not messages_path.exists():
            continue

        meta = _safe_read_json(meta_path)
        if meta is None:
            continue

        session_id = str(meta.get("session_id") or session_dir.name)
        started_at = meta.get("start_time")
        ended_at = meta.get("end_time")

        environment = meta.get("environment")
        working_directory: str | None = None
        if isinstance(environment, dict):
            candidate = environment.get("working_directory")
            if isinstance(candidate, str):
                working_directory = candidate

        if cwd_filter is not None and working_directory != cwd_filter:
            continue

        try:
            last_mtime = messages_path.stat().st_mtime
        except OSError:
            continue

        snapshots.append(
            SessionSnapshot(
                session_id=session_id,
                session_dir=session_dir,
                started_at=started_at if isinstance(started_at, str) else None,
                ended_at=ended_at if isinstance(ended_at, str) else None,
                working_directory=working_directory,
                message_count=_count_message_lines(messages_path),
                last_message_mtime=last_mtime,
            )
        )

    snapshots.sort(key=lambda item: (-item.last_message_mtime, item.session_id))
    return snapshots


def pick_session(
    sessions: list[SessionSnapshot], session_hint: str | None = None
) -> SessionSnapshot | None:
    if not sessions:
        return None

    if not session_hint:
        return sessions[0]

    hint = session_hint.strip().lower()
    if not hint:
        return sessions[0]

    for session in sessions:
        sid = session.session_id.lower()
        short = sid[:8]
        folder = session.session_dir.name.lower()
        if sid.startswith(hint) or short.startswith(hint) or folder.endswith(hint):
            return session

    for session in sessions:
        if hint in session.session_id.lower():
            return session

    return None


def _short_text(value: str | None, limit: int = 120) -> str:
    if not value:
        return ""
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def parse_message_line(line: str) -> ParsedLogEvent:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError("message line is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("message line must decode to a JSON object")

    role = payload.get("role")
    message_id = payload.get("message_id") if isinstance(payload.get("message_id"), str) else None

    if role == "user":
        content = payload.get("content") if isinstance(payload.get("content"), str) else ""
        return ParsedLogEvent(
            kind="user_message",
            message_id=message_id,
            summary=_short_text(content, limit=100),
            raw=payload,
        )

    if role == "assistant":
        tool_calls = payload.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            first = tool_calls[0] if isinstance(tool_calls[0], dict) else {}
            function = first.get("function") if isinstance(first.get("function"), dict) else {}
            tool_name = function.get("name") if isinstance(function.get("name"), str) else "unknown"
            call_id = first.get("id") if isinstance(first.get("id"), str) else ""
            suffix = f" ({call_id})" if call_id else ""
            return ParsedLogEvent(
                kind="tool_call",
                message_id=message_id,
                summary=f"{tool_name}{suffix}",
                raw=payload,
            )

        content = payload.get("content") if isinstance(payload.get("content"), str) else ""
        return ParsedLogEvent(
            kind="assistant",
            message_id=message_id,
            summary=_short_text(content, limit=100),
            raw=payload,
        )

    if role == "tool":
        tool_name = payload.get("name") if isinstance(payload.get("name"), str) else "tool"
        tool_call_id = (
            payload.get("tool_call_id")
            if isinstance(payload.get("tool_call_id"), str)
            else ""
        )
        suffix = f" ({tool_call_id})" if tool_call_id else ""
        content = payload.get("content") if isinstance(payload.get("content"), str) else ""
        summary = f"{tool_name}{suffix}: {_short_text(content, limit=80)}".rstrip()
        return ParsedLogEvent(
            kind="tool_result",
            message_id=message_id,
            summary=summary,
            raw=payload,
        )

    return ParsedLogEvent(
        kind="unknown",
        message_id=message_id,
        summary=_short_text(str(payload), limit=100),
        raw=payload,
    )


def read_last_lines(messages_path: Path, limit: int) -> list[str]:
    if limit <= 0:
        return []
    try:
        with messages_path.open("r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return []
    return [line.rstrip("\n") for line in lines[-limit:]]


def follow_new_lines(
    messages_path: Path,
    *,
    duration_seconds: float,
    poll_seconds: float = 0.5,
) -> list[str]:
    if duration_seconds <= 0:
        return []

    collected: list[str] = []
    deadline = time.monotonic() + duration_seconds

    try:
        with messages_path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(0, 2)
            while time.monotonic() < deadline:
                position = handle.tell()
                line = handle.readline()
                if line:
                    collected.append(line.rstrip("\n"))
                    continue

                handle.seek(position)
                time.sleep(poll_seconds)
    except OSError:
        return collected

    return collected
