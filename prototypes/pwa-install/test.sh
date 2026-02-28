#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing pwa-install ==="
uv run python -m http.server 8080 >/tmp/proto-pwa.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

READY=0
for _ in {1..50}; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server exited early; see /tmp/proto-pwa.log"
    exit 1
  fi
  PROBE_MANIFEST=$(curl -s http://localhost:8080/manifest.json || true)
  if [[ "$PROBE_MANIFEST" == *'"display": "standalone"'* ]]; then
    READY=1
    break
  fi
  sleep 0.2
done

if [[ "$READY" -ne 1 ]]; then
  echo "Server did not become ready"
  exit 1
fi

curl -sf http://localhost:8080/manifest.json >/tmp/proto-manifest.json
curl -sf http://localhost:8080/sw.js >/tmp/proto-sw.js
curl -sf http://localhost:8080/icons/vibe-192.png >/dev/null

uv run python - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('/tmp/proto-manifest.json').read_text(encoding='utf-8'))
assert manifest['display'] == 'standalone'
assert manifest['theme_color'] == '#ff7000'
assert manifest['background_color'] == '#11141f'
assert any(icon['sizes'] == '192x192' for icon in manifest['icons'])
assert any(icon['sizes'] == '512x512' for icon in manifest['icons'])
print('PASS: manifest and sw served')
PY
