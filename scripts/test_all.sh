#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv not found in PATH." >&2
  echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

if [[ -z "${MISTRAL_API_KEY:-}" ]]; then
  echo "Error: MISTRAL_API_KEY is not set." >&2
  echo "Export your key: export MISTRAL_API_KEY=YOUR_KEY" >&2
  exit 1
fi

RUN_REALTIME=false
RUN_REALTIME_MIC=false

for arg in "$@"; do
  case "$arg" in
    --realtime)
      RUN_REALTIME=true
      ;;
    --mic)
      RUN_REALTIME=true
      RUN_REALTIME_MIC=true
      ;;
    --help|-h)
      echo "Usage: scripts/preflight_all.sh [--realtime] [--mic]";
      echo "  --realtime  Run Voxtral realtime test from file";
      echo "  --mic       Run Voxtral realtime test from microphone";
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

AUDIO_MP3="$ROOT_DIR/scripts/test_audio.mp3"
AUDIO_WAV="$ROOT_DIR/scripts/test_audio.wav"

run_test() {
  local name="$1"
  shift
  echo ""
  echo "==> $name"
  if "$@"; then
    echo "PASS: $name"
  else
    echo "FAIL: $name" >&2
    return 1
  fi
}

failures=0

run_test "Generate test audio" \
  uv run python scripts/generate_test_audio.py || failures=$((failures + 1))

run_test "Devstral 2" \
  uv run python scripts/test_devstral2.py || failures=$((failures + 1))

run_test "Mistral Large 3" \
  uv run python scripts/test_mistral_large3.py || failures=$((failures + 1))

run_test "Mistral Small (EN-JA)" \
  uv run python scripts/test_mistral_small.py || failures=$((failures + 1))

run_test "Ministral 8B" \
  uv run python scripts/test_ministral8b.py || failures=$((failures + 1))

if [[ -f "$AUDIO_MP3" ]]; then
  run_test "Voxtral batch (transcribe)" \
    uv run python scripts/test_voxtral_transcribe.py "$AUDIO_MP3" || failures=$((failures + 1))
else
  echo "Skipping Voxtral batch: $AUDIO_MP3 not found" >&2
  failures=$((failures + 1))
fi

if [[ "$RUN_REALTIME" == "true" ]]; then
  if [[ "$RUN_REALTIME_MIC" == "true" ]]; then
    run_test "Voxtral realtime (mic)" \
      uv run python scripts/test_voxtral_realtime.py --mic || failures=$((failures + 1))
  else
    if [[ -f "$AUDIO_WAV" ]]; then
      run_test "Voxtral realtime (file)" \
        uv run python scripts/test_voxtral_realtime.py "$AUDIO_WAV" || failures=$((failures + 1))
    else
      echo "Skipping Voxtral realtime: $AUDIO_WAV not found" >&2
      failures=$((failures + 1))
    fi
  fi
else
  echo ""
  echo "Skipping Voxtral realtime (use --realtime or --mic)."
fi

if [[ "$failures" -gt 0 ]]; then
  echo ""
  echo "Tests completed with $failures failure(s)." >&2
  exit 1
fi

echo ""
echo "Tests completed successfully."
