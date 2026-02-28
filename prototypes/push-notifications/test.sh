#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing push-notifications ==="
uv run python server.py >/tmp/proto-push.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

READY=0
for _ in {1..50}; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server exited early; see /tmp/proto-push.log"
    exit 1
  fi
  PROBE_RESP=$(curl -s http://localhost:8080/vapid-public-key || true)
  if [[ "$PROBE_RESP" == *'"publicKey"'* ]]; then
    READY=1
    break
  fi
  sleep 0.2
done

if [[ "$READY" -ne 1 ]]; then
  echo "Server did not become ready"
  exit 1
fi

KEY=$(curl -sf http://localhost:8080/vapid-public-key)
uv run python - <<'PY' "$KEY"
import json
import sys
payload = json.loads(sys.argv[1])
assert payload.get("publicKey")
print("PASS: public key endpoint")
PY

DUMMY='{"endpoint":"https://example.com/push/abc123","expirationTime":null,"keys":{"p256dh":"BNc_dummy","auth":"abc_dummy"}}'
SUB_RESP=$(curl -sf -X POST -H 'Content-Type: application/json' -d "$DUMMY" http://localhost:8080/subscribe)
uv run python - <<'PY' "$SUB_RESP"
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["status"] == "ok"
print("PASS: subscribe endpoint")
PY

SEND_RESP=$(curl -sf -X POST -H 'Content-Type: application/json' -d '{"title":"test","body":"hello"}' http://localhost:8080/send-test)
uv run python - <<'PY' "$SEND_RESP"
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["status"] == "ok"
assert "attempted" in payload
print("PASS: send-test endpoint", payload["attempted"], payload["failed"])
PY
