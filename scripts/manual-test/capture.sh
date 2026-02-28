#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACTS_ROOT="$ROOT_DIR/artifacts/manual-test"

BASE_URL="${BASE_URL:-}"
WS_PORT="${WS_PORT:-7870}"

usage() {
  cat <<'EOF'
Usage: capture.sh [--base-url URL] [--ws-port PORT]

Starts vibecheck-vibe under terminal transcript capture.
Use this in Terminal A for WU-34 manual validation.

Examples:
  scripts/manual-test/capture.sh --base-url https://vibecheck.example.com --ws-port 7870
  BASE_URL=https://vibecheck.example.com scripts/manual-test/capture.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --ws-port)
      WS_PORT="${2:-7870}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$BASE_URL" ]]; then
  read -r -p "Base URL (e.g. https://vibecheck.example.com): " BASE_URL
fi

mkdir -p "$ARTIFACTS_ROOT"
timestamp="$(date +%Y%m%d-%H%M%S)"
run_dir="$ARTIFACTS_ROOT/wu34-$timestamp"
mkdir -p "$run_dir"

transcript_file="$run_dir/tui-transcript.log"
meta_file="$run_dir/meta.txt"

{
  echo "timestamp=$timestamp"
  echo "base_url=$BASE_URL"
  echo "ws_port=$WS_PORT"
  echo "cwd=$ROOT_DIR"
} >"$meta_file"

echo "Starting vibecheck-vibe with transcript capture"
echo "Run dir: $run_dir"
echo "Transcript: $transcript_file"
echo
echo "Phone UI URL: $BASE_URL"
echo
echo "Then in Terminal B run:"
echo "  scripts/manual-test/run.sh --base-url $BASE_URL"
echo "  # SID auto-selects; no manual SID needed"
echo "  # Use Phone debug URL printed by run.sh to confirm session binding"
echo
echo "Session verification helper (Terminal B):"
echo "  scripts/manual-test/api.sh selected-sid"
echo
echo "Stop with Ctrl+C when done."

cd "$ROOT_DIR"

if ! uv run python - <<'PY' >/dev/null 2>&1
from vibecheck.bridge import load_vibe_runtime
load_vibe_runtime()
PY
then
  echo
  echo "Vibe runtime preflight failed."
  echo "Install runtime deps once, then retry:"
  echo "  uv pip install -e reference/mistral-vibe"
  exit 1
fi

script -q -f "$transcript_file" -c "uv run vibecheck-vibe --ws-port $WS_PORT"
