#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./android-mirroring.sh [options] [-- <extra scrcpy args>]

What this script does:
  - Verifies `adb` and `scrcpy` are installed.
  - Starts the ADB server if needed.
  - Waits for an authorized device (`device` state).
  - Launches scrcpy with sensible defaults.

Defaults:
  - Audio forwarding: ON (remove only with --no-audio)
  - Phone screen: ON (set --screen-off to disable phone display)
  - Stay awake while mirroring: ON
  - Borderless window: ON
  - Max size / FPS / bitrate: 1080 / 60 / 8M

Options:
  -h, --help                 Show this help.
  --dry-run                  Print the final scrcpy command and exit.
  --serial <serial>          Device serial to use (required if multiple devices are attached).
  --wireless <ip[:port]>     Run `adb connect` first and mirror that target (default port: 5555).
  --wait-seconds <n>         Wait up to n seconds for a ready device (default: 20).
  --title <text>             Window title (default: "vibecheck").
  --max-size <n>             scrcpy --max-size (default: 1080).
  --max-fps <n>              scrcpy --max-fps (default: 60).
  --bit-rate <value>         scrcpy --video-bit-rate (default: 8M).
  --no-audio                 Disable forwarding Android audio to laptop.
  --screen-off               Turn the phone screen off while mirroring.
  --no-screen-off            Keep phone screen on (default; better for handheld demos).
  --stay-awake               Keep phone awake while mirroring (default).
  --no-stay-awake            Do not force stay-awake.
  --borderless               Borderless window (default).
  --no-borderless            Keep normal window decorations.

Examples:
  # Live demo, interactive on-device, with audio to laptop/projector:
  ./android-mirroring.sh --title "vibecheck - Pixel 7"

  # Demo where phone screen should stay off:
  ./android-mirroring.sh --screen-off --no-audio

  # Wireless session:
  ./android-mirroring.sh --wireless 192.168.1.42:5555
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "error: required command not found: $cmd" >&2
    exit 1
  fi
}

require_opt_value() {
  local opt="$1"
  if (( $# < 2 )) || [[ -z "${2:-}" ]]; then
    echo "error: $opt requires a value." >&2
    exit 1
  fi
}

list_device_states() {
  adb devices | awk 'NR > 1 && NF >= 2 { print $1 " " $2 }'
}

wait_for_ready_device() {
  local timeout="$1"
  local target_serial="${2:-}"
  local deadline=$((SECONDS + timeout))

  while (( SECONDS < deadline )); do
    local found_device=0
    local state=""
    local serial=""

    if [[ -n "$target_serial" ]]; then
      state="$(adb devices | awk -v s="$target_serial" '$1 == s { print $2 }')"
      if [[ "$state" == "device" ]]; then
        echo "$target_serial"
        return 0
      fi
    else
      while read -r serial state; do
        if [[ "$state" == "device" ]]; then
          if (( found_device == 1 )); then
            echo "error: multiple devices detected; pass --serial to select one." >&2
            adb devices -l >&2 || true
            exit 1
          fi
          found_device=1
          target_serial="$serial"
        fi
      done < <(list_device_states)

      if (( found_device == 1 )); then
        echo "$target_serial"
        return 0
      fi
    fi

    sleep 1
  done

  if [[ -n "$target_serial" ]]; then
    state="$(adb devices | awk -v s="$target_serial" '$1 == s { print $2 }')"
    case "$state" in
      unauthorized)
        echo "error: device $target_serial is unauthorized. Unlock phone and accept the RSA prompt." >&2
        ;;
      offline)
        echo "error: device $target_serial is offline. Reconnect USB and retry." >&2
        ;;
      "")
        echo "error: device $target_serial not found in 'adb devices' output." >&2
        ;;
      *)
        echo "error: device $target_serial is in state '$state'." >&2
        ;;
    esac
  else
    if adb devices | awk 'NR > 1 { print $2 }' | grep -q '^unauthorized$'; then
      echo "error: adb sees an unauthorized device. Unlock phone and accept the RSA prompt." >&2
    elif adb devices | awk 'NR > 1 { print $2 }' | grep -q '^offline$'; then
      echo "error: adb sees an offline device. Reconnect USB and retry." >&2
    else
      echo "error: no ready adb device after ${timeout}s." >&2
    fi
  fi

  adb devices -l >&2 || true
  exit 1
}

