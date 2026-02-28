# vibecheck — Worklog

## 2026-02-28

### Repository setup
- Created `vibecheck` repo
- Created README.md (full product brief)
- Created docs/PLAN.md (L0-L9 layer architecture, parallel tracks, tech stack)
- Created docs/IMPLEMENTATION.md (WU-01 through WU-27, dependency graph, testing strategy, directory structure)
- Created docs/DEMO.md, docs/ANALYSIS-vibe.md, docs/USING-VIBE.md, docs/TODO.md
- Created docs/REMOTING-UI.md (mobile-to-TUI bridge research)
- Updated AGENTS.md/CLAUDE.md with correct `docs/` paths for all key files
- All cross-links verified (README ↔ docs/PLAN ↔ docs/IMPLEMENTATION)

### Reviewer 2 - Phase 0 audit (Vibe/Devstral)
- Reviewed WU-01/WU-02 scaffold output against `docs/IMPLEMENTATION.md` and `REVIEW-PROCESS.md`
- Executed verification checks (`npm run build`, pytest run, runtime API probe)
- Added findings and capability assessment to `docs/VIBE-REVIEW.md`
- Confirmed blockers: HTTP auth bypass, broken backend test fixture setup, and process non-compliance on commit/worklog hygiene

### Phase 0 punchlist reset (WU-01/WU-02)
- Updated `docs/IMPLEMENTATION.md` WU-01 to enforce strict PSK policy (`VIBECHECK_PSK` required, no default)
- Updated WU-01 route contract to `WS /ws/events/{session_id}` and session-id REST placeholders
- Updated WU-01 verification commands to explicit `export VIBECHECK_PSK=dev`, targeted auth tests, and full-suite gate
- Updated WU-02 mobile acceptance note to target 360px–428px phone widths and retained explicit frontend build gate

### Documentation consistency pass (README → PLAN → IMPLEMENTATION)
- Normalized session storage path references to `~/.vibe/logs/session/` across planning docs
- Standardized REST and WS route parameter naming to `{session_id}` across examples and WU specs
- Updated stale endpoint examples (`/api/approve`, `/api/input`, `/api/message`) to session-scoped paths
- Standardized status wording to `disconnected` (replacing mixed `detached` usage in API planning text)

### Phase 0 implementation (WU-01 + WU-02) redo
- Rebuilt Phase 0 from scratch in a clean tree using tests-first flow:
  - Added `vibecheck/tests/conftest.py` and `vibecheck/tests/test_auth.py` before implementation.
  - Confirmed red state first (`ModuleNotFoundError: No module named 'vibecheck'`) using `uv run --with ... pytest`.
- Implemented backend scaffold (`WU-01`) with root-level `pyproject.toml` and importable `vibecheck/` package:
  - Added FastAPI app factory (`vibecheck/app.py`) with CORS, lifespan hook, API/WS router mounting.
  - Added strict PSK middleware (`vibecheck/auth.py`) with fail-fast `VIBECHECK_PSK` requirement and timing-safe compare.
  - Added stub REST routes (`vibecheck/routes/api.py`) and WS scaffold (`vibecheck/ws.py`) with connect event + 30s heartbeat.
  - Added runtime entrypoint (`vibecheck/__main__.py`) for `uv run python -m vibecheck`.
- Implemented frontend scaffold (`WU-02`) via `npm create vite@latest vibecheck/frontend -- --template svelte`:
  - Configured `vite.config.js` proxy (`/api`, `/ws`) to `localhost:7870` and build output to `../static`.
  - Replaced default app with mobile shell layout in `src/App.svelte` (safe-area insets, 44px targets, dark theme vars).
  - Added PWA files (`public/manifest.json`, `public/sw.js`) and registered SW in `src/main.js`.
  - Generated placeholder icons: `public/icons/vibe-192.png` and `public/icons/vibe-512.png`.
- Updated ignore policy:
  - Added `vibecheck/frontend/node_modules/` and `vibecheck/static/` to root `.gitignore`.
- Verification results:
  - `uv run pytest vibecheck/tests/test_auth.py -v` -> 6 passed.
  - `uv run pytest vibecheck/tests/ -v` -> 6 passed.
  - Backend smoke: `uv run python -m vibecheck` + `curl` checks (`/api/health` 200, `/api/state` with PSK 200, without PSK 401).
  - Frontend: `cd vibecheck/frontend && npm install && npm run build` succeeded; output in `vibecheck/static/`.
  - Frontend dev probe: `npm run dev` served on `:5173` and responded to `curl`.

### Reviewer 2 - Phase 0 reimplementation audit
- Reviewed commit `baf0fa0` and re-ran claimed verification commands:
  - `uv run pytest vibecheck/tests/test_auth.py -v` -> 6 passed
  - `uv run pytest vibecheck/tests/ -v` -> 6 passed
  - `cd vibecheck/frontend && npm run build` -> success
- Ran additional integration checks against backend-hosted frontend assets/PWA files.
- Logged findings in `docs/VIBE-REVIEW.md`: quality is improved, but backend static mount currently breaks root asset and PWA paths (`/assets/*`, `/manifest.json`, `/sw.js`, `/icons/*` returning 404).

