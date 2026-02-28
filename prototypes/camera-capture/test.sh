#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing camera-capture ==="
uv run python server.py >/tmp/proto-camera.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

READY=0
for _ in {1..50}; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server exited early; see /tmp/proto-camera.log"
    exit 1
  fi
  echo 'probe-image-bytes' >/tmp/proto-probe-image.jpg
  PROBE_RESP=$(curl -s -X POST -F "image=@/tmp/proto-probe-image.jpg;type=image/jpeg" http://localhost:8080/upload || true)
  if [[ "$PROBE_RESP" == *'"description":"A whiteboard with code"'* ]]; then
    READY=1
    break
  fi
  sleep 0.2
done

if [[ "$READY" -ne 1 ]]; then
  echo "Server did not become ready"
  exit 1
fi

echo 'not-a-real-image' >/tmp/proto-image.jpg
RESP=$(curl -sf -X POST -F "image=@/tmp/proto-image.jpg;type=image/jpeg" http://localhost:8080/upload)

uv run python - <<'PY' "$RESP"
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["description"] == "A whiteboard with code"
assert payload["bytes"] > 0
assert payload["content_type"] == "image/jpeg"
print("PASS: camera upload", payload["bytes"])
PY
