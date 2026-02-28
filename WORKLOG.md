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

### Frontend prototype planning
- Added `docs/FRONTEND-PROTOTYPE-IMPLEMENTATION.md` with milestone-based punchlist for the Voxtral STT + ElevenLabs TTS voice loop prototype

### Frontend prototype reviewer corrections
- Updated `frontend-prototype/server/server/app.py` to stream `/api/tts` responses back to clients instead of buffering full audio in memory.
- Hardened STT upload handling with chunked reads and early 413 rejection when payload size exceeds `STT_MAX_UPLOAD_BYTES`.
- Added explicit dev-intent comment for wildcard CORS in prototype backend.
- Removed unused `mistralai` dependency from `frontend-prototype/server/pyproject.toml` and aligned lockfile.
- Added `frontend-prototype/server/pytest.ini` and removed test-time `sys.path` mutation.
- Expanded backend tests for voice entry shape, STT 413 branch, STT auth-error mapping, and empty TTS upstream audio branch.
- Aligned prototype docs to implemented backend contract and corrected backend verification command to run from `frontend-prototype/server`.

### Frontend prototype milestone 2 (UI skeleton)
- Added frontend component test setup for Svelte 5 (`vitest`, `@testing-library/svelte`, `@testing-library/jest-dom`, `jsdom`) with Vite `svelteTesting()` integration.
- Wrote red-first component tests in `frontend-prototype/frontend/src/App.test.js` for Milestone 2 acceptance: explicit state-preview controls and error-state preview behavior.
- Implemented a `State Preview` panel in `frontend-prototype/frontend/src/App.svelte` so `idle`, `recording`, `transcribing`, `speaking`, and `error` can be forced without API calls.
- Added state-specific visual styling in `frontend-prototype/frontend/src/app.css` for clearer differentiation across all five UI states while preserving mobile-safe spacing and touch target sizing.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 2 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.

### Frontend prototype review fixes (milestone 2 hardening)
- Fixed preview-state safety regression in `frontend-prototype/frontend/src/App.svelte`: changing preview state now stops active `MediaRecorder` sessions and suppresses processing for intentionally dropped preview cancellations.
- Added status accessibility announcement (`role="status"`, `aria-live="polite"`) so state/status changes are announced to assistive tech.
- Expanded frontend tests in `frontend-prototype/frontend/src/App.test.js`:
  - Assert per-state preview transitions update state pill + surface classes for all five states.
  - Assert preview transition during active recording calls recorder `stop()` and stops audio tracks (prevents orphan mic capture).
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 4 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
- Mobile verification attempt:
  - Tried Playwright mobile screenshot smoke check (`iPhone 12`, `Pixel 7`) against local Vite dev server.
  - Blocked in current environment due missing host browser libs required by Playwright runtime (`libevent-2.1-7t64`, `libgstreamer-plugins-bad1.0-0`, `libflite1`, `libavif16`).
  - Manual on-device iOS/Android check remains pending.

### Frontend prototype Playwright setup (CLI + project integration)
- Added Playwright as a project dev dependency in `frontend-prototype/frontend` (`@playwright/test`) to avoid transient `npx` installs.
- Added `frontend-prototype/frontend/playwright.config.js` with:
  - Mobile projects (`Pixel 7`, `iPhone 12`)
  - Local dev `webServer` startup on `127.0.0.1:4178`
  - HTML report output enabled
- Added mobile smoke test `frontend-prototype/frontend/e2e/mobile-smoke.spec.js`:
  - Verifies core UI render on mobile projects
  - Stubs `/api/voices` so test is backend-independent
  - Verifies all five preview states update the visible state pill
- Added npm scripts:
  - `test:e2e`
  - `test:e2e:headed`
- Updated `frontend-prototype/.gitignore` for Playwright artifacts:
  - `frontend/playwright-report/`
  - `frontend/test-results/`
- Updated Vitest include pattern in `frontend-prototype/frontend/vite.config.js` so unit test runs exclude Playwright e2e specs.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 4 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 2 passed (`Mobile Chrome`, `Mobile Safari`).

### Frontend prototype follow-up review fixes (race + test isolation)
- Hardened recording lifecycle in `frontend-prototype/frontend/src/App.svelte` to prevent stale `onstop` callbacks from prior recordings mutating active recorder state:
  - Added per-recording session IDs.
  - Switched preview-cancel tracking from single boolean to session ID set.
  - Scoped `onstop`/`onerror` handlers to captured recorder/stream instances.
  - Updated `stopTracks` to support targeted stream shutdown.
- Removed unreachable `if (!currentAudio)` branch in `playAudioBlob` by using a local `audio` instance binding.
- Simplified state pill rendering to display `uiState` directly (removed redundant state-label mapping).
- Improved unit test isolation in `frontend-prototype/frontend/src/App.test.js` by restoring `navigator.mediaDevices` descriptors in tests that override them.
- Added regression test for rapid re-record scenario:
  - Start recording A -> preview-cancel A -> start recording B -> flush delayed onstop for A.
  - Assert stream B is not stopped by A’s stale callback.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 5 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 2 passed.