### Reviewer 2 - static/PWA routing fix verification
- Reviewed commit `9be9622` (`fix: serve frontend PWA assets from backend root`).
- Re-ran claimed validations:
  - `uv run pytest vibecheck/tests/test_static_frontend.py -v` -> passed
  - `uv run pytest vibecheck/tests/test_auth.py -v` -> 6 passed
  - `uv run pytest vibecheck/tests/ -v` -> 7 passed
- Reproduced runtime smoke with backend server:
  - `/`, `/assets/index-*.js`, `/manifest.json`, `/sw.js`, `/icons/vibe-192.png` all returned 200
  - `/api/state` with PSK returned 200; without PSK returned 401
- Appended acceptance follow-up notes to `docs/VIBE-REVIEW.md`.

### Phase 2 implementation (WU-09 to WU-12)
- Implemented typed event models in `vibecheck/events.py` and added round-trip/validation coverage in `vibecheck/tests/test_events.py`.
- Built out `SessionBridge`/`SessionManager` in `vibecheck/bridge.py` with:
  - per-session state, pending approval/input futures, backlog cap, and session discovery from `~/.vibe/logs/session/`
  - fleet aggregation and session detail helpers for API consumers
- Replaced stub API routes with real session-backed endpoints in `vibecheck/routes/api.py`:
  - `GET /api/state`, `GET /api/sessions`, `GET /api/sessions/{session_id}`, `GET /api/sessions/{session_id}/state`
  - `POST /api/sessions/{session_id}/approve|input|message`
- Reworked WebSocket manager in `vibecheck/ws.py`:
  - session rooms (`rooms`, `socket_to_session`) with `connect` auth, `disconnect`, `broadcast`, `broadcast_all`, `send_personal`
  - connect flow sends `connected` + `state` + backlog, plus 30s heartbeat task
  - teardown hardened so heartbeat-task failures/cancellation do not skip disconnect cleanup
- Expanded API/WS/bridge tests:
  - `vibecheck/tests/test_api.py`
  - `vibecheck/tests/test_ws.py`
  - `vibecheck/tests/test_bridge.py`
- Updated auth state assertions in `vibecheck/tests/test_auth.py` to match dynamic session discovery (`/api/state` values are non-negative ints, not hardcoded zeros).
- Verification:
  - `uv run pytest vibecheck/tests/test_events.py -v` -> passed
  - `uv run pytest vibecheck/tests/test_bridge.py -v` -> passed
  - `uv run pytest vibecheck/tests/test_api.py -v` -> passed
  - `uv run pytest vibecheck/tests/test_ws.py -v` -> passed
  - `uv run pytest vibecheck/tests/ -v` -> passed (34 tests)
  - backend smoke: `uv run python -m vibecheck` + `curl http://127.0.0.1:7870/api/health` returned `{"status":"ok"}`

### Live Vibe tap probe script (external process reality check)
- Added `scripts/probe_live_vibe_session.py` to probe a real session log under `~/.vibe/logs/session/` and print:
  - discovered target session metadata
  - parsed last-N events (`user_message`, `assistant`, `tool_call`, `tool_result`)
  - optional short tail window for new live log lines
  - explicit capability verdict that callback control cannot be attached from an external running `vibe` process
- Added reusable probe helpers in `vibecheck/live_probe.py` and test coverage in `vibecheck/tests/test_live_probe.py`.
- Verification:
  - `uv run pytest vibecheck/tests/test_live_probe.py -v` -> passed
  - `uv run pytest vibecheck/tests/ -v` -> passed (38 tests)
  - `uv run python scripts/probe_live_vibe_session.py --tail-seconds 3 --show-last 4` -> passed against live session logs

### Session attachment deep-dive analysis
- Added `docs/ANALYSIS-session-attachment.md` to clarify the distinction between:
  - discovery/observe-only attach
  - replay/resume attach (new loop from history)
  - true live attach to the same already-running terminal process
- Documented current constraints of in-process callback wiring (`set_approval_callback`, `set_user_input_callback`) and why unmanaged external `vibe` processes are not automatically controllable.
- Added recommended roadmap clarifications, attach-mode capability contract, incremental implementation plan, and validation criteria for the "coffee-walk control" promise.

