#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing media-recorder ==="
uv run python server.py >/tmp/proto-media-recorder.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

READY=0
for _ in {1..50}; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server exited early; see /tmp/proto-media-recorder.log"
    exit 1
  fi
  PROBE_RESP=$(curl -s -X POST -H 'Content-Type: audio/webm;codecs=opus' --data-binary 'probe' http://localhost:8080/upload || true)
  if [[ "$PROBE_RESP" == *'"text":"テスト"'* ]]; then
    READY=1
    break
  fi
  sleep 0.2
done

if [[ "$READY" -ne 1 ]]; then
  echo "Server did not become ready"
  exit 1
fi

echo 'fake opus bytes' >/tmp/proto-audio.webm
RESP=$(curl -sf -X POST \
  -H 'Content-Type: audio/webm;codecs=opus' \
  --data-binary @/tmp/proto-audio.webm \
  http://localhost:8080/upload)

uv run python - <<'PY' "$RESP"
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["text"] == "テスト"
assert payload["language"] == "ja"
assert isinstance(payload["duration_ms"], int)
print("PASS: media response", payload["duration_ms"])
PY