### Frontend prototype reviewer sync fixes (style + stale onerror guard)
- Updated event handler syntax in `frontend-prototype/frontend/src/App.svelte` from legacy `on:click` to Svelte 5 style `onclick` for all button handlers.
- Replaced `void` fire-and-forget async calls with explicit `.catch(...)` handling:
  - `loadVoices().catch(...)` in `onMount`
  - `processRecording(...).catch(...)` in recorder `onstop`
- Added stale-session isolation in recorder `onerror`:
  - Old recorder errors now return early without forcing global `uiState=error` when the recorder/session is no longer active.
- Added regression coverage in `frontend-prototype/frontend/src/App.test.js`:
  - New test confirms stale errors from prior recorder sessions do not disrupt an active newer recording.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 6 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 2 passed.

### Frontend prototype final race fix (stale onerror before delayed onstop)
- Added regression test in `frontend-prototype/frontend/src/App.test.js` for ordering:
  - preview-cancel recording A
  - start recording B
  - stale `onerror` from A fires before delayed `onstop` from A
  - assert A is still treated as dropped and does not disrupt recording B
- Fixed stale callback handling in `frontend-prototype/frontend/src/App.svelte`:
  - stale `recorder.onerror` no longer clears dropped-session marker, so delayed `onstop` still short-circuits as canceled.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 7 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 2 passed.

### Frontend prototype milestone 3 kickoff (STT integration verification)
- Read `docs/PLAN.md`, `docs/IMPLEMENTATION.md`, `docs/FRONTEND-PROTOTYPE-PLAN.md`, and `docs/FRONTEND-PROTOTYPE-IMPLEMENTATION.md` to align milestone scope before changes.
- Added Milestone 3-focused frontend tests in `frontend-prototype/frontend/src/App.test.js`:
  - record -> stop -> `/api/stt` upload -> transcript render
  - microphone permission denied path with actionable UI error
  - short recording validation path (no STT call)
  - STT failure retry path (`Retry STT` re-attempts transcription)
- Result: all new tests passed with current `App.svelte` implementation, confirming Milestone 3 behavior was already present and stable.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 11 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.

### Frontend prototype reviewer-feedback fixes (milestone 3)
- Addressed reviewer gap in M3 success-path testing by mocking `/api/tts` and playback dependencies in frontend unit tests:
  - Added deterministic playback mocks (`Audio`, `URL.createObjectURL`, `URL.revokeObjectURL`) so STT + TTS can run to completion in jsdom.
  - Updated M3 success test to assert clean completion (`state=idle`, status `Playback complete`, no error panel).
- Added frontend test coverage requested by reviewers:
  - STT FormData shape check (`audio` + `language`).
  - Unsupported browser path (`MediaRecorder` unavailable).
  - Empty STT response text mapping (`Transcription came back empty`).
  - Explicit byte-size short-audio guard coverage.
- Replaced fragile microtask flush (`await Promise.resolve()`) with `waitFor(...)` in delayed-stop race test.
- Aligned frontend short-audio threshold with backend default:
  - Updated `MIN_AUDIO_BYTES` in `frontend-prototype/frontend/src/App.svelte` from `1024` to `2048`.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 15 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 2 passed.

### Frontend prototype milestone 4 kickoff (TTS integration + playback)
- Read `docs/PLAN.md`, `docs/IMPLEMENTATION.md`, `docs/FRONTEND-PROTOTYPE-PLAN.md`, and `docs/FRONTEND-PROTOTYPE-IMPLEMENTATION.md` to align Milestone 4 scope and exit criteria.
- Added Milestone 4 frontend tests first in `frontend-prototype/frontend/src/App.test.js`:
  - selected voice ID is sent in `/api/tts` payload
  - speaking state includes explicit playback status messaging during active audio playback
  - playback failures surface actionable errors and recover through `Retry TTS`
