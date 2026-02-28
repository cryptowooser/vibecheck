#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing websocket-reconnect ==="
uv run python server.py >/tmp/proto-ws-reconnect.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

READY=0
for _ in {1..50}; do
  if curl -sf http://localhost:8080/ >/dev/null; then
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
curl -sf -X POST http://localhost:8080/drop >/dev/null

echo "PASS: websocket message received"
