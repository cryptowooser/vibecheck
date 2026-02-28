# Vibe/Devstral Review Log

## 2026-02-28 - Reviewer 2 - Phase 0 (WU-01, WU-02)

### Verdict
- Phase 0 is **not complete**. Multiple blocking defects contradict the reported verification summary.

### Blocking findings
- **Auth bypass on all HTTP routes** (`vibecheck/auth.py:22-24`): exempt path list includes `"/"`, and middleware uses `startswith`, so every path is exempt. Protected routes (`/api/state`, `/api/sessions`, etc.) currently return 200 without PSK.
- **Backend tests are broken and do not validate claims** (`vibecheck/tests/conftest.py:9-17`): async fixture is declared with `@pytest.fixture` in strict asyncio mode; test run errors before assertions execute. Also uses outdated `AsyncClient(app=...)` style instead of transport-based client.
- **WU-01 verification command does not pass as documented**: `uv run pytest vibecheck/tests/ -v` fails from repo root due package layout/import behavior (`ModuleNotFoundError: No module named 'vibecheck'`).

### Major findings
- **WebSocket scaffold does not match WU-01 contract** (`vibecheck/ws.py:78-90`): implemented route is `/ws/events/{session_id}` while WU-01 specifies `/ws/events`; heartbeat is not periodic every 30s and only replies after client sends text.
- **PWA manifest references missing icon assets** (`vibecheck/frontend/public/manifest.json:10-19`): `/icons/vibe-192.png` and `/icons/vibe-512.png` are not present.
- **Frontend toolchain mismatch warning during build** (`vibecheck/frontend/package.json:12-16`): Svelte 5 with vite-plugin-svelte v3 triggers compatibility warning.

### Process/compliance findings (AGENTS.md)
- No Phase 0 completion entry was added to `WORKLOG.md` by implementer.
- No commit exists for completed WU-01/WU-02 work despite completion claim (`git log` unchanged at setup commit).
- `.gitignore` was not updated for `vibecheck/frontend/node_modules/` and `vibecheck/static/` as required by WU-02 checklist.

### Evidence run by reviewer
- `cd vibecheck/frontend && npm run build` -> succeeds, but with Svelte plugin compatibility warning.
- `cd vibecheck && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests -v` -> fixture/plugin errors (no passing verification).
- Runtime probe (ASGI transport) shows `/api/state` and `/api/sessions` return 200 without PSK.

### Reviewer assessment of coding capability (Phase 0 sample)
- Positive: scaffold velocity is high; basic project shape and route wiring are in place.
- Negative: verification quality is low (reported pass conditions not reproducible), and core security behavior was missed in both implementation and tests.
- Current confidence for Phase 1/2 autonomy: **low until test rigor and claim accuracy improve**.

---

## 2026-02-28 - Reviewer 1 (Claude Opus 4.6) - Phase 0 (WU-01, WU-02)

### Verdict
**FAIL — critical bugs, nothing actually runs.** Devstral's verification claims are not reproducible.

### Blocking Defects (P0)

**P0-1: Package structure is broken — nothing is importable**
- `vibecheck/pyproject.toml` lives at the same level as `__init__.py`
- Hatch config `packages = ["vibecheck"]` looks for `vibecheck/vibecheck/vibecheck/` which doesn't exist
- `uv run python -m vibecheck` → `ModuleNotFoundError: No module named 'vibecheck'`
- `uv run pytest vibecheck/tests/ -v` → same error
- **The server cannot start. The tests cannot run. Every "verification" Devstral claimed is impossible.**
- Fix: move `pyproject.toml` to repo root, or change hatch config

**P0-2: Auth middleware exempts ALL paths (security bypass)**
- `vibecheck/auth.py:22-24`: `exempt_paths = ["/", "/api/health", "/static/"]`
- Check uses `startswith("/")` → True for every URL path
- PSK authentication is effectively disabled for every endpoint
- Verified independently: `/api/state`, `/api/sessions`, `/ws/events/test` all exempt
- Tests in `test_auth.py` would catch this (they expect 401) — if they could run

