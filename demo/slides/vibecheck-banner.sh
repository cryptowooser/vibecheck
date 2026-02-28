#!/usr/bin/env bash
# vibecheck logo banner: figlet slant flame gradient + green checkmark (no box)
# Run: bash slides/vibecheck-banner.sh

G='\033[1;38;5;46m'   # bold green
R='\033[0m'            # reset
DIM1='\033[38;5;245m'   # gray
DIM2='\033[38;5;240m'  # darker gray

# Gap between text and checkmark (decrease to bring closer)
PAD=${1:-47}

# Flame gradient colors (top=yellow → bottom=red)
colors=(220 214 208 202 196 196)

# Checkmark (no box) — aligned to figlet line heights
check=(
  "       ▄█"
  "      ██ "
  " ▄   ██  "
  " ▀█▄██   "
  "  ▀██    "
  ""
)

# Capture figlet output
mapfile -t lines < <(figlet -f slant "vibecheck")

echo ""

# Print side by side: figlet text (flame) + gap + checkmark (green)
max=${#lines[@]}
[ ${#check[@]} -gt "$max" ] && max=${#check[@]}

for ((i=0; i<max; i++)); do
  t="${lines[$i]:-}"
  c="${check[$i]:-}"
  fc="${colors[$i]:-196}"
  # Pad text to consistent width
  printf "\033[1;38;5;%dm%-${PAD}s%b%s%b\n" "$fc" "$t" "$G" "$c" "$R"
done

printf "${DIM1}  check your vibes from anywhere${R}\n"
printf "${DIM2} 🔧 approve · 🎤 voice · 🌐 translate · 🔔 notify${R}\n"
echo ""
