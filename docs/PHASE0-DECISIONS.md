# Phase 0 Decisions — API Contract & Policy Freeze

> **Date:** 2026-02-28
> **Status:** DRAFT — needs team sign-off before WU-01/WU-02 restart
> **Context:** Coder review identified 8 areas that need nailing down before implementation restarts. This document resolves each one.

---

## 1. API Contract Freeze

### Routes (canonical, final)

**Auth-exempt:**
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Health check |
| `GET` | `/` | Static files / SPA shell |
| `GET` | `/static/*` | Built frontend assets |

**PSK-protected REST (require `X-PSK` header or `?psk=` query):**
| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `GET` | `/api/state` | Fleet summary (N running, N waiting, N idle) | L1 |
| `GET` | `/api/sessions` | List all discovered sessions | L1 |
| `GET` | `/api/sessions/{session_id}` | Session detail + event backlog | L1 |
| `POST` | `/api/sessions/{session_id}/approve` | Approve/deny tool call | L1 |
| `POST` | `/api/sessions/{session_id}/input` | Respond to agent question | L1 |
| `POST` | `/api/sessions/{session_id}/message` | Send new user message to Vibe | L1 |
| `POST` | `/api/voice/transcribe` | Voxtral batch transcription proxy | L3 |
| `POST` | `/api/push/subscribe` | Register push subscription | L4a |
| `POST` | `/api/translate` | Mistral Large translation proxy | L5 |
| `POST` | `/api/tts` | ElevenLabs TTS proxy | L7 |
| `POST` | `/api/sessions` | Spawn new Vibe session | L8 |
| `DELETE` | `/api/sessions/{session_id}` | Stop a Vibe session | L8 |

**WebSocket (PSK via `?psk=` query param on connect):**
| Path | Purpose | Phase |
|------|---------|-------|
| `WS /ws/events/{session_id}` | Stream events for one session | L1 |

### Naming resolution

PLAN.md says `/ws/events/{session_id}`. WU-01 spec says `/ws/events`. **Decision: use `/ws/events/{session_id}`** — it's the right design for multi-session from day one. WU-01 stubs this route; the scaffold test can use a fixed session_id like `"test"`.

Update WU-01 spec accordingly.

### Request/response shapes (stubs, Phase 0)

```
GET /api/health
→ 200 {"status": "ok"}

GET /api/state
→ 200 {"total": 0, "running": 0, "waiting": 0, "idle": 0}

GET /api/sessions
→ 200 []

GET /api/sessions/{session_id}
→ 501 {"detail": "not implemented"}

POST /api/sessions/{session_id}/approve
Body: {"tool_call_id": str, "approved": bool, "edited_args"?: dict}
→ 501 {"detail": "not implemented"}

POST /api/sessions/{session_id}/input
Body: {"text": str}
→ 501 {"detail": "not implemented"}

POST /api/sessions/{session_id}/message
Body: {"text": str}
→ 501 {"detail": "not implemented"}

WS /ws/events/{session_id}?psk=<key>
→ Server sends: {"type": "connected", "session_id": "<id>"}
→ Server sends: {"type": "heartbeat", "ts": "<ISO8601>"} every 30s
→ Server sends: event objects (see §4 Event Schema)
```

---

## 2. Auth Policy (Dev vs Prod)

**Decision: `VIBECHECK_PSK` is always required. No magic defaults.**

| Scenario | Behavior |
|----------|----------|
| `VIBECHECK_PSK` is set | Use that value for auth |
| `VIBECHECK_PSK` is unset | Server refuses to start with clear error message |

**Rationale:** The WU-01 spec suggested `default "dev" in dev` — this is how the auth bypass happened. A missing env var is a config error, not something to silently default.

**Dev workflow:** Set `export VIBECHECK_PSK=dev` in your shell profile. It's one line. No auto-defaults that can accidentally ship.

**Auth-exempt paths:** Exact match for `/api/health`, prefix match for `/static/`. Everything else requires PSK.

**WebSocket auth:** PSK passed as `?psk=<key>` query parameter on the WS upgrade request. Validated before upgrade completes. No first-message auth.

---

## 3. Session Source-of-Truth

### Where sessions live

Vibe stores session logs in `~/.vibe/logs/session/` (NOT `~/.vibe/sessions/` — the PLAN.md reference was wrong).

