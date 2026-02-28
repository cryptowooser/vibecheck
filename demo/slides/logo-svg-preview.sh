#!/usr/bin/env bash
# Generate and preview multiple SVG logo variants in terminal via chafa
# Run: bash slides/logo-svg-preview.sh
cd "$(dirname "$0")"

render() {
  local name="$1" svgfile="$2"
  echo ""
  echo "━━━ ${name} ━━━"
  rsvg-convert -w 1600 -h 400 "$svgfile" -o "/tmp/vibecheck-${name}.png" 2>/dev/null
  chafa --size=80x12 "/tmp/vibecheck-${name}.png"
  echo ""
}

# --- Variant 1: Unicode ☑ checkbox + Hack Bold ---
cat > /tmp/vc-v1.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" fill="#1a1a1a"/>
  <text x="10" y="145" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="150" fill="#44DD44">☑</text>
  <text x="170" y="135" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="100" font-weight="bold" fill="url(#flame)">vibecheck</text>
</svg>
EOF
render "v1-unicode-checkbox-hack" /tmp/vc-v1.svg

# --- Variant 2: Unicode ✓ checkmark + Inconsolata Black ---
cat > /tmp/vc-v2.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" fill="#1a1a1a"/>
  <!-- Green box -->
  <rect x="15" y="25" width="130" height="130" rx="15" ry="15"
        fill="none" stroke="#44DD44" stroke-width="8"/>
  <!-- Big checkmark glyph inside -->
  <text x="28" y="140" font-family="DejaVu Sans, sans-serif"
        font-size="140" fill="#44DD44">✓</text>
  <text x="175" y="130" font-family="Inconsolata, Hack, monospace"
        font-size="96" font-weight="900" fill="url(#flame)">vibecheck</text>
</svg>
EOF
render "v2-checkmark-in-box" /tmp/vc-v2.svg

# --- Variant 3: ✅ emoji-style + FantasqueSansM ---
cat > /tmp/vc-v3.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" fill="#1a1a1a"/>
  <!-- Filled green rounded square -->
  <rect x="15" y="25" width="135" height="135" rx="22" ry="22" fill="#22AA22"/>
  <!-- White checkmark -->
  <polyline points="42,95 68,125 130,50"
            fill="none" stroke="white" stroke-width="16"
            stroke-linecap="round" stroke-linejoin="round"/>
  <text x="180" y="132" font-family="FantasqueSansM Nerd Font, Hack, monospace"
        font-size="100" font-weight="bold" fill="url(#flame)">vibecheck</text>
</svg>
EOF
render "v3-filled-green-box-white-check" /tmp/vc-v3.svg

# --- Variant 4: Outlined green check + flame text, with tagline ---
cat > /tmp/vc-v4.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 220" width="900" height="220">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
    <linearGradient id="greenG" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#66FF66"/>
      <stop offset="100%" stop-color="#00BB00"/>
    </linearGradient>
  </defs>
  <rect width="900" height="220" fill="#1a1a1a"/>
  <!-- Rounded green border box -->
  <rect x="15" y="22" width="130" height="130" rx="18" ry="18"
        fill="none" stroke="url(#greenG)" stroke-width="7"/>
  <!-- SVG checkmark path -->
  <polyline points="40,88 62,115 118,48"
            fill="none" stroke="url(#greenG)" stroke-width="13"
            stroke-linecap="round" stroke-linejoin="round"/>
  <text x="175" y="125" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="94" font-weight="bold" fill="url(#flame)"
        letter-spacing="-1">vibecheck</text>
  <text x="178" y="170" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="22" fill="#777777">check your vibes from anywhere</text>
</svg>
EOF
render "v4-outlined-check-with-tagline" /tmp/vc-v4.svg

# --- Variant 5: Nerd Font checkbox icon + compact ---
cat > /tmp/vc-v5.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 180" width="900" height="180">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="180" fill="#1a1a1a"/>
  <!-- Unicode ballot box with check -->
  <text x="5" y="130" font-family="FantasqueSansM Nerd Font, DejaVu Sans, sans-serif"
        font-size="150" fill="#44DD44">☑</text>
  <text x="150" y="120" font-family="Hack, monospace"
        font-size="88" font-weight="bold" fill="url(#flame)">vibecheck</text>
</svg>
EOF
render "v5-ballot-box-nerd-font" /tmp/vc-v5.svg

# --- Variant 6: Solid orange text, green check, no gradient (clean/flat) ---
cat > /tmp/vc-v6.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 180" width="900" height="180">
  <rect width="900" height="180" fill="#1a1a1a"/>
  <!-- Simple green outlined box with check -->
  <rect x="18" y="20" width="120" height="120" rx="14" ry="14"
        fill="none" stroke="#44DD44" stroke-width="6"/>
  <polyline points="42,82 60,105 110,42"
            fill="none" stroke="#44DD44" stroke-width="12"
            stroke-linecap="round" stroke-linejoin="round"/>
  <!-- Solid Mistral orange -->
  <text x="168" y="115" font-family="Hack, monospace"
        font-size="88" font-weight="bold" fill="#FF7000">vibecheck</text>
</svg>
EOF
render "v6-flat-orange-green" /tmp/vc-v6.svg

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PNGs saved to /tmp/vibecheck-*.png"
echo "SVGs in /tmp/vc-v*.svg"
echo "To view full-res in Ghostty: chafa --format=kitty /tmp/vibecheck-v4-outlined-check-with-tagline.png"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
