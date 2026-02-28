#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing speech-synthesis ==="

grep -q "speechSynthesis" browser-tts.html
uv run python -m py_compile elevenlabs-tts.py elevenlabs-tts-server.py

echo "PASS: browser and python files are valid"

if [[ -n "${ELEVENLABS_API_KEY:-}" ]]; then
  uv run python elevenlabs-tts.py "Hello from vibecheck" --out /tmp/proto-elevenlabs.mp3
  test -s /tmp/proto-elevenlabs.mp3
  echo "PASS: ElevenLabs API synthesis"
else
  echo "SKIP: ELEVENLABS_API_KEY not set; skipping live ElevenLabs call"
fi
