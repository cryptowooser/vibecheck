from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from vibecheck.live_probe import (
    SessionSnapshot,
    discover_sessions,
    parse_message_line,
    pick_session,
)


def _write_session(
    root: Path,
    folder: str,
    *,
    session_id: str,
    cwd: str,
    messages: list[dict],
) -> Path:
    session_dir = root / folder
    session_dir.mkdir(parents=True)

    meta = {
        "session_id": session_id,
        "start_time": "2026-02-28T00:00:00+00:00",
        "end_time": None,
        "environment": {"working_directory": cwd},
    }
    (session_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    with (session_dir / "messages.jsonl").open("w", encoding="utf-8") as handle:
        for message in messages:
            handle.write(json.dumps(message) + "\n")

    return session_dir


def test_discover_sessions_filters_and_sorts(tmp_path: Path) -> None:
    root = tmp_path / "session"
    project = "/home/ubuntu/vibecheck"

    older = _write_session(
        root,
        "session_older_11111111",
        session_id="11111111-aaaa-bbbb-cccc-111111111111",
        cwd=project,
        messages=[{"role": "user", "content": "first", "message_id": "m1"}],
    )
    newer = _write_session(
        root,
        "session_newer_22222222",
        session_id="22222222-aaaa-bbbb-cccc-222222222222",
        cwd=project,
        messages=[{"role": "assistant", "content": "second", "message_id": "m2"}],
    )
    _write_session(
        root,
        "session_other_33333333",
        session_id="33333333-aaaa-bbbb-cccc-333333333333",
        cwd="/tmp/elsewhere",
        messages=[{"role": "assistant", "content": "third", "message_id": "m3"}],
    )

    # Ensure deterministic order by mtime.
    older_messages = older / "messages.jsonl"
    newer_messages = newer / "messages.jsonl"
    os.utime(older_messages, (1000, 1000))
    os.utime(newer_messages, (2000, 2000))

    snapshots = discover_sessions(root, cwd_filter=project)

    assert [item.session_id for item in snapshots] == [
        "22222222-aaaa-bbbb-cccc-222222222222",
        "11111111-aaaa-bbbb-cccc-111111111111",
    ]
    assert all(isinstance(item, SessionSnapshot) for item in snapshots)


def test_pick_session_by_prefix(tmp_path: Path) -> None:
    root = tmp_path / "session"
    project = "/home/ubuntu/vibecheck"

    _write_session(
        root,
        "session_a_aaaaaaaa",
        session_id="aaaaaaaa-0000-0000-0000-aaaaaaaaaaaa",
        cwd=project,
        messages=[{"role": "assistant", "content": "a", "message_id": "a"}],
    )
    _write_session(
        root,
        "session_b_bbbbbbbb",
        session_id="bbbbbbbb-0000-0000-0000-bbbbbbbbbbbb",
        cwd=project,
        messages=[{"role": "assistant", "content": "b", "message_id": "b"}],
    )

    snapshots = discover_sessions(root, cwd_filter=project)

    chosen = pick_session(snapshots, session_hint="aaaa")
    assert chosen is not None
    assert chosen.session_id.startswith("aaaaaaaa")

    assert pick_session(snapshots, session_hint="missing") is None


def test_parse_message_line_shapes() -> None:
    user = parse_message_line('{"role":"user","content":"hello","message_id":"u1"}')
    assert user.kind == "user_message"
    assert user.message_id == "u1"

    tool_call = parse_message_line(
        '{"role":"assistant","tool_calls":[{"function":{"name":"bash"},"id":"tc-1"}],"message_id":"a1"}'
    )
    assert tool_call.kind == "tool_call"
    assert "bash" in tool_call.summary

    tool_result = parse_message_line(
        '{"role":"tool","name":"bash","tool_call_id":"tc-1","content":"ok"}'
    )
    assert tool_result.kind == "tool_result"
    assert "bash" in tool_result.summary


def test_parse_message_line_rejects_invalid_json() -> None:
    with pytest.raises(ValueError):
        parse_message_line("not-json")
