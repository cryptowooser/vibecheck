#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/.env.local" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.env.local"
fi

BASE_URL="${BASE_URL:-}"
PSK="${PSK:-}"
SID="${SID:-${SESSION_ID:-}}"
_SID_AUTO_SELECTED=0

usage() {
  cat <<'EOF'
Usage: api.sh <command> [args...]

Environment:
  BASE_URL  Required for API commands (e.g., https://vibecheck.example.com)
  PSK       Required for authenticated API commands
  SID       Session ID for session-specific commands

Commands:
  sessions
  live-session-id
  selected-sid
  ws-check [timeout_seconds]
  state
  detail
  call-id
  request-id
  wait-pending-approval [timeout_seconds]
  wait-pending-input [timeout_seconds]
  wait-clear-approval [timeout_seconds]
  wait-clear-input [timeout_seconds]
  wait-state <state> [timeout_seconds]
  message <text>
  approve <call_id>
  reject <call_id>
  answer <request_id> <response>

Examples:
  BASE_URL=https://host PSK=... ./api.sh sessions
  BASE_URL=https://host PSK=... SID=live-session ./api.sh wait-pending-approval 120
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing dependency: $1" >&2
    exit 1
  }
}

require_auth() {
  if [[ -z "$BASE_URL" || -z "$PSK" ]]; then
    echo "BASE_URL and PSK are required" >&2
    exit 1
  fi
}

require_sid() {
  require_auth
  if [[ -z "$SID" ]]; then
    SID="$(discover_live_sid)"
    _SID_AUTO_SELECTED=1
  fi

  if [[ -z "$SID" ]]; then
    echo "SID is required for this command (no live/controllable session found)" >&2
    exit 1
  fi

  if ! api_get "/api/sessions/$SID/state" >/dev/null 2>&1; then
    SID="$(discover_live_sid)"
    _SID_AUTO_SELECTED=1
  fi

  if [[ -z "$SID" ]]; then
    echo "Could not resolve a usable SID from /api/sessions" >&2
    exit 1
  fi
}

api_get() {
  local path="$1"
  curl -fsS -H "X-PSK: $PSK" "$BASE_URL$path"
}

api_post() {
  local path="$1"
  local body="$2"
  curl -fsS -H "X-PSK: $PSK" -H "Content-Type: application/json" -X POST "$BASE_URL$path" -d "$body"
}

discover_live_sid() {
  api_get "/api/sessions" | jq -r '
    [.[] | select(.attach_mode == "live" and .controllable == true and .status != "disconnected")][0].id //
    [.[] | select(.controllable == true and .status != "disconnected")][0].id //
    [.[] | select(.attach_mode == "live")][0].id //
    .[0].id //
    empty
  '
}

announce_selected_sid_once() {
  if [[ "${_SID_AUTO_SELECTED:-0}" -eq 1 ]]; then
    echo "Auto-selected SID=$SID" >&2
    _SID_AUTO_SELECTED=0
  fi
}

session_state_json() {
  api_get "/api/sessions/$SID/state"
}

wait_until_expr_nonempty() {
  local jq_expr="$1"
  local timeout="${2:-120}"
  local interval=1
  local elapsed=0
  local value=""

  while (( elapsed < timeout )); do
    value="$(session_state_json | jq -r "$jq_expr")"
    if [[ -n "$value" && "$value" != "null" ]]; then
      echo "$value"
      return 0
    fi
    sleep "$interval"
    ((elapsed += interval))
  done

  return 1
}

wait_until_expr_empty() {
  local jq_expr="$1"
  local timeout="${2:-120}"
  local interval=1
  local elapsed=0
  local value=""

  while (( elapsed < timeout )); do
    value="$(session_state_json | jq -r "$jq_expr")"
    if [[ -z "$value" || "$value" == "null" ]]; then
      return 0
    fi
    sleep "$interval"
    ((elapsed += interval))
  done

  return 1
}

require_cmd jq
require_cmd curl
require_cmd uv

command="${1:-}"
if [[ -z "$command" || "$command" == "--help" || "$command" == "-h" ]]; then
  usage
  exit 0
fi
shift || true

case "$command" in
  sessions)
    require_auth
    api_get "/api/sessions" | jq
    ;;
  live-session-id)
    require_auth
    discover_live_sid
    ;;
  selected-sid)
    require_auth
    require_sid
    announce_selected_sid_once
    echo "$SID"
    ;;
  ws-check)
    require_sid
    announce_selected_sid_once
    timeout="${1:-8}"
    BASE_URL="$BASE_URL" SID="$SID" PSK="$PSK" WS_TIMEOUT="$timeout" uv run python - <<'PY'
import asyncio
import json
import os
import sys
from urllib.parse import quote, urlparse, urlunparse

try:
    import websockets
