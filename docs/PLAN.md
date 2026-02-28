# vibecheck — Hackathon Execution Plan

> **Last updated:** 2026-02-28
> **Team size:** 2 people, ~24 hours
> **Architecture:** In-process FastAPI bridge into Vibe's Textual/Python event system (multi-session)
> **Deployment:** EC2 instance (Vibe + bridge + Caddy), phone connects over HTTPS
> **Excluded:** Voxtral fine-tuning (no public training code for Realtime architecture)

---

## Table of Contents

- [Architecture Decision](#architecture-decision)
- [Deliverables](#deliverables)
- [Feature Layers](#feature-layers)
- [Parallel Tracks](#parallel-tracks)
- [Integration Points](#integration-points)
- [Dependency Graph](#dependency-graph)
- [Tech Stack](#tech-stack)
- [Open Questions Resolved](#open-questions-resolved)

---

## Architecture Decision

Vibe uses **Textual** (Python TUI framework) with typed async events (`BaseEvent` hierarchy) and `asyncio.Future` callbacks. Unlike Claude Code's raw terminal I/O, Vibe exposes clean programmatic hooks:

- `AgentLoop.set_approval_callback()` — intercept tool approval requests
- `AgentLoop.set_user_input_callback()` — intercept `ask_user_question` tool
- `message_observer` — capture all events for broadcasting
- `BaseEvent` hierarchy — typed events (AssistantEvent, ToolCallEvent, etc.)

**We hook directly into Vibe's event system** — no terminal emulation, no tmux, no PTY bridging. This gives us typed, structured data on the mobile client instead of terminal scraping.

**The user runs `vibecheck-vibe` instead of `vibe`.** Same Textual TUI, same AgentLoop, but with vibecheck's WebSocket bridge running alongside. Terminal and phone are parallel surfaces into the same session:
```
Terminal (Textual TUI) ──┐
                         ├── vibecheck-vibe ── AgentLoop ── Mistral API
Phone (PWA) ─────────────┘
         ↕ HTTPS/WSS
EC2 (Caddy → :7870)
```
No SSH tunnels, no Cloudflare, no Tailscale. Caddy handles TLS termination (Let's Encrypt) and WebSocket upgrade.

---

## Deliverables

| Artifact | Description |
|----------|-------------|
| `vibecheck/` | Python package — FastAPI bridge server + Vibe integration |
| `vibecheck/frontend/` | Svelte + Vite PWA mobile client |
| `vibecheck/frontend/public/sw.js` | Service worker (push notifications + offline) |
| `DEMO.md` | Presentation script, setup checklist, demo beats, fallback plan |
| EC2 deployment | Running instance with Caddy + HTTPS + Vibe + vibecheck |

---

## Feature Layers

Each layer builds on the previous. Every layer is an independently demoable state — if time runs out at any layer, you have a working product to show.

### Layer 0 — Foundation

> *Demo: "Vibe is running on EC2, accessible over HTTPS"*

- [ ] EC2 instance provisioned (Python 3.12+, uv, ffmpeg)
- [ ] Vibe installed and running on EC2
- [ ] Caddy configured with Let's Encrypt (HTTPS + WSS proxy to :7870)
- [ ] `vibecheck/` package scaffolded (FastAPI app skeleton)
- [ ] PSK auth mechanism implemented
- [ ] Verify HTTPS reachable from phone browser

### Layer 1 — Core Bridge (Multi-Session from Day One)

> *Demo: "Connect to bridge, see Vibe events flowing, approve tool calls via curl"*

The bridge is designed multi-session from the start. All state is keyed by `session_id`, so one vibecheck server manages N concurrent Vibe instances.

- [ ] `SessionBridge` — per-session bridge wrapping one `AgentLoop` instance
  - `approval_callback` — intercept tool approvals, resolve via REST/WS
  - `user_input_callback` — intercept questions, resolve via REST/WS
  - Per-session pending state (`_pending_approval`, `_pending_input`, `_waiting_state`)
- [ ] `SessionManager` — discover and manage multiple sessions
  - Scan `~/.vibe/logs/session/` for existing Vibe sessions
  - `attach(session_id)` — create `SessionBridge` for a discovered session (`observe_only` or `replay` mode — **not** live control; live attach requires the session to be started via `vibecheck-vibe`)
  - `detach(session_id)` — stop receiving events, clean up
  - `list()` — return all known sessions with status (running/waiting/idle)
- [ ] WebSocket `/ws/events/{session_id}` — stream `BaseEvent` types for one session
  - Clients subscribe to a specific session (room-based routing)
  - Connection tracked per-session: `Dict[str, Set[WebSocket]]`
- [ ] REST API (session-aware):
  - `GET /api/sessions` — list discovered sessions with status summary
  - `GET /api/sessions/{session_id}` — session detail + event backlog
  - `POST /api/sessions/{session_id}/approve` — approve/deny tool calls
  - `POST /api/sessions/{session_id}/input` — respond to agent questions
  - `POST /api/sessions/{session_id}/message` — send new user messages to Vibe
  - `GET /api/state` — fleet summary (N running, N waiting, N idle)
- [ ] Event broadcasting scoped to session subscribers

> **Fallback:** If in-process `AgentLoop` hooks don't work as expected, fall back to tmux/PTY sidecar (terminal scraping). See `docs/ANALYSIS-session-attachment.md` for full option analysis.

### Layer 1.5 — Live Attach (Vibe TUI + Mobile Bridge)

> *Demo: "Run vibecheck-vibe in terminal, open phone, see same events, approve from either surface"*

The core product promise: run Vibe in your terminal, walk away, control it from your phone. This requires the terminal TUI and mobile PWA to share the **same** AgentLoop in the **same** process. See `docs/ANALYSIS-session-attachment.md` for why this can't be done cross-process (Vibe has no IPC).

**Architecture:**
```
Terminal (Textual TUI) ──┐
                         ├── vibecheck-vibe process ── AgentLoop ── Mistral API
Phone (PWA via WSS) ─────┘
```

- [ ] `vibecheck-vibe` CLI wrapper replaces `vibe` command
  - Creates AgentLoop using Vibe's libraries (same as `vibe` CLI)
  - Creates SessionBridge with `attach_to_loop()` — wires callbacks on the existing loop
  - Starts vibecheck FastAPI/WebSocket server on :7870 (uvicorn as Textual worker, same asyncio loop)
  - Launches Vibe's Textual TUI (`VibeCheckApp` subclass of `VibeApp`)
- [ ] Bridge owns AgentLoop — single consumer of `act()` generator
  - Event tee: fan out events to both TUI renderer and WebSocket broadcast
  - Dual input: terminal keyboard and phone REST both go through `bridge.inject_message()`
  - Serialized through bridge's `_message_queue` / `_message_worker`
- [ ] Session API exposes `attach_mode` and `controllable` fields:
  - `attach_mode: "live"` + `controllable: true` — started via `vibecheck-vibe`, full control
  - `attach_mode: "managed"` + `controllable: true` — bridge-created loop, full control
  - `attach_mode: "observe_only"` + `controllable: false` — discovered unmanaged session, read-only
  - `attach_mode: "replay"` + `controllable: true` — new loop from history, independent of terminal
- [ ] Approval callback routes to both surfaces; either can resolve
  - Mobile approves via REST → bridge resolves Future → TUI updates
  - TUI approves via keyboard → bridge resolves Future → mobile updates via WebSocket
  - Both surfaces show pending state; first to respond wins

> **Fallback:** If VibeApp subclassing proves unworkable, fall back to tmux/PTY sidecar (Option C in `docs/ANALYSIS-session-attachment.md`). Brittle but demoable.

#### Phase 3 status: bridge mechanics complete, TUI integration gaps identified

Phase 3 (WU-25–28) proved the bridge mechanics: callback ownership, event tee, dual-surface resolution (60 tests). **Phase 3.1** (WU-32–34) addresses three TUI integration gaps that only manifest with the real Vibe Textual app:

1. **TUI stuck in approval UI after mobile resolves (High):** Settle resolves the asyncio Future but doesn't trigger Vibe's Textual UI cleanup (`on_approval_app_*` handlers). Must fix before demo.
2. **Mobile-injected prompts invisible in terminal (Medium):** Vibe's EventHandler ignores `UserMessageEvent` by design. Accept and document for hackathon.
3. **`_handle_agent_loop_turn` bypass drops loading widget + interrupt (Medium):** Document; loading widget is nice-to-have.

See `docs/ANALYSIS-session-attachment.md` § "Phase 3 Validation: Confirmed Gaps" for full technical detail.

### Layer 2 — Mobile PWA Chat

> *Demo: "Open phone browser, see Vibe working live, approve tool calls from phone"*

- [ ] **Session switcher** — top-of-screen dropdown or swipeable tabs
  - Fetches session list from `GET /api/sessions`
  - Shows session name/project + status badge (running/waiting/idle)
  - Switching sessions reconnects WebSocket to `/ws/events/{new_session_id}`
  - Fleet status bar: "3 vibes: 2 running, 1 waiting"
- [ ] HTML/CSS/JS chat UI with structured event rendering:
  - AssistantEvent → chat bubble
  - ToolCallEvent → collapsible tool card (name + args)
  - ToolResultEvent → result/error under tool card
  - ReasoningEvent → collapsible dimmed block
  - CompactStartEvent/CompactEndEvent → compaction notice
- [ ] Sticky approve/deny panel (visible when Vibe is waiting)
  - Approve / Deny / Edit & Approve buttons
  - Tool name + args display
- [ ] Input bar (text input + send button)
- [ ] Connection status indicator (connected/disconnected/reconnecting)
- [ ] WebSocket auto-reconnect with exponential backoff
- [ ] PWA manifest (standalone, portrait, Mistral orange theme)
- [ ] Service worker shell (offline fallback page)
- [ ] Mobile-optimized CSS (touch targets, safe areas, viewport)

### Layer 3 — Voice Input

> *Demo: "Hold mic button, speak Japanese, see transcription, send to Vibe"*

- [ ] `POST /api/voice/transcribe` — server-side Voxtral batch API proxy
  - Accept `audio/webm;codecs=opus` from MediaRecorder
  - `language` param (default `ja`, option `en`)
  - Context biasing for domain terms (vibecheck, Voxtral, Mistral, etc.)
- [ ] Push-to-talk mic button (tap-and-hold)
  - MediaRecorder with `audio/webm;codecs=opus`
  - echoCancellation + noiseSuppression enabled
  - Visual recording indicator (pulsing mic)
- [ ] Transcription preview in input field (edit before sending)
- [ ] Voice language selector in settings (JA / EN)

### Layer 4a — Push Notifications (Core)

> *Demo: "Put phone away, Vibe asks for approval, phone buzzes, approve from lock screen"*

- [ ] VAPID key generation (one-time setup)
- [ ] `POST /api/push/subscribe` — register client push subscriptions
- [ ] pywebpush integration — send notifications on:
  - `approval` — tool call needs approval (high priority, requireInteraction)
  - `user_input` — agent has a question (high priority, requireInteraction)
  - `error` — agent crashed (normal priority)
- [ ] Service worker push handler with notification rendering
- [ ] Notification action buttons: Approve / Deny (Android; iOS opens app)

### Layer 4b — Smart Notifications (Ministral + Intensity)

> *Demo: "Notification says 'npm test wants to check your code' instead of raw JSON. Slide intensity to Ralph mode."*

- [ ] Ministral integration:
  - Notification copy generation (short, calm, slightly playful, max 80 chars)
  - Urgency classification (maps to push priority)
  - 1-line tool call summaries (for approval banner + push text)
- [ ] Extended notification events:
  - `task_complete` — task finished (low priority, Level 3+)
  - `idle` — agent idle (low priority, Level 3+)
  - `progress` — progress update (low priority, Level 4+)
- [ ] **Intensity system** (5 levels):
  - 😴 Chill — errors only
  - 🎵 Vibing — approval + questions (default)
  - 🎯 Dialed In — + completion + idle nudges
  - 🔥 Locked In — + progress + escalating idle alerts
  - 💀 Ralph — everything, repeated, relentless
- [ ] Escalating idle alerts (5min → 10min → 15min → 30min messages)
- [ ] Snooze controls: 30min / 1hr / Until Morning
- [ ] Snooze never suppresses approval/question/error (agent-blocking events)

### Layer 5 — Japanese Auto-Translation

> *Demo: "Toggle translation on English output, see Japanese instantly"*

- [ ] `POST /api/translate` — translate via `mistral-large-latest` (Mistral Large 3)
  - Preserve code blocks, file paths, technical terms untranslated
  - Preserve markdown formatting
  - temperature=0.1 for consistency
- [ ] Per-message `🌐 自動翻訳` toggle (click to swap EN↔JA)
- [ ] Global "Auto-translate EN→JA" setting toggle
- [ ] Client-side translation cache (by message ID, avoids re-translating)
- [ ] CJK-ratio language detection (skip translating already-JA content)
- [ ] Server-side auto-translate option (broadcast translated events alongside originals)

### Layer 6 — Polish & UX

> *Demo: "Full polished mobile experience — themes, diffs, session details"*

- [ ] Session detail view (event backlog, file changes, token usage)
- [ ] Session resume/continue from mobile (reattach bridge to a past session)
- [ ] Tool call diff viewer (for write_file/search_replace — show before/after)
- [ ] Settings panel:
  - Intensity slider
  - Translation toggle + voice language
  - Notification on/off
  - Snooze controls
  - Theme toggle
- [ ] Dark/light theme
- [ ] Offline event cache (show last known state when reconnecting)

### Layer 7 — Stretch: Advanced Voice + ElevenLabs TTS

> *Demo: "Talk to your agent, hear it respond — full voice loop from your phone"*

- [ ] **ElevenLabs TTS for agent responses** (Best Voice Use Case prize target)
  - Stream agent `AssistantEvent` text → ElevenLabs TTS API → audio playback on phone
  - Use streaming endpoint for low-latency: text chunks → audio chunks → `<audio>` or Web Audio API
  - Voice selection: pick a voice that fits the "agent assistant" vibe (e.g. `Rachel`, `Antoni`)
  - Japanese support: ElevenLabs supports 32 languages including JA — TTS works for translated text too
  - Auto-read toggle: optionally read all agent responses aloud (off by default, toggle in settings)
  - `POST /api/tts` — server-side proxy to ElevenLabs API (keeps API key server-side)
- [ ] **Full voice loop UX**: Voxtral STT (input) + ElevenLabs TTS (output) = conversational agent
  - Walkie-talkie mode: hold to speak → release → agent processes → hear response
  - Haptic feedback on state transitions (recording → processing → speaking)
- [ ] Voxtral Realtime streaming transcription
  - AudioWorklet PCM pipeline (16kHz mono)
  - Phone → WebSocket `/ws/voice` → server → Voxtral Realtime WS
  - Partial text deltas streamed back to phone
  - Live subtitles while speaking
- [ ] Browser `SpeechSynthesis` API as zero-cost fallback (no API key needed, lower quality)

### Layer 8 — Stretch: Spawn/Orchestrate & Rich Media

> *Demo: "Spin up a new Vibe from your phone, snap a whiteboard photo, send to agent"*

Multi-session *discovery and switching* is built into L1/L2. This layer adds active orchestration — spawning and tearing down sessions from mobile.

- [ ] `POST /api/sessions` — spawn a new Vibe instance from mobile (project path + initial prompt)
- [ ] `DELETE /api/sessions/{session_id}` — gracefully stop a Vibe session
- [ ] Cross-agent context sharing (copy output from Agent A → input to Agent B)
- [ ] Camera input: snap photo → Mistral Large 3 (multimodal) analyzes → context for Vibe
- [ ] Screenshot relay: periodic dev machine captures → Large 3 summarizes → phone
- [ ] File browser: browse & preview project files from mobile

### Layer 9 — Stretch: Smart Autonomy & Showmanship

> *Demo: "Audience opens QR code, watches the agent code live on their phones"*

- [ ] Autonomy slider: "ask me about everything" ↔ "YOLO mode" (auto-approve safe tools)
- [ ] Per-tool trust levels: auto-approve `read_file`, always ask for `bash`, etc.
- [ ] Time-boxed autonomy: "run free for 10 minutes, then check in"
- [ ] Cost/token tracker: live dashboard of API spend per session
- [ ] Risk scoring: color-code tool calls by danger level (green/yellow/red)
- [ ] Live demo mode: public read-only URL for judges/audience
- [ ] QR code on slide → instant audience participation
- [ ] Replay mode: speed-run playback of a full agent session
- [ ] Confetti animation on task completion 🎉

---

## Parallel Tracks

Two tracks organized by **what can be built independently**, not by person. Either team member can pick up work from either track. Tracks converge at integration points.

### Track A — Backend / Bridge (Python)

Owns: Vibe integration, FastAPI server, WebSocket event system, all `/api/*` endpoints, Mistral API integrations (Voxtral, Ministral, translation), EC2 infra.

```
L0:    Scaffold vibecheck/ package, FastAPI app, PSK auth
       EC2 provisioning, Caddy + Let's Encrypt, Vibe on EC2
L1:    SessionManager + SessionBridge, session discovery (~/.vibe/logs/session/),
       WS /ws/events/{session_id}, session-scoped REST endpoints, fleet state
L1.5:  attach_to_loop(), event tee, VibeCheckApp subclass, vibecheck-vibe launcher
L2:    Session-scoped event broadcasting, session switcher data
L3:  POST /api/voice/transcribe (Voxtral batch proxy)
L4a: VAPID + pywebpush, push on approval/input/error (includes session_id)
L4b: Ministral copy/urgency/summaries, IntensityManager, snooze
L5:  POST /api/translate (mistral-large-latest), auto-translate broadcast
L6:  Session detail/resume APIs, diff data endpoints
L7:  ElevenLabs TTS proxy, Voxtral Realtime streaming, autonomy controls backend
L8:  Spawn/kill sessions from mobile, cross-agent context
L9:  Read-only public endpoints, token tracker
```

### Track B — Frontend / PWA (Svelte + Vite)

Owns: Mobile UI, Svelte components, chat rendering, approve/deny panels, voice recording, translation toggle, service worker, push notification handling, all client-side UX.

```
L0:  Svelte + Vite scaffold, PWA manifest, base layout + CSS
L1:  Static chat mockup with mock events, approve/deny panel design
L2:  Session switcher (dropdown/tabs), real WS rendering per session,
     fleet status bar, connection status, auto-reconnect
L3:  MediaRecorder mic button, push-to-talk UX, transcription preview
L4a: Service worker push handler, notification action buttons (with session_id)
L4b: Intensity slider UI, snooze controls
L5:  Per-message translation toggle, global toggle, client-side cache
L6:  Settings panel, dark/light theme, diff viewer, session detail view
L7:  Walkie-talkie UX (voice loop), live subtitle rendering, ElevenLabs TTS playback
L8:  Spawn session UI, camera input UI, file browser
L9:  Autonomy slider, risk badges, confetti, replay player
```

### Parallelism Map

Shows what can be worked on simultaneously at each layer:

```
Layer   Track A (Backend)                    Track B (Frontend)              Parallel?
─────   ─────────────────                    ──────────────────              ─────────
L0      FastAPI + EC2 + Caddy                Svelte scaffold + PWA shell    ✅ fully
L1      WS + callbacks + REST                Static mockup + panel design   ✅ fully
L1.5    attach_to_loop + launcher            (backend-only)                 ⚠️ backend
                ╔═══════════════════════════════════════════╗
                ║  INTEGRATION #1 — connect A↔B, test E2E  ║
                ╚═══════════════════════════════════════════╝
L2      Event broadcast + state              Live WS rendering + reconnect  ✅ fully
L3      Voxtral proxy endpoint               Mic button + recording UX      ✅ fully
L4a     VAPID + pywebpush                    SW push handler + actions      ✅ fully
L4b     Ministral + Intensity backend        Intensity UI + snooze          ✅ fully
L5      Translate endpoint                   Toggle UI + cache              ✅ fully
L6      Session/diff APIs                    Settings + theme + diff view   ✅ fully
L7+     Stretch backend                      Stretch frontend               ✅ fully
```

> **Note:** L1.5 is a backend-only layer (no frontend changes). After L1.5 + L2, layers L3/L4a/L4b/L5/L6 are independent branches — the team can tackle them in any order or split across them freely.

---

## Integration Points

These are moments where parallel tracks must sync and test together.

### Integration #1: First Live Mobile Demo (after L1.5 + L2)

**What:** Track A's WebSocket + events + callbacks connected to Track B's chat UI on Track C's EC2 instance.

**Test:** Open phone browser → see Vibe events streaming → approve a tool call from phone → Vibe continues.

**Blocker if fails:** Everything after this depends on the bridge working. Debug together if needed.

### Integration #2: Voice Pipeline End-to-End (after L3)

**What:** Track B's mic recording → Track A's Voxtral proxy → transcription → injected into Vibe.

**Test:** Hold mic on phone → speak Japanese → see transcription in input → send → Vibe receives Japanese text.

### Integration #3: Push Notification Full Loop (after L4a)

**What:** Vibe waits for approval → Track A sends push → Track B's service worker shows notification → user approves → Track A resolves callback → Vibe continues.

**Test:** Close phone browser → Vibe runs a tool → phone buzzes → approve from notification → Vibe continues.

### Integration #4: Translation Pipeline (after L5)

**What:** Track A's translate endpoint → Track B's toggle UI → cached translations.

**Test:** English assistant message → tap 🌐 → see Japanese translation → tap back → see English.

---

## Dependency Graph

```
L0 Foundation ─────────────────────────────────────────────────────────
  │
  ├── L1 Core Bridge ──────────────────────────────────────────────────
  │     │
  │     ├── L1.5 Live Attach (TUI + Mobile Bridge) ────────────────────
  │     │     │
  │     │     ├── L2 Mobile PWA Chat ──────────────────────────────────
  │     │     │
  │     │     ├── L3 Voice Input ──────────────────────────────────────
  │     │     │     │
  │     │     │     └── L7 Advanced Voice (stretch) ───────────────────
  │     │     │
  │     │     ├── L4a Push Notifications (core) ───────────────────────
  │     │     │     │
  │     │     │     └── L4b Smart Notifications (Ministral + Intensity)
  │     │     │
  │     │     ├── L5 Japanese Auto-Translation ────────────────────────
  │     │     │
  │     │     └── L6 Polish & UX ──────────────────────────────────────
  │     │           │
  │     │           ├── L8 Spawn/Orchestrate & Rich Media (stretch) ───
  │     │           │
  │     │           └── L9 Smart Autonomy & Showmanship (stretch) ─────
```

Note: L1.5 is a prerequisite for all higher layers (it provides the live attach capability). L3, L4a, L5, L6 are **independent of each other** — they all branch from L1.5/L2. L4b depends on L4a. After L1.5 + L2 are working, the team can split across these features in any order.

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|------------|
| Bridge server | FastAPI + Starlette (async) |
| WebSocket | Starlette WebSocket |
| Vibe integration | In-process `AgentLoop` hooks |
| Voice transcription | Mistral SDK (`voxtral-mini-latest` batch API) |
| Translation | Mistral SDK (`mistral-large-latest` chat) |
| Notification copy | Mistral SDK (`ministral-8b-latest` chat) |
| Push notifications | pywebpush (VAPID) |
| Auth | PSK (pre-shared key, timing-safe comparison) |

### Frontend
| Component | Technology |
|-----------|------------|
| UI framework | Svelte 5 + Vite |
| PWA | Service Worker + Web App Manifest |
| Voice recording | MediaRecorder API (`audio/webm;codecs=opus`) |
| Push | Push API + Notification API |
| State management | Svelte stores (writable/readable) |
| Build | Vite (dev server + production build) |

### Infrastructure
| Component | Technology |
|-----------|------------|
| Server | EC2 instance |
| Reverse proxy | Caddy |
| TLS | Let's Encrypt (certbot) |
| Python | 3.12+ via uv |
| Process manager | systemd (Vibe + bridge) |

### Mistral Models Used
| Model | Purpose | Pricing |
|-------|---------|---------|
| **Devstral 2** | Core Vibe coding agent | $0.40/M in, $2.00/M out |
| **Voxtral Mini** (batch) | Push-to-talk transcription | $0.003/min |
| **Voxtral Mini** (realtime) | Live streaming transcription (stretch) | $0.006/min |
| **Ministral 8B** | Notification copy, urgency, tool summaries | see docs |
| **Mistral Large 3** | EN↔JA translation + camera/multimodal input (vision) | see docs |

---

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| Terminal emulation vs event bridging? | **Event bridging.** Vibe is Textual/Python — hook into `AgentLoop` directly. |
| Tunnel approach? | **None needed.** Vibe runs on EC2, Caddy handles HTTPS. |
| PWA vs native app for notifications? | **PWA.** Web Push works on Android (full) and iOS 16.4+ (requires Add to Home Screen). |
| Voxtral API vs self-hosted? | **API** for hackathon ($0.003-0.006/min is cheap). Self-hosted is stretch if GPU available. |
| In-process vs sidecar? | **In-process sidecar injection** (Option B). `vibecheck-vibe` wraps Vibe's CLI — same process runs TUI + WebSocket bridge. Typed events, shared AgentLoop, no terminal scraping. See `docs/ANALYSIS-session-attachment.md`. |
| JA-native prompting vs translation overlay? | **Both.** Support JA input natively AND provide translation as fallback for EN-only content. |
| Voxtral fine-tuning? | **Excluded.** No public training code for Realtime architecture. |
| Demo approach? | **Split-screen** (Vibe terminal + phone mirror via scrcpy) + QR audience participation. See DEMO.md. |
| Frontend framework? | **Svelte 5 + Vite.** Less code than Vue/React, compiles away the framework, smallest bundles. Good enough AI tooling support. Component model maps well to event types. |
| Single-session or multi-session? | **Multi-session from day one.** Bridge is keyed by `session_id` from L1. Discover existing sessions for `observe_only`/`replay` (L1). Live control requires sessions started via `vibecheck-vibe` (L1.5). Spawn/orchestrate is stretch (L8). |

---

*See also: [README.md](../README.md) (product brief)*
