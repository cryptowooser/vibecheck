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
  if [[ -z "$SID" ]]; then
    echo "SID is required for this command" >&2
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
    api_get "/api/sessions" | jq -r '
      [.[] | select(.attach_mode == "live")][0].id //
      [.[] | select(.controllable == true)][0].id //
      .[0].id //
      empty
    '
    ;;
  state)
    require_auth
    require_sid
    session_state_json | jq
    ;;
  detail)
    require_auth
    require_sid
    api_get "/api/sessions/$SID" | jq
    ;;
  call-id)
    require_auth
    require_sid
    session_state_json | jq -r '.pending_approval.call_id // empty'
    ;;
  request-id)
    require_auth
    require_sid
    session_state_json | jq -r '.pending_input.request_id // empty'
    ;;
  wait-pending-approval)
    require_auth
    require_sid
    wait_until_expr_nonempty '.pending_approval.call_id // empty' "${1:-120}"
    ;;
  wait-pending-input)
    require_auth
    require_sid
    wait_until_expr_nonempty '.pending_input.request_id // empty' "${1:-120}"
    ;;
  wait-clear-approval)
    require_auth
    require_sid
    wait_until_expr_empty '.pending_approval.call_id // empty' "${1:-120}"
    ;;
  wait-clear-input)
    require_auth
    require_sid
    wait_until_expr_empty '.pending_input.request_id // empty' "${1:-120}"
    ;;
  wait-state)
    require_auth
    require_sid
    target_state="${1:-}"
    timeout="${2:-120}"
    if [[ -z "$target_state" ]]; then
      echo "wait-state requires <state>" >&2
      exit 1
    fi
    wait_until_expr_nonempty ".state | select(. == \"$target_state\")" "$timeout" >/dev/null
    ;;
  message)
    require_auth
    require_sid
    content="${1:-}"
    if [[ -z "$content" ]]; then
      echo "message requires text content" >&2
      exit 1
    fi
    api_post "/api/sessions/$SID/message" "$(jq -nc --arg c "$content" '{content:$c}')" | jq
    ;;
  approve)
    require_auth
    require_sid
    call_id="${1:-}"
    if [[ -z "$call_id" ]]; then
      echo "approve requires <call_id>" >&2
      exit 1
    fi
    api_post "/api/sessions/$SID/approve" "$(jq -nc --arg id "$call_id" '{call_id:$id, approved:true}')" | jq
    ;;
  reject)
    require_auth
    require_sid
    call_id="${1:-}"
    if [[ -z "$call_id" ]]; then
      echo "reject requires <call_id>" >&2
      exit 1
    fi
    api_post "/api/sessions/$SID/approve" "$(jq -nc --arg id "$call_id" '{call_id:$id, approved:false}')" | jq
    ;;
  answer)
    require_auth
    require_sid
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