```
~/.vibe/logs/session/
├── session_20260228_120000_abc12345/
│   ├── meta.json        # Session metadata (id, times, stats, config)
│   └── messages.jsonl   # LLMMessage objects, one per line
├── session_20260228_130000_def67890/
│   ├── meta.json
│   └── messages.jsonl
...
```

### Session discovery

`SessionManager.list()` scans `~/.vibe/logs/session/`, reads `meta.json` from each subdirectory. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` (UUID) | Unique identifier |
| `title` | `str` | First 50 chars of first user message |
| `start_time` | `str` (ISO8601) | When session started |
| `end_time` | `str \| None` | When session ended (null if active) |
| `environment.working_directory` | `str` | Project path |
| `stats` | `dict` | Token usage, tool call counts |

### Session status (derived, not stored)

Status is **computed**, not a field in `meta.json`:

| Status | Condition |
|--------|-----------|
| `running` | Attached bridge, AgentLoop actively generating |
| `waiting_approval` | Attached bridge, `_pending_approval` Future is pending |
| `waiting_input` | Attached bridge, `_pending_input` Future is pending |
| `idle` | Attached bridge, no pending operations |
| `disconnected` | Session exists on disk but no bridge attached |

### Attach / Detach semantics

- **Attach** (`SessionManager.attach(session_id)`) — Create a `SessionBridge` wrapping a live `AgentLoop` for this session. Set callbacks. Start receiving events. Multiple WS clients can watch the same attached session.
- **Detach** (`SessionManager.detach(session_id)`) — Remove callbacks, disconnect all WS clients for this session, garbage-collect the bridge. Session remains on disk.
- **One bridge per session.** No duplicate attachments.

### PLAN.md correction

Update PLAN.md references from `~/.vibe/sessions/` to `~/.vibe/logs/session/`.

---

## 4. Event Schema Freeze

### Wire format (WebSocket JSON)

Every event sent over the WS is a JSON object with a `type` discriminator field. All fields below are the canonical wire schema — frontend and backend must agree on these.

#### Vibe-sourced events (mirroring BaseEvent hierarchy)

```jsonc
// Assistant text output
{"type": "assistant", "content": "string", "message_id": "string?"}

// Tool call initiated
{"type": "tool_call", "tool_call_id": "string", "tool_name": "string", "args": {}}

// Tool execution result
{"type": "tool_result", "tool_call_id": "string", "tool_name": "string",
 "result": {} | null, "error": "string?", "skipped": false,
 "duration": 1.23}

// Streaming output from a tool (e.g., bash stdout)
{"type": "tool_stream", "tool_call_id": "string", "tool_name": "string",
 "message": "string"}

// Model reasoning / chain-of-thought
{"type": "reasoning", "content": "string", "message_id": "string?"}

// Context compaction started
{"type": "compact_start", "current_context_tokens": 150000, "threshold": 200000}

// Context compaction completed
{"type": "compact_end", "old_context_tokens": 150000,
 "new_context_tokens": 50000, "summary_length": 2000}

// User message (echoed to all WS clients)
{"type": "user_message", "content": "string", "message_id": "string"}
```

#### Vibecheck-specific events (bridge → client)

```jsonc
// Agent is waiting for tool approval from user
{"type": "waiting_approval", "tool_call_id": "string",
 "tool_name": "string", "args": {}}

// Agent is waiting for user input
{"type": "waiting_input", "prompt": "string", "options": ["string"]?}

// Session state changed
{"type": "state_change", "session_id": "string",
 "status": "running|waiting_approval|waiting_input|idle|error",
 "detail": "string?"}

// Connection lifecycle
{"type": "connected", "session_id": "string"}
{"type": "heartbeat", "ts": "2026-02-28T12:00:00Z"}

