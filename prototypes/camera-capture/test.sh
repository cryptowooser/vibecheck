#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing camera-capture ==="
uv run python server.py >/tmp/proto-camera.log 2>&1 &
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

echo 'not-a-real-image' >/tmp/proto-image.jpg
RESP=$(curl -sf -X POST -F "image=@/tmp/proto-image.jpg;type=image/jpeg" http://localhost:8080/upload)

python3 - <<'PY' "$RESP"
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["description"] == "A whiteboard with code"
assert payload["bytes"] > 0
print("PASS: camera upload", payload["bytes"])
PY