### CRITICAL: Architecture gap identified — bridge creates new AgentLoop, cannot attach to running Vibe
- **Problem:** Phase 2's `SessionBridge` creates its own `AgentLoop` via `_ensure_agent_loop()`. It cannot control an already-running Vibe terminal process. Vibe has zero IPC — `set_approval_callback()` and `set_user_input_callback()` are in-process method calls, not network endpoints. The product promise ("run Vibe in terminal, control from phone") was impossible with the Phase 2 architecture.
- **Analysis:** Evaluated four architecture options:
  - **Option A: Managed startup** — vibecheck replaces vibe. Works but users lose Vibe's Textual TUI (rich tool approval dialogs, streaming output, syntax highlighting). This is what Phase 2 builds. Not acceptable because the UX promise requires terminal + mobile.
  - **Option B: Sidecar injection into Vibe's entry point** — `vibecheck-vibe` wraps Vibe's CLI. Same process runs Textual TUI + FastAPI/WebSocket server. One shared AgentLoop. **SELECTED.**
  - **Option C: tmux/PTY sidecar** — Terminal scraping. Fragile (heuristic parsing, keystroke simulation, state drift). Used by Happy and other Claude Code remoting apps — their UX shows the limitations. **Fallback only.**
  - **Option D: Upstream ACP** — Vibe's `resume_session()` is `NotImplemented`. Not viable for hackathon timeline.
- **Key architectural insight from Vibe source analysis:** In `vibe/cli/cli.py`, the flow is: create `AgentLoop` (line ~190) → pass to `run_textual_ui(agent_loop=agent_loop)` (line ~203). The TUI and AgentLoop are independent objects. Textual is built on asyncio. We can run uvicorn alongside it as a Textual worker in the same event loop.
- **Decision:** Option B primary, Option C fallback. User confirmed.

### Phase 3 (Live Attach) inserted into planning docs
- **`docs/ANALYSIS-session-attachment.md`** — Complete rewrite replacing colleague's initial draft. Now contains:
  - Problem statement (Vibe has no IPC)
  - Three attachment modes (observe-only, replay/resume, live attach)
  - Four architecture options with honest tradeoffs
  - Decision rationale (Option B primary, Option C fallback)
  - Detailed Option B architecture: single asyncio loop, bridge owns AgentLoop, event tee pattern, dual input, approval flow
  - Session API contract with `attach_mode` values
  - Acceptance test definition
  - Risk/mitigation table
- **`docs/PLAN.md`** — Updated:
  - Architecture diagram: now shows `vibecheck-vibe` with terminal + phone as parallel surfaces
  - Inserted Layer 1.5 (Live Attach) between L1 and L2
  - Updated dependency graph: L1.5 is prerequisite for all higher layers
  - Updated parallelism map: added L1.5 row (backend-only)
  - Updated Track A: added L1.5 entry
  - Fixed "In-process vs sidecar?" open question to reference Option B
- **`docs/IMPLEMENTATION.md`** — Major restructure:
  - Inserted new **Phase 3: Live Attach (L1.5)** with four work units:
    - WU-25: Bridge `attach_to_loop()` — wire callbacks on existing AgentLoop, add `attach_mode` field
    - WU-26: Event tee + TUI bridge rendering — `TuiBridge` adapter, event fan-out to TUI + WebSocket
    - WU-27: VibeCheckApp + launcher — Textual subclass, uvicorn as worker, `vibecheck-vibe` entry point
    - WU-28: Live attach integration test — mocked AgentLoop, real FastAPI, acceptance test
  - Renumbered all subsequent phases: Phase 3→4, 4→5, 5→6, 6→7, 7→8
  - Renumbered stretch WUs to avoid collision: WU-25→29, WU-26→30, WU-27→31
  - Updated: ToC, dependency graph, constraints table, WU table, parallelism map, directory structure
  - Added new files to directory structure: `tui_bridge.py`, `launcher.py`, `test_tui_bridge.py`, `test_launcher.py`, `test_live_attach.py`
- All 44 existing tests pass after changes (doc-only commit, no code changes).

### Reviewer 2 + Reviewer 3 findings on Phase 3 doc insertion
- Fixed 7 findings from Reviewer 2 and additional feedback from Reviewer 3:
  1. **Blocker fixed:** Normalized `act()` ownership — bridge is sole consumer in all modes (live + managed). Removed contradictory "TUI drives act() initially" language from IMPLEMENTATION.md.
  2. **High fixed:** Integration/deploy steps now reference `vibecheck-vibe` as primary startup path, with `python -m vibecheck` as standalone fallback.
  3. **High fixed:** Clarified discovered sessions are `observe_only` — live control requires sessions started via `vibecheck-vibe`. Added explicit notes in PLAN.md (L1 SessionManager, Open Questions) and IMPLEMENTATION.md (WU-12).
  4. **Medium fixed:** Gate labels corrected — Integration #1 says "after L1.5 + L2", stretch WUs reference Phase 5 gate.
  5. **Medium fixed:** Added `controllable` property alongside `attach_mode` in PLAN.md and IMPLEMENTATION.md — derived from mode, used by frontend to show/hide controls.
  6. **Medium fixed:** Normalized approval surface — both TUI keyboard and mobile REST can resolve pending approvals (first response wins). Per Reviewer 3: this is required for "go back and forth" UX, not stretch.
  7. **Low fixed:** Updated WU range from WU-27 to WU-31 in README.md and AGENTS.md.
- Added explicit Textual + uvicorn spike step in WU-27 (highest technical risk).
- Files changed: `docs/ANALYSIS-session-attachment.md`, `docs/PLAN.md`, `docs/IMPLEMENTATION.md`, `README.md`, `AGENTS.md`
