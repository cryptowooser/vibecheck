#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing websocket-reconnect ==="
uv run python server.py >/tmp/proto-ws-reconnect.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

READY=0
for _ in {1..50}; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server exited early; see /tmp/proto-ws-reconnect.log"
    exit 1
  fi
  DROP_RESP=$(curl -s -X POST http://localhost:8080/drop || true)
  if [[ "$DROP_RESP" == *'"status":"ok"'* ]]; then
    READY=1
    break
  fi
  sleep 0.2
done

if [[ "$READY" -ne 1 ]]; then
  echo "Server did not become ready"
  exit 1
fi

OUT_FILE="/tmp/proto-ws-message.out"
if command -v websocat >/dev/null 2>&1; then
  timeout 8 websocat ws://localhost:8080/ws/events >"$OUT_FILE" || true
else
  uv run python - <<'PY' >"$OUT_FILE"
import asyncio
import websockets

async def main() -> None:
    async with websockets.connect("ws://localhost:8080/ws/events") as ws:
        print(await ws.recv())

asyncio.run(main())
PY
fi

grep -q '"type"' "$OUT_FILE"

# Confirm disconnect bookkeeping is clean: after client disconnect, no stale
# websocket should remain in the hub.
sleep 0.2
DROP_JSON=$(curl -sf -X POST http://localhost:8080/drop)
uv run python - <<'PY' "$DROP_JSON"
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["status"] == "ok"
assert payload["dropped"] == 0, payload
print("PASS: no stale websocket connections")
PY

echo "PASS: websocket message received"
