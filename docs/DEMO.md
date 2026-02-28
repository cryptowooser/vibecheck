# vibecheck — check your vibes from anywhere — Demo Script & Setup

> **Last updated:** 2026-02-28
> **Hardware:** Linux desktop (Niri compositor) + Pixel 9 Android dev phone
> **Screen layout:** presenterm (terminal slides) → then 50% terminal / 50% scrcpy
> **Slides:** presenterm (primary, terminal-native) + Slidev PDF (backup/handout)

---

## Table of Contents

- [Equipment & Setup](#equipment--setup)
- [Screen Layout](#screen-layout)
- [Pre-Demo Checklist](#pre-demo-checklist)
- [Demo Script](#demo-script)
- [Fallback Plan](#fallback-plan)

---

## Equipment & Setup

### presenterm (Terminal Slides)

**Install on Arch Linux:**
```bash
sudo pacman -S presenterm
# or: cargo install presenterm
```

**Key features for Ghostty:**
- Inline images via Kitty graphics protocol (Ghostty supports this natively)
- Mermaid diagram rendering (renders to PNG → displays inline)
- Syntax-highlighted code blocks
- Speaker notes (visible in presenter mode)
- Seamless transition: quit slides → you're in the same terminal → run Vibe

**Create slides:**
```markdown
---
title: vibecheck
theme:
  name: dark
---

# vibecheck

check your vibes from anywhere

<!-- end_slide -->

## Vibe from anywhere

- TUI Agentic Coding is great
- Agents should keep working even if you're not at your terminal
- Vibe doesn't have a good mobile solution yet

## Architecture

We like Python

![](./slides/architecture.png)

<!-- end_slide -->

## Models
Why not all of them?

```python
# Devstral 2 — coding agent (via Vibe)
# Voxtral — realtime voice transcription (push-to-talk)
# Ministral — notification copy + urgency + tool call summaries
# Mistral Large — EN↔JA translation + (optional) screenshot/excerpt explanations
```

<!-- end_slide -->

OK, any of this, let's demo

<!-- Demo starts here — quit presenterm, you're in the terminal -->
```

**Run:**
```bash
presenterm slides.md
# Arrow keys / space to navigate
# q to quit → seamless transition to live demo
```

**Generate diagrams for slides:**
```bash
# Architecture diagram → PNG for inline display
# Use Mermaid CLI, D2, or just create in any image editor
mmdc -i architecture.mmd -o slides/architecture.png -t dark -b transparent

# ANSI art title banner (optional, for extra flair)
toilet -f future "vibecheck" > slides/title.txt

# High-res logo → terminal display (if needed outside presenterm)
chafa --format kitty --size 60x30 vibecheck-logo.png
```

### Slidev (PDF Backup / Handout)

```bash
npm init slidev@latest  # one-time setup
# Write slides in slides.md (Slidev markdown format)
# Export:
npx slidev export --output slides-backup.pdf
```

Keep the Slidev version as a PDF backup in case presenterm has issues with the projector, and as a handout for judges.

---

### scrcpy (Android Screen Mirroring)

**Install on Arch Linux:**
```bash
sudo pacman -S scrcpy
```

**Connect Pixel 9:**
```bash
# USB (lowest latency, recommended for demo)
scrcpy --window-title="vibecheck" --window-borderless

# WiFi (if USB isn't practical on stage)
adb tcpip 5555
adb connect <phone-ip>:5555
scrcpy --window-title="vibecheck" --window-borderless
```

**Recommended scrcpy flags for demo:**
```bash
scrcpy \
  --window-title="vibecheck - Pixel 9" \
  --window-borderless \
  --max-size=1080 \
  --max-fps=60 \
  --video-bit-rate=8M \
  --no-audio \
  --stay-awake \
  --turn-screen-off  # keep phone screen off while mirroring, save battery
```

**Niri window placement:**
After launching scrcpy, use Niri's tiling to place:
- Left 50%: Terminal (SSH to EC2, Vibe running)
- Right 50%: scrcpy window (phone screen)

### Phone Prep (Pixel 9)

- [ ] PWA installed (Add to Home Screen from Chrome)
- [ ] Push notifications enabled (Chrome → vibecheck → Allow)
- [ ] Microphone permission granted
- [ ] Do Not Disturb OFF (need notification sounds for demo)
- [ ] Screen timeout set to 10 minutes (Settings → Display)
- [ ] Brightness at max (for scrcpy visibility)
- [ ] USB debugging enabled (Settings → Developer Options)
- [ ] USB cable connected and scrcpy tested

### EC2 Prep

- [ ] Vibe running and responsive
- [ ] vibecheck bridge server running on :7870
- [ ] Caddy serving HTTPS (verify `https://your-domain` loads)
- [ ] WebSocket connectivity verified (phone connects, events flow)
- [ ] Test project loaded (something Vibe can code against)

---

## Screen Layout

### Phase 1: Presentation (100% terminal — presenterm)

```
┌────────────────────────────────────────────────────────────┐
│  Ghostty (fullscreen)                                      │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              presenterm slides.md                     │  │
│  │                                                       │  │
│  │     ╔═══════════════════════════════╗                 │  │
│  │     ║        vibecheck             ║                 │  │
│  │     ╚═══════════════════════════════╝                 │  │
│  │                                                       │  │
│  │     check your vibes from anywhere                    │  │
│  │                                                       │  │
│  │     [inline architecture diagram]                     │  │
│  │     (rendered via Kitty graphics)                     │  │
│  │                                                       │  │
│  │  ◀ ─────────────────────────────────────────────── ▶  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│   Intro → Problem → Architecture → Models → "let's demo"  │
│                                                            │
└────────────────────────────────────────────────────────────┘

  Press q → exits presenterm → you're in the terminal
  The transition to live demo is seamless
```

### Phase 2: Live Demo (50/50 split — Niri tiling)

```
┌────────────────────────────┬───────────────────────────────┐
│                            │                               │
│  TERMINAL (50%)            │  SCRCPY / PHONE (50%)         │
│  SSH into EC2              │  Pixel 9 via scrcpy           │
│  Vibe agent running        │  vibecheck PWA                │
│                            │                               │
│  $ vibe                    │  ┌─────────────────────────┐  │
│  > I'll create a REST...   │  │ 🟢 Vibe Mobile    🔔 ⚙️│  │
│  > 🔧 bash: npm test       │  │                         │  │
│  > ⏳ Waiting for approval  │  │ Chat messages...        │  │
│                            │  │                         │  │
│                            │  │ ⚠️ APPROVE bash?        │  │
│                            │  │ [✅ Approve] [❌ Deny]  │  │
│                            │  │                         │  │
│                            │  │ [🎤] Type or speak [→]  │  │
│                            │  └─────────────────────────┘  │
│                            │                               │
└────────────────────────────┴───────────────────────────────┘

  Transition: resize Ghostty to 50%, open scrcpy alongside
  Or: Niri keybind to switch from fullscreen → tiled layout
```

---

## Pre-Demo Checklist

Run through this 10 minutes before presenting:

```bash
# 0. Test presenterm with projector
presenterm slides.md
# Verify: inline images render (Kitty protocol), text is readable at room distance
# Press q to exit

# 1. Verify EC2 is live
curl -s -H "X-PSK: $VIBECHECK_PSK" https://your-domain/api/state | jq .

# 2. Verify Vibe is running on EC2
ssh ec2 "pgrep -f 'vibe'"

# 3. Launch scrcpy
scrcpy --window-title="vibecheck - Pixel 9" --window-borderless \
  --max-size=1080 --max-fps=60 --video-bit-rate=8M --no-audio --stay-awake

# 4. Open terminal, SSH into EC2
ssh ec2

# 5. On phone: open vibecheck PWA
# Verify: green 🟢 connected indicator
# Verify: can see any existing Vibe session events

# 6. Test quick approval cycle
# On EC2: trigger a tool call in Vibe
# On phone: approve from PWA → verify Vibe continues

# 7. Test voice
# On phone: hold mic → speak → verify transcription appears

# 8. Test push notification
# On phone: close PWA → trigger approval in Vibe
# Verify: phone buzzes with notification
```

---

## Demo Script

### Beat 1: The Problem (presenterm)

*"You're running an AI coding agent — Mistral Vibe — on your dev machine. It's writing code, running tests, building features. But every few minutes it stops and asks: 'Can I run this command?' 'Should I create this file?' You're stuck at your desk."*

*"What if you could check on your agent from your phone?"*

### Beat 2: Architecture (presenterm, 1 min)

Architecture diagram displayed inline via Kitty graphics protocol:
```
Phone → HTTPS → EC2 (Caddy + vibecheck bridge + Vibe)
```

*"We hook directly into Vibe's Python event system — no terminal scraping. Typed events, clean callbacks."*

Model usage slide: Devstral 2 (coding), Voxtral (voice), Ministral (notifications), Mistral Large (translation + optional image/excerpt explainers).

### Beat 3: Live Demo — Core Loop

**Quit presenterm (q) → you're in the terminal. Open scrcpy alongside. Switch to 50/50 Niri layout.**

1. **Show Vibe running** on the left (terminal). Give it a task: *"Create a REST API endpoint for user authentication"*
2. **Show phone** on the right (scrcpy). Events streaming in real time — assistant messages, tool calls.
3. Vibe asks for approval → **phone shows approval panel** → tap Approve on the phone → Vibe continues on terminal.

*"That's the core loop. Your agent works, you approve from your pocket."*

### Beat 4: Voice Input

1. Tap the mic button on phone → **speak in Japanese**: "テストを実行して" (run the tests)
2. Voxtral transcribes → Japanese text appears in input → send
3. Vibe receives the message and acts

*"Voxtral transcribes Japanese at $0.003/minute. Push-to-talk, release, confirm, send."*

### Beat 5: Push Notifications

1. **Close the PWA** on the phone (swipe away)
2. On terminal: Vibe hits a point where it needs approval
3. **Phone buzzes** — push notification appears: "🔧 Vibe Check: bash wants to run npm test"
4. Tap Approve directly from the notification (Android action button)
5. Vibe continues

*"You don't even need the app open. Approve from your lock screen."*

### Beat 6: Translation

1. Open the PWA again
2. Vibe has produced English output
3. Tap `🌐 自動翻訳` on a message → **Japanese translation appears instantly**
4. Show global toggle in settings → all messages auto-translate

*"For the Tokyo audience — everything in Japanese with one toggle. Powered by Mistral Large."*

### (Optional) Beat 6b: Images / Excerpts → Explain

1. On phone (or terminal): paste an error excerpt/log snippet, or a screenshot (OCR → text)
2. Tap "Explain (JP)" → Mistral Large returns a short Japanese explanation and suggested next action

*"This is great for debugging from your pocket — even when the original output is a messy wall of English."*

### Beat 7: Intensity (if time)

Show the intensity slider: *"How hard are you going?"*
- Slide to 🔥 Locked In — show escalating idle notifications
- Slide to 💀 Ralph — *"Named after Ralph Wiggum. Your agent won't stop and neither will your notifications."*

### Beat 8: QR Code (the closer)

Put a QR code on screen → the EC2 URL.

*"Want to try it? Open your phone camera."*

Audience opens the PWA on their own phones. They can see the live agent session in read-only mode.

*"That's vibecheck. AI coding from your pocket."*

---

## Fallback Plan

| Failure | Mitigation |
|---------|------------|
| presenterm broken on projector | Switch to Slidev PDF backup (pre-exported) |
| EC2 down | Have a pre-recorded video of the full demo flow |
| scrcpy fails | Use Chrome DevTools mobile viewport on the projector instead |
| Phone won't connect | Demo from laptop browser in mobile mode |
| Voxtral API down | Type the message manually, explain voice would have worked |
| Push notifications don't fire | Show the notification in the PWA directly, explain push pipeline |
| WiFi unreliable at venue | USB tether phone to laptop, connect EC2 over phone's data |
| Vibe crashes mid-demo | Have a second session pre-loaded, `vibe --resume` |

### Pre-Record Backup

Before the hackathon presentation, record a complete screen capture of the full demo flow (all beats) as a fallback video. Use OBS or similar.

```bash
# Quick OBS recording setup (Wayland/Niri)
# Record the full 50/50 layout for 3-5 minutes
# Save as demo-backup.mp4
```

---

*See also: [PLAN.md](./PLAN.md) (implementation plan), [README.md](./README.md) (product brief)*
