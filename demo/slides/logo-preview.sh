#!/usr/bin/env bash
# Preview vibecheck logo options in terminal
# Run: bash slides/logo-preview.sh

echo ""
echo "━━━ Option 1: slant + flame gradient (tips up) ━━━"
echo ""
colors=(220 214 208 202 196 196)
i=0
figlet -f slant "vibecheck" | while IFS= read -r line; do
  color=${colors[$i]}
  [ -z "$color" ] && color=196
  printf '\033[38;5;%dm%s\033[0m\n' "$color" "$line"
  ((i++))
done

echo ""
echo "━━━ Option 2: slant + bold Mistral orange ━━━"
echo ""
printf '\033[1;38;5;208m'
figlet -f slant "vibecheck"
printf '\033[0m'

echo ""
echo "━━━ Option 3: smslant + flame gradient (compact) ━━━"
echo ""
colors=(220 214 208 202 196)
i=0
figlet -f smslant "vibecheck" | while IFS= read -r line; do
  color=${colors[$i]}
  [ -z "$color" ] && color=196
  printf '\033[38;5;%dm%s\033[0m\n' "$color" "$line"
  ((i++))
done

echo ""
echo "━━━ Option 4: slant + Mistral orange w/ tagline ━━━"
echo ""
printf '\033[1;38;5;208m'
figlet -f slant "vibecheck"
printf '\033[0m'
printf '\033[38;5;245m        check your vibes from anywhere\033[0m\n'
printf '\033[38;5;240m        🔧 approve · 🎤 voice · 🌐 translate · 🔔 notify\033[0m\n'

echo ""
echo "━━━ Option 5: slant + flame gradient w/ tagline ━━━"
echo ""
colors=(220 214 208 202 196 196)
i=0
figlet -f slant "vibecheck" | while IFS= read -r line; do
  color=${colors[$i]}
  [ -z "$color" ] && color=196
  printf '\033[38;5;%dm%s\033[0m\n' "$color" "$line"
  ((i++))
done
printf '\033[38;5;245m        check your vibes from anywhere\033[0m\n'
printf '\033[38;5;240m        🔧 approve · 🎤 voice · 🌐 translate · 🔔 notify\033[0m\n'

echo ""
