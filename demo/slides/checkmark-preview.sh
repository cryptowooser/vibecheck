#!/usr/bin/env bash
# Preview green checkmark box options
# Run: bash slides/checkmark-preview.sh

G='\033[38;5;46m'   # green
BG='\033[1;38;5;46m' # bold green
O='\033[1;38;5;208m' # bold orange
DIM='\033[38;5;245m' # gray
R='\033[0m'          # reset

echo ""
echo "━━━ Option A: Thick checkmark in rounded box ━━━"
echo ""
printf "${G} ╭──────────────╮${R}\n"
printf "${G} │              │${R}\n"
printf "${G} │          ██  │${R}\n"
printf "${G} │         ██   │${R}\n"
printf "${G} │   ██   ██    │${R}\n"
printf "${G} │    ██ ██     │${R}\n"
printf "${G} │     ███      │${R}\n"
printf "${G} │              │${R}\n"
printf "${G} ╰──────────────╯${R}\n"

echo ""
echo "━━━ Option B: Double-line box, thick check ━━━"
echo ""
printf "${G} ╔══════════════╗${R}\n"
printf "${G} ║           ▄█ ║${R}\n"
printf "${G} ║          ██  ║${R}\n"
printf "${G} ║    ▄█   ██   ║${R}\n"
printf "${G} ║     ▀█▄██    ║${R}\n"
printf "${G} ║      ▀██     ║${R}\n"
printf "${G} ╚══════════════╝${R}\n"

echo ""
echo "━━━ Option C: Heavy blocks in square ━━━"
echo ""
printf "${G} ████████████████${R}\n"
printf "${G} ██           ██${R}\n"
printf "${G} ██        █▄ ██${R}\n"
printf "${G} ██       ██  ██${R}\n"
printf "${G} ██  █▄  ██   ██${R}\n"
printf "${G} ██   ▀███    ██${R}\n"
printf "${G} ██           ██${R}\n"
printf "${G} ████████████████${R}\n"

echo ""
echo "━━━ Option D: Minimal checkmark (no box) ━━━"
echo ""
printf "${BG}            ██${R}\n"
printf "${BG}           ██${R}\n"
printf "${BG}     ██   ██${R}\n"
printf "${BG}      ██ ██${R}\n"
printf "${BG}       ███${R}\n"

echo ""
echo "━━━ Option E: Filled box with negative-space check ━━━"
echo ""
printf "${G} ████████████████${R}\n"
printf "${G} ████████████ ██${R}\n"
printf "${G} ███████████  ██${R}\n"
printf "${G} ████  ████  ███${R}\n"
printf "${G} █████  ██  ████${R}\n"
printf "${G} ██████  █ █████${R}\n"
printf "${G} ███████  ██████${R}\n"
printf "${G} ████████████████${R}\n"

echo ""
echo "━━━ Combined: Option B + slant text (side by side) ━━━"
echo ""
# Side by side rendering
mapfile -t text_lines < <(figlet -f slant "vibecheck")

check=( \
  " ╔══════════════╗  " \
  " ║           ▄█ ║  " \
  " ║          ██  ║  " \
  " ║    ▄█   ██   ║  " \
  " ║     ▀█▄██    ║  " \
  " ║      ▀██     ║  " \
  " ╚══════════════╝  " \
)

pad="                    "
max=${#text_lines[@]}
[ ${#check[@]} -gt "$max" ] && max=${#check[@]}

for ((i=0; i<max; i++)); do
  c="${check[$i]:-$pad}"
  t="${text_lines[$i]:-}"
  printf "${G}%s${O}%s${R}\n" "$c" "$t"
done
printf "${DIM}                    check your vibes from anywhere${R}\n"

echo ""
echo "━━━ Combined: Option A + flame gradient text (side by side) ━━━"
echo ""

check2=( \
  " ╭──────────────╮  " \
  " │              │  " \
  " │          ██  │  " \
  " │         ██   │  " \
  " │   ██   ██    │  " \
  " │    ██ ██     │  " \
  " │     ███      │  " \
  " │              │  " \
  " ╰──────────────╯  " \
)

mapfile -t text_lines2 < <(figlet -f slant "vibecheck")
flame=(220 220 214 208 202 196 196 196 196)

pad2="                    "
max2=${#text_lines2[@]}
[ ${#check2[@]} -gt "$max2" ] && max2=${#check2[@]}

for ((i=0; i<max2; i++)); do
  c="${check2[$i]:-$pad2}"
  t="${text_lines2[$i]:-}"
  fc="${flame[$i]:-196}"
  printf "${G}%s\033[1;38;5;%dm%s${R}\n" "$c" "$fc" "$t"
done
printf "${DIM}                    check your vibes from anywhere${R}\n"

echo ""
