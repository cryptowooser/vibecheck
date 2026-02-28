# Session Attachment: Architecture Analysis & Decision

> **Status:** Decision made — Option B selected, Option C as fallback
> **Last updated:** 2026-02-28
> **Authors:** Reviewer 1 (architecture analysis), Reviewer 2 (initial taxonomy)

## The Product Promise

You run Vibe in your terminal. You leave your desk. You continue controlling that same ongoing session from your phone.

This is not "start a new mobile-only session." This is not "read old logs." This is live, bidirectional control of the same AgentLoop — approvals, input, messages — from a phone while the terminal session continues.

## The Problem

**Vibe has zero IPC.** No sockets, no pipes, no shared memory, no control protocol.

`AgentLoop.set_approval_callback()` and `set_user_input_callback()` are in-process method calls on a Python object. If Vibe is running in PID 1234 and vibecheck is PID 5678, there is no mechanism for vibecheck to call methods on that other process's AgentLoop.

Even Vibe's own ACP entry point (`vibe-acp`) works by spawning a *new* AgentLoop per client, not attaching to existing ones. `resume_session()` in ACP is `NotImplemented`.

Session log files (`~/.vibe/logs/session/*/messages.jsonl`) are write-only from Vibe's perspective. They are not a bidirectional control channel.

## Three Attachment Modes

Any solution must be explicit about which mode it provides. The original roadmap language ("discover/attach") was ambiguous.

### Observe-only

Read `messages.jsonl` and `meta.json` from disk. See what happened. No live control. Good for monitoring dashboards. This is what `SessionManager.discover()` currently provides.

### Replay / Resume

Create a new `AgentLoop`, load prior message history from session logs, continue the conversation from similar context. New process, new callbacks. Not the same running session — the terminal Vibe doesn't know about it.

### Live Attach

Mobile actions resolve callbacks on the exact AgentLoop already running in the terminal. Same process, same object, same Futures. This is what the product promise requires.

## Architecture Options

### Option A: Managed Startup (vibecheck replaces vibe)

vibecheck creates its own AgentLoop in-process. Users interact with Vibe exclusively through vibecheck. No terminal Vibe.

```
Phone → vibecheck process → AgentLoop → Mistral API
```

**This is what Phase 2 currently implements.**

**Why it's insufficient:** Users don't get Vibe's Textual TUI — the rich terminal interface with tool approval dialogs, streaming output, syntax highlighting, and the full interactive experience. vibecheck would need to rebuild all of that from scratch. This isn't wrap-and-enhance; it's a rewrite. The terminal becomes a log stream, not the Vibe experience.

For the demo, this means we can't show "Vibe running in a terminal" — we'd show vibecheck's terminal output, which isn't Vibe.

### Option B: Sidecar Injection into Vibe's Entry Point (SELECTED)

vibecheck wraps Vibe's CLI entry point. Same process runs both the Textual TUI and vibecheck's FastAPI/WebSocket server. One AgentLoop shared between terminal and phone.

```
Terminal (Textual TUI) ──┐
                         ├── vibecheck-vibe process ── AgentLoop ── Mistral API
Phone (PWA via WSS) ─────┘
```

**Why this works:** Vibe's AgentLoop and Textual TUI are independent objects. The TUI doesn't embed the loop — it receives it as a parameter. Textual is built on asyncio, so we can run uvicorn alongside it in the same event loop. The bridge owns the AgentLoop's callbacks; both TUI and mobile are parallel input/display surfaces.

**Key insight from Vibe source analysis:** In `vibe/cli/cli.py`, the flow is:
1. Create `AgentLoop` (line ~190)
2. Pass to `run_textual_ui(agent_loop=agent_loop, ...)` (line ~203)

The TUI's `on_mount()` calls `set_approval_callback()` and `set_user_input_callback()` on the loop it received. We intercept this by subclassing `VibeApp` and having our bridge set callbacks first, or wrapping the TUI's callbacks with a dual-channel version.

**Tradeoff:** We depend on Vibe's internal Textual class structure (`VibeApp`, `_handle_agent_loop_turn`, `on_chat_input_container_submitted`). These are private APIs that could change with Vibe updates. Acceptable for a hackathon; pin the Vibe version.

### Option C: tmux/PTY Sidecar (FALLBACK)

User runs normal `vibe` in a tmux session. vibecheck attaches to the tmux pane, scrapes terminal output, and sends keystrokes to approve.