main() {
  require_cmd adb
  require_cmd scrcpy

  local title="vibecheck"
  local max_size="1080"
  local max_fps="60"
  local bit_rate="8M"
  local wait_seconds="20"
  local serial=""
  local wireless=""
  local dry_run=0
  local audio_enabled=1
  local screen_off=0
  local stay_awake=1
  local borderless=1
  local -a passthrough=()

  while (( $# > 0 )); do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      --serial)
        require_opt_value "$1" "${2:-}"
        serial="${2:-}"
        shift 2
        ;;
      --wireless)
        require_opt_value "$1" "${2:-}"
        wireless="${2:-}"
        shift 2
        ;;
      --wait-seconds)
        require_opt_value "$1" "${2:-}"
        wait_seconds="${2:-}"
        shift 2
        ;;
      --title)
        require_opt_value "$1" "${2:-}"
        title="${2:-}"
        shift 2
        ;;
      --max-size)
        require_opt_value "$1" "${2:-}"
        max_size="${2:-}"
        shift 2
        ;;
      --max-fps)
        require_opt_value "$1" "${2:-}"
        max_fps="${2:-}"
        shift 2
        ;;
      --bit-rate)
        require_opt_value "$1" "${2:-}"
        bit_rate="${2:-}"
        shift 2
        ;;
      --no-audio)
        audio_enabled=0
        shift
        ;;
      --screen-off)
        screen_off=1
        shift
        ;;
      --no-screen-off)
        screen_off=0
        shift
        ;;
      --stay-awake)
        stay_awake=1
        shift
        ;;
      --no-stay-awake)
        stay_awake=0
        shift
        ;;
      --borderless)
        borderless=1
        shift
        ;;
      --no-borderless)
        borderless=0
        shift
        ;;
      --)
        shift
        passthrough+=("$@")
        break
        ;;
      *)
        echo "error: unknown option: $1" >&2
        echo "run './android-mirroring.sh --help' for usage." >&2
        exit 1
        ;;
    esac
  done

  if [[ -z "$wait_seconds" || ! "$wait_seconds" =~ ^[0-9]+$ ]]; then
    echo "error: --wait-seconds must be a non-negative integer." >&2
    exit 1
  fi

  if [[ -n "$wireless" && -z "$serial" ]]; then
    serial="$wireless"
  fi

  adb start-server >/dev/null 2>&1 || true

  if [[ -n "$wireless" ]]; then
    local connect_out=""
    connect_out="$(adb connect "$wireless" 2>&1 || true)"
    if [[ "$connect_out" != *"connected to"* && "$connect_out" != *"already connected to"* ]]; then
      echo "warning: adb connect did not report success for $wireless" >&2
      echo "$connect_out" >&2
    fi
  fi

  local selected_serial=""
  selected_serial="$(wait_for_ready_device "$wait_seconds" "$serial")"

  local -a cmd=(
    scrcpy
    --serial="$selected_serial"
    --window-title="$title"
    --max-size="$max_size"
    --max-fps="$max_fps"
    --video-bit-rate="$bit_rate"
  )

  if (( borderless == 1 )); then
    cmd+=(--window-borderless)
  fi
  if (( audio_enabled == 0 )); then
    cmd+=(--no-audio)
  fi
  if (( stay_awake == 1 )); then
    cmd+=(--stay-awake)
  fi
  if (( screen_off == 1 )); then
    cmd+=(--turn-screen-off)
  fi
  if (( ${#passthrough[@]} > 0 )); then
    cmd+=("${passthrough[@]}")
  fi

  echo "Using adb device: $selected_serial"
  printf 'Launching: '
  printf '%q ' "${cmd[@]}"
  echo

  if (( dry_run == 1 )); then
    exit 0
  fi

  exec "${cmd[@]}"
}

main "$@"
