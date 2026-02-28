#!/usr/bin/env bash
# Preview additional Unicode check variants in SVG → terminal
# Run: bash slides/logo-svg-preview2.sh
cd "$(dirname "$0")"

render() {
  local name="$1" svgfile="$2"
  echo ""
  echo "━━━ ${name} ━━━"
  rsvg-convert -w 1600 -h 400 "$svgfile" -o "/tmp/vibecheck-${name}.png" 2>/dev/null
  chafa --size=80x12 "/tmp/vibecheck-${name}.png"
  echo ""
}

# All check variants as standalone glyphs first (to see which renders best)
cat > /tmp/vc-glyphs.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 200" width="1000" height="200">
  <rect width="1000" height="200" fill="#1a1a1a"/>
  <text x="10" y="55" font-family="DejaVu Sans, sans-serif" font-size="20" fill="#888">☑ U+2611      ✓ U+2713       ✔ U+2714       🗹 U+1F5F9      ✅ emoji</text>
  <text x="10" y="160" font-family="DejaVu Sans, sans-serif" font-size="120" fill="#44DD44">☑</text>
  <text x="180" y="160" font-family="DejaVu Sans, sans-serif" font-size="120" fill="#44DD44">✓</text>
  <text x="330" y="160" font-family="DejaVu Sans, sans-serif" font-size="120" fill="#44DD44">✔</text>
  <text x="480" y="160" font-family="DejaVu Sans, sans-serif" font-size="120" fill="#44DD44">🗹</text>
  <text x="680" y="160" font-family="Noto Color Emoji, Apple Color Emoji, sans-serif" font-size="120">✅</text>
</svg>
SVGEOF
render "glyph-comparison" /tmp/vc-glyphs.svg

# --- 🗹 U+1F5F9 BALLOT BOX WITH BOLD CHECK ---
cat > /tmp/vc-ballot-bold.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" fill="#1a1a1a"/>
  <text x="5" y="155" font-family="DejaVu Sans, Noto Sans, sans-serif"
        font-size="160" fill="#44DD44">🗹</text>
  <text x="185" y="130" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="94" font-weight="bold" fill="url(#flame)">vibecheck</text>
</svg>
SVGEOF
render "ballot-bold-check" /tmp/vc-ballot-bold.svg

# --- ✔ U+2714 HEAVY CHECK MARK (standalone, no box — we draw the box) ---
cat > /tmp/vc-heavy-check-box.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" fill="#1a1a1a"/>
  <rect x="12" y="18" width="140" height="140" rx="16" ry="16"
        fill="none" stroke="#44DD44" stroke-width="7"/>
  <text x="22" y="152" font-family="DejaVu Sans, sans-serif"
        font-size="145" fill="#44DD44">✔</text>
  <text x="180" y="130" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="94" font-weight="bold" fill="url(#flame)">vibecheck</text>
</svg>
SVGEOF
render "heavy-check-in-drawn-box" /tmp/vc-heavy-check-box.svg

# --- ✔ in filled green box (emoji-✅ style but with the heavy check glyph) ---
cat > /tmp/vc-heavy-filled.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" fill="#1a1a1a"/>
  <rect x="12" y="18" width="140" height="140" rx="22" ry="22" fill="#22AA22"/>
  <text x="22" y="148" font-family="DejaVu Sans, sans-serif"
        font-size="135" fill="white">✔</text>
  <text x="180" y="130" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="94" font-weight="bold" fill="url(#flame)">vibecheck</text>
</svg>
SVGEOF
render "heavy-check-filled-green" /tmp/vc-heavy-filled.svg

# --- ☑ U+2611 BALLOT BOX WITH CHECK (the OG) ---
cat > /tmp/vc-ballot-og.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" fill="#1a1a1a"/>
  <text x="5" y="155" font-family="DejaVu Sans, Noto Sans, sans-serif"
        font-size="160" fill="#44DD44">☑</text>
  <text x="175" y="130" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="94" font-weight="bold" fill="url(#flame)">vibecheck</text>
</svg>
SVGEOF
render "ballot-box-check-og" /tmp/vc-ballot-og.svg

# --- ☑ with tagline ---
cat > /tmp/vc-ballot-tag.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 220" width="900" height="220">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="220" fill="#1a1a1a"/>
  <text x="5" y="148" font-family="DejaVu Sans, Noto Sans, sans-serif"
        font-size="155" fill="#44DD44">☑</text>
  <text x="172" y="125" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="90" font-weight="bold" fill="url(#flame)">vibecheck</text>
  <text x="175" y="168" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="22" fill="#777">check your vibes from anywhere</text>
</svg>
SVGEOF
render "ballot-box-with-tagline" /tmp/vc-ballot-tag.svg

# --- 🗹 with tagline ---
cat > /tmp/vc-bold-ballot-tag.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 220" width="900" height="220">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="900" height="220" fill="#1a1a1a"/>
  <text x="2" y="150" font-family="DejaVu Sans, Noto Sans, sans-serif"
        font-size="155" fill="#44DD44">🗹</text>
  <text x="178" y="125" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="90" font-weight="bold" fill="url(#flame)">vibecheck</text>
  <text x="181" y="168" font-family="Hack, DejaVu Sans Mono, monospace"
        font-size="22" fill="#777">check your vibes from anywhere</text>
</svg>
SVGEOF
render "bold-ballot-with-tagline" /tmp/vc-bold-ballot-tag.svg

# --- Flat/clean: ✔ in box, solid orange (no gradient) ---
cat > /tmp/vc-flat-clean.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200" width="900" height="200">
  <rect width="900" height="200" fill="#1a1a1a"/>
  <rect x="12" y="20" width="135" height="135" rx="16" ry="16"
        fill="none" stroke="#44DD44" stroke-width="6"/>
  <text x="20" y="148" font-family="DejaVu Sans, sans-serif"
        font-size="140" fill="#44DD44">✔</text>
  <text x="175" y="125" font-family="Hack, monospace"
        font-size="90" font-weight="bold" fill="#FF7000">vibecheck</text>
</svg>
SVGEOF
render "flat-heavy-check-solid-orange" /tmp/vc-flat-clean.svg

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PNGs saved to /tmp/vibecheck-*.png"
echo "Full-res preview: chafa /tmp/vibecheck-<name>.png"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