**P0-3: Zero git commits**
- AGENTS.md: "Commit immediately after validation passes"
- All work is in untracked files — no history, no collaboration visibility
- A single `git clean` would destroy everything

**P0-4: WORKLOG.md not updated**
- AGENTS.md: "Update WORKLOG.md with what you completed"
- No entry for WU-01 or WU-02

### Critical Defects (P1)

**P1-1: Missing required dependencies**
- WU-01 spec requires: `fastapi, uvicorn[standard], websockets, pydantic>=2, mistralai, pywebpush, httpx`
- Missing: `uvicorn[standard]` (bare uvicorn lacks websocket protocol support), `mistralai`, `pywebpush`

**P1-2: `ConnectionManager.disconnect` mutates dict during iteration**
- `vibecheck/ws.py:31-37`: `del self.active_connections[session_id]` inside `for ... in self.active_connections.items()`
- Technically safe due to immediate `break`, but fragile — removing the `break` would cause `RuntimeError`

**P1-3: Deprecated `[tool.uv]` syntax**
- Every `uv run` prints deprecation warning
- Should use `[dependency-groups] dev` instead of `[tool.uv] dev-dependencies`

### Moderate Defects (P2)

**P2-1: Frontend uses Svelte 4 mount API**
- `main.js:16`: `new App({target: ...})` is Svelte 4 pattern
- Svelte 5 uses `import { mount } from 'svelte'; mount(App, {target: ...})`
- Works via compat layer but violates "Svelte 5" requirement

**P2-2: Missing PWA icons**
- `manifest.json` references `/icons/vibe-192.png` and `/icons/vibe-512.png` — files don't exist
- PWA install will fail or show broken icons

**P2-3: Missing mobile CSS requirements (WU-02)**
- No `viewport-fit=cover` in meta viewport tag
- No `env(safe-area-inset-*)` CSS
- No minimum 44px touch targets
- No `<meta name="theme-color">` tag

**P2-4: WebSocket endpoint deviates from spec**
- Spec: `WS /ws/events` — Actual: `WS /ws/events/{session_id}`
- Spec: "heartbeat every 30s" — Actual: echo-only, no server-initiated heartbeat

**P2-5: `app.py` uses `os.path` instead of `pathlib`**
- CLAUDE.md: "pathlib.Path for filesystem ops"
- Uses `os.path.abspath`, `os.path.join`, `os.path.dirname`, `os.path.exists`

**P2-6: Silent exception swallowing**
- `app.py:53-54`: `except Exception: pass` hides all errors during static file mounting

**P2-7: `.gitignore` missing frontend entries**
- WU-02: "Add to .gitignore: vibecheck/frontend/node_modules/, vibecheck/static/"
- Neither entry present — `node_modules` not in gitignore at all

### Minor (P3)

- `import os` inside function body (`app.py:47`) instead of top-level
- Redundant unused import in `conftest.py:2` (`from httpx import AsyncClient`)
- `vite-plugin-svelte@3` should be `@4` for Svelte 5

### What Devstral Got Right

1. **File structure matches the spec** — correct files in correct locations
2. **Test scenarios are well-chosen** — health no-auth, valid PSK, bad PSK, no PSK, query param PSK
3. **Frontend build succeeds** — Svelte/Vite chain produces output
4. **Vite proxy config is correct** — `/api` and `/ws` properly proxied
5. **App factory pattern is sound** — CORS, lifespan, route mounting all reasonable
6. **WebSocket ConnectionManager design is good** — session-keyed connections with broadcast
7. **Dark/light theme CSS is clean** — CSS custom properties with `prefers-color-scheme`
8. **Service worker structure is correct** — install, fetch, push handlers

### Assessment of Devstral 2's Coding Capability

**Pattern recognition: Good.** Code *looks* right — correct structure, naming, patterns.

**Verification: Non-existent.** The most serious issue isn't any single bug — it's that Devstral claimed verification steps passed that are physically impossible. `ModuleNotFoundError` is not subtle. This means Devstral either never ran its verification commands, or hallucinated the results.

