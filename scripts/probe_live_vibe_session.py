#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from vibecheck.live_probe import (
    discover_sessions,
    follow_new_lines,
    parse_message_line,
    pick_session,
    read_last_lines,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe a live Vibe session log to verify event tap capability."
    )
    parser.add_argument(
        "--logs-root",
        type=Path,
        default=Path.home() / ".vibe" / "logs" / "session",
        help="Session logs root directory (default: ~/.vibe/logs/session)",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=str(Path.cwd()),
        help="Filter sessions by working directory (default: current directory)",
    )
    parser.add_argument(
        "--all-cwds",
        action="store_true",
        help="Disable CWD filtering and search all sessions",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session id hint (full/short/prefix)",
    )
    parser.add_argument(
        "--show-last",
        type=int,
        default=8,
        help="Show the last N existing messages before tailing",
    )
    parser.add_argument(
        "--tail-seconds",
        type=float,
        default=20.0,
        help="Seconds to watch for new log lines",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=0.5,
        help="Polling interval while tailing",
    )
    parser.add_argument(
        "--require-new",
        action="store_true",
        help="Exit non-zero if no new lines appear during tail period",
    )
    return parser.parse_args()


def _format_age(seconds: float) -> str:
    if seconds < 1:
        return "<1s"
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes, remainder = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{remainder:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def _print_event(prefix: str, raw_line: str) -> None:
    try:
        event = parse_message_line(raw_line)
    except ValueError as exc:
        print(f"{prefix} [invalid] {exc}")
        return

    mid = f" id={event.message_id}" if event.message_id else ""
    print(f"{prefix} [{event.kind}]{mid} {event.summary}")


def main() -> int:
    args = _parse_args()

    cwd_filter = None if args.all_cwds else args.cwd
    sessions = discover_sessions(args.logs_root, cwd_filter=cwd_filter)

    if not sessions:
        filter_text = "(all cwd)" if cwd_filter is None else f"cwd={cwd_filter}"
        print(f"FAIL: no sessions found in {args.logs_root} with filter {filter_text}")
        return 2

    target = pick_session(sessions, session_hint=args.session)
    if target is None:
        print(f"FAIL: no session matched hint: {args.session}")
        return 3

    message_path = target.session_dir / "messages.jsonl"
    age_seconds = max(0.0, datetime.now(tz=UTC).timestamp() - target.last_message_mtime)

    print("=== Vibe Live Session Probe ===")
    print(f"Session:   {target.session_id}")
    print(f"Directory: {target.session_dir}")
    print(f"Messages:  {target.message_count}")
    print(f"Last write:{_format_age(age_seconds)} ago")
    if target.working_directory:
        print(f"CWD:       {target.working_directory}")
    if target.started_at:
        print(f"Started:   {target.started_at}")
    if target.ended_at:
        print(f"Ended:     {target.ended_at}")

    print(f"\n--- Last {args.show_last} logged messages ---")
    existing = read_last_lines(message_path, limit=args.show_last)
    for line in existing:
        _print_event("old", line)

    counts: Counter[str] = Counter()
    for line in existing:
        try:
            counts[parse_message_line(line).kind] += 1
        except ValueError:
            counts["invalid"] += 1

    new_lines: list[str] = []
    if args.tail_seconds > 0:
        print(f"\n--- Watching for new lines ({args.tail_seconds:.1f}s) ---")
        new_lines = follow_new_lines(
            message_path,
            duration_seconds=args.tail_seconds,
            poll_seconds=max(args.poll_seconds, 0.05),
        )
        if not new_lines:
            print("new [none] no new messages observed")
        for line in new_lines:
            _print_event("new", line)
            try:
                counts[parse_message_line(line).kind] += 1
            except ValueError:
                counts["invalid"] += 1

    print("\n--- Verdict ---")
    print("PASS: session discovery from ~/.vibe/logs/session")
    if existing or new_lines:
        print("PASS: message/event tap via session log parsing")
    else:
        print("WARN: session exists but no parsable messages were found")

    print(
        "INFO: callback control (approve/input) is NOT attachable to an already-running "
        "external `vibe` process; this requires in-process AgentLoop hooks in vibecheck bridge."
    )

    if counts:
        print(f"INFO: observed event counts: {dict(counts)}")

    if args.require_new and not new_lines:
        print("FAIL: --require-new was set but no new lines appeared")
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
