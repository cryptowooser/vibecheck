#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: tui_prompts.sh <scenario>

Scenarios:
  list
  approve
  reject
  question
  race
  reconnect
  running
EOF
}

print_prompt() {
  local scenario="$1"
  case "$scenario" in
    approve)
      cat <<'EOF'
Run exactly this in the TUI:
Create a tiny file at /tmp/wu34-approve.txt containing "ok", then read it back with read_file.
If any tool approval appears, wait for phone approval.
EOF
      ;;
    reject)
      cat <<'EOF'
Run exactly this in the TUI:
Run bash: `echo WU34_REJECT_SHOULD_NOT_RUN`
If approval appears, reject it from the phone.
EOF
      ;;
    question)
      cat <<'EOF'
Run exactly this in the TUI:
Use ask_user_question with one question:
- question: "WU34 question flow check: continue?"
- options: "Continue" and "Stop"
Then:
- if Continue: run bash `echo WU34_Q_CONTINUE`
- if Stop: respond `WU34_Q_STOP`
EOF
      ;;
    race)
      cat <<'EOF'
Run exactly this in the TUI:
Run bash: `echo WU34_RACE_TEST`
When approval appears, resolve nearly simultaneously on both surfaces:
- terminal keyboard (approve/reject)
- phone approval panel
EOF
      ;;
    reconnect)
      cat <<'EOF'
Run exactly this in the TUI:
Run bash: `echo WU34_RECONNECT_TEST`
When approval appears:
- disconnect/close phone PWA first
- reconnect phone
- then resolve from phone
EOF
      ;;
    running)
      cat <<'EOF'
Run exactly this in the TUI:
Run bash:
for i in 1 2 3 4 5; do echo WU34_TICK_$i; sleep 1; done
While running, type and submit another short prompt to verify no wedge/deadlock.
EOF
      ;;
    list)
      cat <<'EOF'
approve
reject
question
race
reconnect
running
EOF
      ;;
    *)
      echo "unknown scenario: $scenario" >&2
      usage
      exit 1
      ;;
  esac
}

scenario="${1:-}"
if [[ -z "$scenario" || "$scenario" == "--help" || "$scenario" == "-h" ]]; then
  usage
  exit 0
fi

print_prompt "$scenario"