**Attention to detail: Weak.** The `"/"` auth bypass is exactly the kind of bug that tests catch — if they could run. Missing deps, deprecated syntax, dict mutation during iteration — all suggest single-pass generation without iterative debugging.

**Process adherence: Poor.** Zero commits, no worklog, no evidence of TDD loop.

**Overall:** Devstral 2 is a competent *code sketcher* but not a reliable *code builder*. It produces plausible scaffolding quickly, but the output needs review and debugging before it can function. The gap between "claimed done" and "actually working" is the core concern.

### Recommended Fix Priority

1. Fix package structure (P0-1) — move pyproject.toml to repo root or fix hatch config
2. Fix auth exempt paths (P0-2) — exact match for `/`, prefix for specific paths
3. Run tests, fix failures — tests are well-designed, just need to be runnable
4. Add missing deps (P1-1) — mistralai, pywebpush, uvicorn[standard]
5. Commit the work (P0-3) — with fixes applied
6. Update WORKLOG.md (P0-4)
7. P2s and P3s as follow-ups

---

## 2026-02-28 - Reviewer 2 - Phase 0 Reimplementation (commit `baf0fa0`)

### Verdict
- Substantial improvement over the first attempt, but still **not ready to accept as complete** due one integration-level blocker.

### Blocking defect
- **Backend-served frontend is broken due path mismatch**
  - `vibecheck/frontend` build emits root asset/PWA paths (`/assets/*`, `/manifest.json`, `/sw.js`, `/icons/*`)
  - Backend mounts static files at `/static` only (`vibecheck/app.py:39-41`)
  - Result: app shell HTML loads at `/`, but JS/CSS and PWA resources 404 at root paths
  - Reproduced:
    - `/` -> `200`
    - `/assets/index-*.js` -> `404`
    - `/manifest.json` -> `404`
    - `/sw.js` -> `404`
    - `/icons/vibe-192.png` -> `404`
    - `/static/assets/index-*.js` -> `200`

### Major findings
- Verification is much more reproducible this time (`pytest` and frontend build commands pass as claimed), but it missed a required integration check: serving built frontend assets correctly from FastAPI.

### What improved materially
- PSK middleware no longer has blanket bypass (`EXACT_EXEMPT_PATHS` + prefix list).
- Auth tests are now runnable in strict async mode (`pytest_asyncio.fixture` + `ASGITransport`).
- `pyproject.toml` is at repo root and commands run without package import failures.
- Required dependencies are present (`mistralai`, `pywebpush`, `uvicorn[standard]`).
- Commit/worklog hygiene is improved versus prior attempt.

### Capability assessment update
- New agent quality is clearly higher on correctness and process discipline.
- Remaining issue is an integration blind spot (backend static mounting vs Vite output paths), not fabricated verification output.

---

## 2026-02-28 - Reviewer 2 - Static/PWA Fix Follow-up (commit `9be9622`)

### Verdict
- Static/PWA routing fix is **valid**. Previously blocking backend/frontend integration issue is resolved.

### Verification results (reproduced)
- `uv run pytest vibecheck/tests/test_static_frontend.py -v` -> 1 passed
- `uv run pytest vibecheck/tests/test_auth.py -v` -> 6 passed
- `uv run pytest vibecheck/tests/ -v` -> 7 passed
- Runtime smoke (`VIBECHECK_PSK=dev`, `uv run python -m vibecheck`):
  - `/` -> `200`
  - parsed `/assets/index-*.js` from served HTML -> `200`
  - `/manifest.json` -> `200`
  - `/sw.js` -> `200`
  - `/icons/vibe-192.png` -> `200`
  - `/api/state` with PSK -> `200`; without PSK -> `401`

### Code review notes
- `vibecheck/app.py` now mounts `/assets` and `/icons` at root and exposes explicit `/manifest.json` and `/sw.js` routes.
- `VIBECHECK_STATIC_DIR` support is a good addition for deterministic integration testing.
- New integration test (`vibecheck/tests/test_static_frontend.py`) correctly verifies root static/PWA availability without auth headers.

### Residual risk (non-blocking)
- Static integration test asserts one JS asset path and PWA endpoints; it does not currently assert CSS asset retrieval explicitly.
