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

---

## Phase 3 Validation: Confirmed Gaps

> **Context:** Phase 3 (WU-25–28) is complete. Bridge mechanics are correct: 60 unit/integration tests pass covering callback ownership, event tee, dual-surface resolution, raw event listeners, and attach mode classification. The gaps below are **TUI integration layer** issues that only manifest with the real Vibe Textual app — they cannot be caught by unit tests that mock Textual internals.

### Gap 1 (High): TUI stuck in approval/question UI after mobile resolves

**The problem:** In Vibe, the approval flow has two layers:

1. **asyncio layer:** `_pending_approval = asyncio.Future()` — awaited in the callback, resolved when the user acts
2. **Textual UI layer:** `_switch_to_approval_app(tool, args)` swaps the bottom dock to show the approval widget. Switching BACK to the input area happens in `on_approval_app_approval_granted` / `on_approval_app_approval_rejected` — Textual event handlers that fire when the user clicks buttons in the approval widget

Our `_settle_local_approval_state()` (bridge.py) correctly resolves layer 1 (sets the Future result so the callback returns and the AgentLoop continues). But it does NOT trigger layer 2 — the `on_approval_app_*` handlers never fire, so the Textual UI stays stuck showing the approval widget with the input area hidden.

**Reference:** `vibe/cli/textual_ui/app.py:666–682` (approval callback sets Future and switches UI), `app.py:399–425` (event handlers that switch UI back)

**Impact:** Terminal is visually frozen. The agent continues, mobile works, but the TUI shows a dead approval dialog. Breaks the "both surfaces work" promise.

**Fix direction:** After settle resolves the Future, fire a synthetic Textual message (e.g., `self.post_message(ApprovalAppApprovalGranted())`) to trigger Vibe's existing UI cleanup path. Alternatively, call `_switch_to_input_app()` directly. Both require reaching into Vibe's Textual internals.

Same pattern applies to `_pending_question` / `on_question_app_answered`.

### Gap 2 (Medium): Mobile-injected prompts invisible in terminal

**The problem:** Vibe's `EventHandler.handle_event()` intentionally no-ops on `UserMessageEvent` (reference `event_handler.py:65`). This is by design: in normal Vibe, the TUI mounts the user message widget *before* calling `act()`, making the event redundant.

When the phone injects a message via `bridge.inject_message()` → `_message_worker` → `act()`:
- `act()` yields `UserMessageEvent`
- Raw event tee delivers to TuiBridge → `EventHandler.handle_event()`
- EventHandler ignores `UserMessageEvent`
- Terminal shows tool calls and assistant response but NOT the originating user prompt

The terminal user sees "ghost conversations" — the agent suddenly starts working with no visible prompt.

**Fix options:**
1. In `TuiBridge`, detect `UserMessageEvent` from remote sources and explicitly mount a user message widget
2. Before `act()`, emit a synthetic chat message into the TUI
3. Accept the limitation and document it (phone user sees everything; terminal sees agent output only)

For hackathon, option 3 is defensible. The phone is the primary control surface when the user is away from the terminal.

### Gap 3 (Medium): `_handle_agent_loop_turn` override drops TUI lifecycle

**The problem:** Our override (launcher.py) routes terminal keyboard input to `bridge.inject_message()`, bypassing Vibe's original `_handle_agent_loop_turn` which manages:

| Vibe behavior | Our override | Impact |
|---|---|---|
| `_agent_running` guard (prevents concurrent turns) | Dropped — bridge `_message_queue` serializes instead | Equivalent. No regression. |
| Loading widget lifecycle (`_loading_widget` mount/unmount) | Dropped | No "thinking" indicator during agent work |
| Interrupt behavior (Ctrl+C during turn) | Dropped | Terminal user can't interrupt a running turn |
| History refresh after turn | Dropped | Stale history if terminal user scrolls up |

The queue substitution for `_agent_running` is correct. The loading widget and interrupt losses are noticeable but not critical.

**Fix direction:** Document what's dropped. Optionally reintroduce loading widget by mounting it before `inject_message` and unmounting via event listener when the turn completes.

### Summary

| Gap | Severity | Required for demo? | Fix approach |
|-----|----------|-------------------|--------------|
| TUI stuck in approval UI | High | Yes — terminal freezes visibly | Fire synthetic Textual messages to trigger UI cleanup |
| Mobile prompts invisible | Medium | No — phone user sees everything | Document as known limitation |
| Lifecycle bypass | Medium | No — agent works correctly | Document; loading widget is nice-to-have |

These gaps are tracked as **Phase 3.1: TUI Integration Hardening** in `docs/IMPLEMENTATION.md` (WU-32 through WU-34).