- Confirmed red-first failure for the new speaking-status expectation (`Expected: "Speaking...", Received: "Generating speech..."`).
- Implemented Milestone 4 UI behavior in `frontend-prototype/frontend/src/App.svelte` by switching status to `Speaking...` when audio playback starts.
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 17 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/server && uv run pytest tests -v` -> 17 passed.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 2 passed (`Mobile Chrome`, `Mobile Safari`).

### Frontend prototype milestone 4 reviewer-feedback hardening
- Addressed M4 frontend test gaps and duplication in `frontend-prototype/frontend/src/App.test.js`:
  - Switched milestone 4 tests to use shared `installPlaybackMocks()` setup/teardown via `beforeEach`/`afterEach` (removed duplicated manual `URL.createObjectURL`, `URL.revokeObjectURL`, and restore blocks).
  - Added frontend test for `/api/tts` HTTP error mapping with detail message assertion and `Retry TTS` visibility.
  - Added frontend test for empty-audio response path (`audioBlob.size === 0`) asserting `TTS returned empty audio`.
  - Added regression test ensuring `Retry TTS` is hidden after a later STT failure so stale transcript text cannot be replayed.
- Hardened milestone 4 UI behavior in `frontend-prototype/frontend/src/App.svelte`:
  - `Retry TTS` now renders only when `lastFailedStage === 'tts'`.
  - `retryTts()` now guards by failure stage and retries current transcript only.
  - Removed redundant `lastTtsText` state and dead fallback path.
  - Removed duplicate normal-path transcribing status assignment by making it conditional (still set for retry STT path).
  - Removed ineffective `audio.preload` assignment after `new Audio(src)`.
- Added browser-level mobile e2e coverage in `frontend-prototype/frontend/e2e/mobile-smoke.spec.js`:
  - deterministic in-page mocks for `MediaRecorder`, `Audio`, `mediaDevices`, and `Date.now`
  - success path coverage: `/api/stt -> /api/tts -> playback complete` with selected voice payload assertion
  - failure/recovery coverage: `/api/tts` HTTP 502 detail surfaced, then `Retry TTS` succeeds
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 20 passed.
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 6 passed (`Mobile Chrome`, `Mobile Safari`).
  - `cd frontend-prototype/server && uv run pytest tests -v` -> 17 passed.

### Frontend prototype backend hotfix (TTS stream consumed twice)
- Investigated production-like runtime error during `/api/tts` playback: `httpx.StreamConsumed` raised from `server/app.py` while streaming ElevenLabs response.
- Root cause: endpoint consumed `upstream_response.aiter_bytes()` once to probe first chunk, then called `aiter_bytes()` again in `stream_body()`. `httpx` streams are single-pass.
- Added red-first regression test in `frontend-prototype/server/tests/test_api.py`:
  - `test_tts_reads_upstream_stream_in_single_pass` uses a single-pass fake upstream response that raises `httpx.StreamConsumed` on second iterator construction.
- Fixed `frontend-prototype/server/server/app.py`:
  - create one shared iterator (`upstream_stream = upstream_response.aiter_bytes()`)
  - read first non-empty chunk from that iterator
  - continue streaming remaining chunks from the same iterator
  - broadened stream-read exception handling to include `httpx.StreamError` in both preflight read and mid-stream path
- Updated mid-stream failure test to model single-iterator semantics and keep expected abort behavior.
- Verification:
  - `cd frontend-prototype/server && uv run pytest tests/test_api.py::test_tts_reads_upstream_stream_in_single_pass -v` -> passed (after initial red failure).
  - `cd frontend-prototype/server && uv run pytest tests -v` -> 18 passed.
  - Startup smoke: `uv run uvicorn server.app:app --host 127.0.0.1 --port 8780` + `curl http://127.0.0.1:8780/health` -> `{"status":"ok"}`.

### Frontend prototype milestone 5 kickoff (hardening + mobile QA)
- Read `docs/PLAN.md`, `docs/IMPLEMENTATION.md`, `docs/FRONTEND-PROTOTYPE-PLAN.md`, and `docs/FRONTEND-PROTOTYPE-IMPLEMENTATION.md` to align Milestone 5 scope and exit criteria.
- Added Milestone 5 frontend tests first in `frontend-prototype/frontend/src/App.test.js`:
  - clears stale transcript state when starting a new recording after a completed prior run
  - disables non-essential controls (preview buttons) while transcription requests are in flight
  - verifies browser request shape uses only local `/api/*` proxy routes with no provider auth headers
- Confirmed red-first failures for new hardening requirements:
  - stale transcript not cleared on new recording start
  - preview controls remained enabled during active transcription
- Implemented Milestone 5 hardening in `frontend-prototype/frontend/src/App.svelte`:
  - added `requestInFlight` state to lock non-essential controls only during real network work (without breaking preview-mode state demos)
  - cleared stale transcript and stale retry blob state on new recording start
  - added retry guards/disabled states to prevent concurrent retry actions during active work
- Expanded mobile e2e QA in `frontend-prototype/frontend/e2e/mobile-smoke.spec.js`:
  - STT failure + `Retry STT` recovery flow
  - control-lock assertions during in-flight transcription
  - proxy-only network behavior assertion (no direct `api.mistral.ai` or `api.elevenlabs.io` calls; no browser provider auth headers)
- Verification:
  - `cd frontend-prototype/frontend && npm test` -> 23 passed.
  - `cd frontend-prototype/frontend && npm run test:e2e` -> 12 passed (`Mobile Chrome`, `Mobile Safari`).
  - `cd frontend-prototype/frontend && npm run build` -> succeeded.
  - `cd frontend-prototype/server && uv run pytest tests -v` -> 18 passed.
  - `cd frontend-prototype/frontend && rg -n "MISTRAL_API_KEY|ELEVENLABS_API_KEY|api\\.mistral\\.ai|api\\.elevenlabs\\.io|xi-api-key|Authorization" src dist --glob '!src/**/*.test.js'` -> no matches.
