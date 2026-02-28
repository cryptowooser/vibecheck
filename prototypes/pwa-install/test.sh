#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing pwa-install ==="
uv run python -m http.server 8080 >/tmp/proto-pwa.log 2>&1 &
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

curl -sf http://localhost:8080/manifest.json >/tmp/proto-manifest.json
curl -sf http://localhost:8080/sw.js >/tmp/proto-sw.js
curl -sf http://localhost:8080/icons/vibe-192.png >/dev/null

python3 - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('/tmp/proto-manifest.json').read_text(encoding='utf-8'))
assert manifest['display'] == 'standalone'
assert any(icon['sizes'] == '192x192' for icon in manifest['icons'])
assert any(icon['sizes'] == '512x512' for icon in manifest['icons'])
print('PASS: manifest and sw served')
PY