except Exception as exc:  # pragma: no cover - runtime env check
    print(
        "websocket probe requires python package 'websockets'; install via: uv pip install websockets",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


def build_ws_url(base_url: str, session_id: str, psk: str) -> str:
    parsed = urlparse(base_url if "://" in base_url else f"https://{base_url}")
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc or parsed.path
    base_path = parsed.path if parsed.netloc else ""
    path = f"{base_path.rstrip('/')}/ws/events/{quote(session_id, safe='')}"
    query = f"psk={quote(psk, safe='')}"
    return urlunparse((scheme, netloc, path, "", query, ""))


async def probe(url: str, timeout: float) -> dict:
    async with websockets.connect(
        url,
        open_timeout=timeout,
        close_timeout=1,
        ping_interval=None,
    ) as ws:
        first_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        second_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)

    first = json.loads(first_raw)
    second = json.loads(second_raw)
    if first.get("type") != "connected":
        raise RuntimeError(f"expected first websocket event=connected, got={first.get('type')}")
    if second.get("type") != "state":
        raise RuntimeError(f"expected second websocket event=state, got={second.get('type')}")

    return {
        "ok": True,
        "ws_url": url,
        "session_id": first.get("session_id"),
        "state": second.get("state"),
        "attach_mode": second.get("attach_mode"),
        "controllable": second.get("controllable"),
    }


def main() -> int:
    base_url = os.environ["BASE_URL"]
    sid = os.environ["SID"]
    psk = os.environ["PSK"]
    timeout = float(os.environ.get("WS_TIMEOUT", "8"))
    ws_url = build_ws_url(base_url, sid, psk)
    try:
        result = asyncio.run(probe(ws_url, timeout))
    except Exception as exc:  # pragma: no cover - runtime env check
        print(f"websocket probe failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


raise SystemExit(main())
PY
    ;;
  state)
    require_sid
    announce_selected_sid_once
    session_state_json | jq
    ;;
  detail)
    require_sid
    announce_selected_sid_once
    api_get "/api/sessions/$SID" | jq
    ;;
  call-id)
    require_sid
    announce_selected_sid_once
    session_state_json | jq -r '.pending_approval.call_id // empty'
    ;;
  request-id)
    require_sid
    announce_selected_sid_once
    session_state_json | jq -r '.pending_input.request_id // empty'
    ;;
  wait-pending-approval)
    require_sid
    announce_selected_sid_once
    wait_until_expr_nonempty '.pending_approval.call_id // empty' "${1:-120}"
    ;;
  wait-pending-input)
    require_sid
    announce_selected_sid_once
    wait_until_expr_nonempty '.pending_input.request_id // empty' "${1:-120}"
    ;;
  wait-clear-approval)
    require_sid
    announce_selected_sid_once
    wait_until_expr_empty '.pending_approval.call_id // empty' "${1:-120}"
    ;;
  wait-clear-input)
    require_sid
    announce_selected_sid_once
    wait_until_expr_empty '.pending_input.request_id // empty' "${1:-120}"
    ;;
  wait-state)
    require_sid
    announce_selected_sid_once
    target_state="${1:-}"
    timeout="${2:-120}"
    if [[ -z "$target_state" ]]; then
      echo "wait-state requires <state>" >&2
      exit 1
    fi
    wait_until_expr_nonempty ".state | select(. == \"$target_state\")" "$timeout" >/dev/null
    ;;
  message)
    require_sid
    announce_selected_sid_once
    content="${1:-}"
    if [[ -z "$content" ]]; then
      echo "message requires text content" >&2
      exit 1
    fi
    api_post "/api/sessions/$SID/message" "$(jq -nc --arg c "$content" '{content:$c}')" | jq
    ;;
  approve)
    require_sid
    announce_selected_sid_once
    call_id="${1:-}"
    if [[ -z "$call_id" ]]; then
      echo "approve requires <call_id>" >&2
      exit 1
    fi
    api_post "/api/sessions/$SID/approve" "$(jq -nc --arg id "$call_id" '{call_id:$id, approved:true}')" | jq
    ;;
  reject)
    require_sid
    announce_selected_sid_once
    call_id="${1:-}"
    if [[ -z "$call_id" ]]; then
      echo "reject requires <call_id>" >&2
      exit 1
    fi
    api_post "/api/sessions/$SID/approve" "$(jq -nc --arg id "$call_id" '{call_id:$id, approved:false}')" | jq
    ;;
  answer)
    require_sid
    announce_selected_sid_once
    request_id="${1:-}"
    response="${2:-}"
    if [[ -z "$request_id" || -z "$response" ]]; then
      echo "answer requires <request_id> <response>" >&2
      exit 1
    fi
    api_post "/api/sessions/$SID/input" "$(jq -nc --arg id "$request_id" --arg r "$response" '{request_id:$id, response:$r}')" | jq
    ;;
  *)
    echo "unknown command: $command" >&2
    usage
    exit 1
    ;;
esac
