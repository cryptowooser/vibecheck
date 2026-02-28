#!/usr/bin/env bash
# Preview pixel fonts for vibecheck logo + pixelated checkmark
# Run: bash slides/logo-pixel-preview.sh
cd "$(dirname "$0")"

render() {
  local name="$1" pngfile="$2"
  echo ""
  echo "━━━ ${name} ━━━"
  chafa --size=80x12 "$pngfile"
  echo ""
}

# --- Pixel font text samples (rendered small, then scaled with nearest-neighbor) ---

# We render at native pixel size then use magick to scale up crisp
pixel_text() {
  local name="$1" fontfamily="$2" fontsize="$3" fontstyle="${4:-normal}" fontweight="${5:-bold}"
  local svgfile="/tmp/vc-pixel-${name}.svg"
  local pngsmall="/tmp/vc-pixel-${name}-small.png"
  local pngbig="/tmp/vc-pixel-${name}.png"

  cat > "$svgfile" << SVGEOF
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 80" width="600" height="80">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="600" height="80" fill="#1a1a1a"/>
  <text x="10" y="55" font-family="${fontfamily}" font-style="${fontstyle}"
        font-size="${fontsize}" font-weight="${fontweight}" fill="url(#flame)">vibecheck</text>
</svg>
SVGEOF

  # Render at native size first
  rsvg-convert -w 600 -h 80 "$svgfile" -o "$pngsmall" 2>/dev/null
  # Scale up 3x with nearest-neighbor for crisp pixels
  magick "$pngsmall" -filter Point -resize 300% "$pngbig" 2>/dev/null
  render "$name" "$pngbig"
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          PIXEL FONT COMPARISON FOR VIBECHECK            ║"
echo "╚══════════════════════════════════════════════════════════╝"

pixel_text "press-start-2p"     "Press Start 2P"     "28"
pixel_text "vt323"              "VT323"              "48"
pixel_text "silkscreen"         "Silkscreen"         "36"
pixel_text "silkscreen-bold"    "Silkscreen"         "36" "normal" "bold"
pixel_text "pixelify-sans"      "Pixelify Sans"      "42"
pixel_text "pixelify-bold"      "Pixelify Sans"      "42" "normal" "bold"
pixel_text "dotgothic16"        "DotGothic16"        "42"

# --- Now with oblique/italic simulation via SVG transform ---
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        OBLIQUE PIXEL FONTS (skewX transform)            ║"
echo "╚══════════════════════════════════════════════════════════╝"

pixel_oblique() {
  local name="$1" fontfamily="$2" fontsize="$3" skew="${4:--12}"
  local svgfile="/tmp/vc-pixel-oblique-${name}.svg"
  local pngsmall="/tmp/vc-pixel-oblique-${name}-small.png"
  local pngbig="/tmp/vc-pixel-oblique-${name}.png"

  cat > "$svgfile" << SVGEOF
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 90" width="650" height="90">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="650" height="90" fill="#1a1a1a"/>
  <text x="30" y="62" font-family="${fontfamily}"
        font-size="${fontsize}" font-weight="bold" fill="url(#flame)"
        transform="skewX(${skew})">vibecheck</text>
</svg>
SVGEOF

  rsvg-convert -w 650 -h 90 "$svgfile" -o "$pngsmall" 2>/dev/null
  magick "$pngsmall" -filter Point -resize 300% "$pngbig" 2>/dev/null
  render "oblique-${name}" "$pngbig"
}

pixel_oblique "press-start-2p"  "Press Start 2P"   "28" "-10"
pixel_oblique "vt323"           "VT323"            "48" "-12"
pixel_oblique "silkscreen"      "Silkscreen"       "36" "-12"
pixel_oblique "pixelify-sans"   "Pixelify Sans"    "42" "-12"
pixel_oblique "dotgothic16"     "DotGothic16"      "42" "-12"

# --- Pixelated checkmark options ---
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           PIXELATED CHECKMARK OPTIONS                   ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Option 1: Hand-drawn pixel checkmark (8x8 grid scaled up)
cat > /tmp/vc-pixelcheck-1.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" width="10" height="10">
  <rect width="10" height="10" fill="#1a1a1a"/>
  <!-- 8x8 pixel checkmark in box -->
  <!-- Box outline -->
  <rect x="0" y="0" width="10" height="10" fill="none" stroke="#44DD44" stroke-width="1"/>
  <!-- Checkmark pixels -->
  <rect x="7" y="2" width="1" height="1" fill="#44DD44"/>
  <rect x="6" y="3" width="1" height="1" fill="#44DD44"/>
  <rect x="5" y="4" width="1" height="1" fill="#44DD44"/>
  <rect x="4" y="5" width="1" height="1" fill="#44DD44"/>
  <rect x="2" y="4" width="1" height="1" fill="#44DD44"/>
  <rect x="3" y="5" width="1" height="1" fill="#44DD44"/>
  <!-- thicken -->
  <rect x="7" y="3" width="1" height="1" fill="#44DD44"/>
  <rect x="6" y="4" width="1" height="1" fill="#44DD44"/>
  <rect x="5" y="5" width="1" height="1" fill="#44DD44"/>
  <rect x="3" y="4" width="1" height="1" fill="#44DD44"/>
</svg>
SVGEOF
rsvg-convert -w 10 -h 10 /tmp/vc-pixelcheck-1.svg -o /tmp/vc-pixelcheck-1-tiny.png 2>/dev/null
magick /tmp/vc-pixelcheck-1-tiny.png -filter Point -resize 1600% /tmp/vc-pixelcheck-1.png 2>/dev/null
render "pixel-check-8x8-box" /tmp/vc-pixelcheck-1.png

# Option 2: Larger pixel checkmark (16x16)
cat > /tmp/vc-pixelcheck-2.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
  <rect width="16" height="16" fill="#1a1a1a"/>
  <!-- Rounded-ish box -->
  <rect x="1" y="1" width="14" height="14" rx="1" ry="1" fill="none" stroke="#44DD44" stroke-width="1"/>
  <!-- Checkmark: thick 2px stroke feel -->
  <rect x="11" y="3" width="2" height="2" fill="#44DD44"/>
  <rect x="10" y="4" width="2" height="2" fill="#44DD44"/>
  <rect x="9" y="5" width="2" height="2" fill="#44DD44"/>
  <rect x="8" y="6" width="2" height="2" fill="#44DD44"/>
  <rect x="7" y="7" width="2" height="2" fill="#44DD44"/>
  <rect x="6" y="8" width="2" height="2" fill="#44DD44"/>
  <rect x="5" y="9" width="2" height="2" fill="#44DD44"/>
  <rect x="3" y="7" width="2" height="2" fill="#44DD44"/>
  <rect x="4" y="8" width="2" height="2" fill="#44DD44"/>
</svg>
SVGEOF
rsvg-convert -w 16 -h 16 /tmp/vc-pixelcheck-2.svg -o /tmp/vc-pixelcheck-2-tiny.png 2>/dev/null
magick /tmp/vc-pixelcheck-2-tiny.png -filter Point -resize 1000% /tmp/vc-pixelcheck-2.png 2>/dev/null
render "pixel-check-16x16-box" /tmp/vc-pixelcheck-2.png

# Option 3: Filled green box, white pixel check (emoji-✅ style)
cat > /tmp/vc-pixelcheck-3.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
  <rect width="16" height="16" fill="#1a1a1a"/>
  <!-- Filled green box -->
  <rect x="1" y="1" width="14" height="14" rx="2" ry="2" fill="#22AA22"/>
  <!-- White checkmark pixels -->
  <rect x="11" y="3" width="2" height="2" fill="white"/>
  <rect x="10" y="4" width="2" height="2" fill="white"/>
  <rect x="9" y="5" width="2" height="2" fill="white"/>
  <rect x="8" y="6" width="2" height="2" fill="white"/>
  <rect x="7" y="7" width="2" height="2" fill="white"/>
  <rect x="6" y="8" width="2" height="2" fill="white"/>
  <rect x="5" y="9" width="2" height="2" fill="white"/>
  <rect x="3" y="7" width="2" height="2" fill="white"/>
  <rect x="4" y="8" width="2" height="2" fill="white"/>
</svg>
SVGEOF
rsvg-convert -w 16 -h 16 /tmp/vc-pixelcheck-3.svg -o /tmp/vc-pixelcheck-3-tiny.png 2>/dev/null
magick /tmp/vc-pixelcheck-3-tiny.png -filter Point -resize 1000% /tmp/vc-pixelcheck-3.png 2>/dev/null
render "pixel-check-filled-green" /tmp/vc-pixelcheck-3.png

# Option 4: No box, just a bold pixel checkmark
cat > /tmp/vc-pixelcheck-4.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 12" width="14" height="12">
  <rect width="14" height="12" fill="#1a1a1a"/>
  <!-- Bold pixel checkmark, no box -->
  <rect x="10" y="1" width="2" height="2" fill="#44DD44"/>
  <rect x="11" y="0" width="2" height="2" fill="#44DD44"/>
  <rect x="9" y="2" width="2" height="2" fill="#44DD44"/>
  <rect x="8" y="3" width="2" height="2" fill="#44DD44"/>
  <rect x="7" y="4" width="2" height="2" fill="#44DD44"/>
  <rect x="6" y="5" width="2" height="2" fill="#44DD44"/>
  <rect x="5" y="6" width="2" height="2" fill="#44DD44"/>
  <rect x="4" y="7" width="2" height="2" fill="#44DD44"/>
  <rect x="3" y="8" width="2" height="2" fill="#44DD44"/>
  <rect x="1" y="5" width="2" height="2" fill="#44DD44"/>
  <rect x="2" y="6" width="2" height="2" fill="#44DD44"/>
  <rect x="3" y="7" width="2" height="2" fill="#44DD44"/>
</svg>
SVGEOF
rsvg-convert -w 14 -h 12 /tmp/vc-pixelcheck-4.svg -o /tmp/vc-pixelcheck-4-tiny.png 2>/dev/null
magick /tmp/vc-pixelcheck-4-tiny.png -filter Point -resize 1200% /tmp/vc-pixelcheck-4.png 2>/dev/null
render "pixel-check-no-box" /tmp/vc-pixelcheck-4.png

# --- Combined: pixel checkmark + pixel font text ---
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        COMBINED: PIXEL CHECK + PIXEL TEXT               ║"
echo "╚══════════════════════════════════════════════════════════╝"

combo() {
  local name="$1" fontfamily="$2" fontsize="$3" oblique="${4:-no}"
  local svgfile="/tmp/vc-combo-${name}.svg"
  local pngsmall="/tmp/vc-combo-${name}-small.png"
  local pngbig="/tmp/vc-combo-${name}.png"
  local transform=""
  [ "$oblique" = "yes" ] && transform='transform="skewX(-10)"'

  cat > "$svgfile" << SVGEOF
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 16" width="48" height="16"
     shape-rendering="crispEdges" image-rendering="pixelated">
  <defs>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FF4500"/>
      <stop offset="40%" stop-color="#FF7000"/>
      <stop offset="100%" stop-color="#FFB800"/>
    </linearGradient>
  </defs>
  <rect width="48" height="16" fill="#1a1a1a"/>
  <!-- Pixel checkmark box -->
  <rect x="1" y="1" width="14" height="14" rx="1" ry="1" fill="none" stroke="#44DD44" stroke-width="1"/>
  <rect x="11" y="3" width="2" height="2" fill="#44DD44"/>
  <rect x="10" y="4" width="2" height="2" fill="#44DD44"/>
  <rect x="9" y="5" width="2" height="2" fill="#44DD44"/>
  <rect x="8" y="6" width="2" height="2" fill="#44DD44"/>
  <rect x="7" y="7" width="2" height="2" fill="#44DD44"/>
  <rect x="6" y="8" width="2" height="2" fill="#44DD44"/>
  <rect x="5" y="9" width="2" height="2" fill="#44DD44"/>
  <rect x="3" y="7" width="2" height="2" fill="#44DD44"/>
  <rect x="4" y="8" width="2" height="2" fill="#44DD44"/>
  <!-- Text -->
  <text x="18" y="13" font-family="${fontfamily}" font-size="${fontsize}"
        font-weight="bold" fill="url(#flame)" ${transform}>vibecheck</text>
</svg>
SVGEOF

  rsvg-convert -w 480 -h 160 "$svgfile" -o "$pngsmall" 2>/dev/null
  magick "$pngsmall" -filter Point -resize 300% "$pngbig" 2>/dev/null
  render "combo-${name}" "$pngbig"
}

combo "press-start"       "Press Start 2P"   "8"
combo "silkscreen"        "Silkscreen"        "11"
combo "vt323"             "VT323"             "14"
combo "pixelify"          "Pixelify Sans"     "12"
combo "press-start-obl"   "Press Start 2P"    "8"  "yes"
combo "silkscreen-obl"    "Silkscreen"        "11" "yes"
combo "pixelify-obl"      "Pixelify Sans"     "12" "yes"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PNGs saved to /tmp/vc-pixel-*.png and /tmp/vc-combo-*.png"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