```
Terminal (tmux) ── vibe process ── AgentLoop
                     ↕ (terminal scraping)
                   vibecheck sidecar
                     ↕ (WebSocket)
                   Phone
```

**Why this is fragile:**

- **Parsing terminal output heuristically.** The TUI renders with Rich/Textual markup. Extracting semantic content (tool name, args, approval state) from rendered terminal cells is error-prone. Layout changes (terminal resize, different tool output length) break parsing.
- **Sending keystrokes to approve.** You're simulating keyboard input to navigate the approval dialog. If the TUI adds a new button or changes the key binding, the automation breaks silently.
- **No typed events.** Everything is strings scraped from terminal cells. You lose Pydantic model validation, event IDs, timestamps — all the structure that makes the mobile UI clean.
- **State drift.** The scraper's model of "what's on screen" can desync from reality. Network latency, rapid output, and terminal redraws cause the scraper to miss or misinterpret state.

**This is the pattern used by Happy and other Claude Code remoting apps.** Their UX reflects the limitations — dropped characters, missed state transitions, noticeable lag between terminal action and mobile update.

**We use this only if Option B fails.**

### Option D: Upstream ACP

Wait for Vibe's ACP to implement `resume_session()` and expose a network-accessible control plane.

**Not viable for hackathon.** `resume_session()` is `NotImplemented` in current Vibe. External dependency with unknown timeline. Even if it shipped tomorrow, it would be replay/resume semantics, not live attach to a running TUI.

## Decision

**Option B is the primary path.** vibecheck wraps Vibe's CLI, runs TUI + WebSocket in the same process, bridge owns the AgentLoop.

**Option C is the fallback.** If subclassing VibeApp and sharing the event loop proves unworkable within the hackathon timeline, fall back to tmux scraping. Brittle but demoable.

## Architecture: How Option B Works

### Single asyncio loop

Textual's `app.run()` manages an asyncio event loop. We run uvicorn's `Server.serve()` as a Textual worker in the same loop. No threading, no cross-loop communication. Bridge callbacks, WebSocket sends, and TUI rendering all share one loop.

### Bridge owns AgentLoop

The bridge's `_message_worker` serializes all input (terminal keyboard + mobile REST) through a single `asyncio.Queue`. The bridge drives `act()` and fans events out to both the TUI renderer and WebSocket clients. The TUI doesn't call `act()` directly — it receives events from the bridge and renders them.

This avoids the "two consumers of one async generator" problem: `act()` returns an async generator that can only be iterated once. The bridge is the single consumer; it tees events to multiple destinations.

### Dual input

```
Terminal keyboard → on_chat_input_container_submitted → bridge.inject_message()
Mobile REST      → POST /api/sessions/{id}/message   → bridge.inject_message()
                                                         ↓
                                                    _message_queue
                                                         ↓
                                                    _message_worker
                                                         ↓
                                                    agent_loop.act()
                                                         ↓
                                              events fan out to TUI + WS
```

### Approval flow

AgentLoop calls the approval callback (bridge's). Bridge creates a pending approval, broadcasts to mobile via WebSocket, shows an indicator in the TUI. Mobile approves via REST → bridge resolves the Future → AgentLoop proceeds → both TUI and mobile update.

Both TUI and mobile can resolve approvals — first response wins. This is required for the "go back and forth" UX: user can approve from either surface depending on where they are.

### Session API contract

```json
{
  "id": "session-abc",
  "state": "waiting_approval",
  "attach_mode": "live",
  "controllable": true
}
```

`attach_mode` values:
- `live` — bridge owns the AgentLoop, full control from mobile
- `replay` — new loop loaded from session history, independent of terminal
- `observe_only` — read-only access to session logs
- `managed` — vibecheck created the loop (no TUI), full control

## Acceptance Test

> Terminal shows Vibe TUI. Phone shows vibecheck PWA. Agent runs a tool. Pending approval visible on both surfaces. User approves from phone. Terminal TUI shows tool proceeding. Phone shows tool result.

## Implementation

See `docs/IMPLEMENTATION.md` Phase 3 (Live Attach): WU-25 through WU-28.

## Risks

| Risk | Mitigation |
|------|------------|
| Textual + uvicorn in same loop conflicts | Test early in WU-27. Fall back to background thread if needed. |
| VibeApp internal APIs change | Pin Vibe version. Document which internals we depend on. |
| TUI event rendering breaks with pushed events | Test in WU-26 with mock event handler. |
| Option B fails entirely | Fall back to Option C (tmux/PTY sidecar). |
