#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Live Attach Integration Test ==="
uv run pytest vibecheck/tests/test_live_attach.py -v

echo "=== Launcher Entry Point Smoke ==="
uv run vibecheck-vibe --help >/dev/null

echo "=== Backend Startup Smoke ==="
uv run python -m vibecheck >/tmp/vibecheck-live-attach.log 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT
sleep 1
curl -sf http://127.0.0.1:7870/api/health >/dev/null
kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
trap - EXIT

echo "Live attach checks passed"
