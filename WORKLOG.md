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