// Error from bridge
{"type": "error", "message": "string", "recoverable": true}
```

#### State enum (canonical values)

```
running | waiting_approval | waiting_input | idle | error | disconnected
```

`disconnected` is only used in REST responses (session list), never over WS (if you're getting WS events, you're connected).

---

## 5. Backlog / Persistence Policy

| Data | Storage | Lifetime | Bound |
|------|---------|----------|-------|
| Event backlog (per session) | In-memory ring buffer | While bridge is attached | Last 500 events |
| WS client connections | In-memory set | Connection lifespan | Unbounded |
| Push subscriptions | File: `~/.vibecheck/push_subscriptions.json` | Persistent across restarts | Per-endpoint dedup |
| VAPID keys | File: `~/.vibecheck/vapid_keys.json` | Persistent, generated once | 1 keypair |
| Session metadata | Vibe-managed: `~/.vibe/logs/session/*/meta.json` | Vibe lifecycle | N/A |
| Translation cache | Client-side (localStorage) | Per-device, LRU | Last 200 translations |
| Settings (intensity, theme, lang) | Client-side (localStorage) | Per-device | N/A |

**On reconnect:** Client receives the last N events from the in-memory backlog (up to 500). This covers the common case of brief disconnects. There is no cross-restart persistence of events — Vibe's own `messages.jsonl` is the durable log.

**On detach:** Backlog is discarded. WS clients are notified with `{"type": "state_change", "status": "disconnected"}` and then disconnected.

---

## 6. Fallback Trigger (In-Process → Sidecar)

**Decision gate: WU-12 (Vibe bridge implementation).**

Switch to Option B (sidecar) if ANY of these occur during WU-12:

| Trigger | Detection |
|---------|-----------|
| `set_approval_callback()` doesn't fire | Bridge test: trigger a tool call, callback is never invoked after 10s |
| `message_observer` misses events | Bridge test: send a message, compare observed events vs expected |
| In-process import crashes | `import vibe.core.agent_loop` raises or has incompatible deps |
| AgentLoop lifecycle conflict | Can't run AgentLoop alongside FastAPI in same process (event loop collision) |

**WU-12 includes a "bridge smoke test" that runs all 4 checks.** If any fail, immediately switch to sidecar and re-scope WU-12 as:
- Launch Vibe in a subprocess
- Watch `~/.vibe/logs/session/*/messages.jsonl` for new events (file tail)
- Parse terminal output for waiting states

**Not a late debate.** WU-12 is Phase 2, well before integration. No code past WU-12 depends on which bridge mode is used — the `SessionBridge` interface is the same either way.

---

## 7. Test Gate Policy

### Per-WU gate (every work unit)

1. Run targeted test file(s) for the WU
2. Run full backend suite: `uv run pytest vibecheck/tests/ -v`
3. If frontend was touched: `cd vibecheck/frontend && npm run build`
4. Server must start: `uv run python -m vibecheck` (if backend changed)

**All 4 must pass before the WU is committed.**

### Phase gate (at phase boundaries: Phase 0, Phase 2, Phase 4)

All per-WU gates plus:
5. Smoke test: `scripts/smoke_test.sh http://localhost:7870`
6. Manual spot check of any new UI

### Rationale

Running the full suite on every WU is cheap (<10s for the backend at this stage) and catches cross-WU regressions immediately. The alternative — targeted-only per WU, full suite only at phase gates — saves a few seconds but risks compounding breakage between agents.

---

## 8. Mobile Support Baseline

### Demo device matrix

| Device | Role | Push | Voice | PWA Install |
|--------|------|------|-------|-------------|
| **Android Chrome (latest)** | Primary demo target | Full support | Full support | Full support |
| **iOS Safari 16.4+** | Secondary / audience | Requires Add to Home Screen | Full support | Requires Add to Home Screen prompt |
| **Desktop Chrome** | Dev testing only | Full support | Full support | N/A |

### Acceptance criteria (consistent across all WUs)

| Criterion | Spec |
|-----------|------|
| Primary screen width | 360px–428px (standard Android phones) |
| Touch targets | Minimum 44x44px |
| Safe area insets | `env(safe-area-inset-*)` for notched devices |
| Viewport | `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` |
| Theme color | `<meta name="theme-color" content="#FF7000">` |
| Orientation | Portrait-primary (manifest), responsive if landscape |
| Offline | Service worker caches app shell; shows "offline" state gracefully |
| iOS push caveat | Documented in demo script; not a blocker for acceptance |
| Android push | Must work without Add to Home Screen (Chrome supports it natively) |

### What we do NOT test for

- Tablets (iPad, Android tablets) — out of scope
- Older browsers (Chrome < 100, Safari < 16.4) — out of scope
- Wearables — out of scope

---

## Action Items

After team sign-off on this document:

1. **Update IMPLEMENTATION.md WU-01** — Change `WS /ws/events` to `WS /ws/events/{session_id}`
2. **Update IMPLEMENTATION.md WU-01** — Change auth default from `"dev"` to fail-on-missing
3. **Update PLAN.md** — Change `~/.vibe/sessions/` to `~/.vibe/logs/session/`
4. **Delete failed Phase 0 scaffold** — Previous Devstral attempt is broken; clean slate
5. **Restart WU-01 and WU-02** with these decisions locked in
