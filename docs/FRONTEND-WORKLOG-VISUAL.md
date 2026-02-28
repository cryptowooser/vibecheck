# vibecheck — Frontend Worklog (Visual)

## 2026-02-28

### Milestone 1 - backend `/api/vision` implementation
- Added `POST /api/vision` in `frontend-prototype/server/server/app.py` using optional `image: UploadFile | None = File(None)` and explicit `400` for missing image.
- Added server-side MIME allowlist validation (`image/jpeg`, `image/png`, `image/webp`) before reading upload bytes.
- Added size-limit enforcement using `VISION_MAX_UPLOAD_BYTES` (default `10485760`) with explicit `413` on overflow.
- Added Mistral vision proxy helper (`describe_image`) targeting `POST /v1/chat/completions` with:
  - model: `mistral-large-latest`
  - fixed prompt: `Describe this image`
  - image data URI: `data:<mime>;base64,<bytes>`
  - timeout: `60s`
- Added normalization for structured `choices[0].message.content` arrays into plain output text.
- Added deterministic vision error mapping:
  - `429` passthrough for rate limit
  - `502` for auth/upstream/transport/empty-content failures
  - `500` when `MISTRAL_API_KEY` is missing

### Milestone 1 - backend test coverage
- Extended `frontend-prototype/server/tests/test_api.py` with `/api/vision` endpoint tests:
  - happy path contract
  - missing image (`400`)
  - unsupported MIME (`415`)
  - oversized payload (`413`)
  - missing `MISTRAL_API_KEY` (`500`)
  - upstream rate-limit mapping (`429`)
  - upstream auth/transport/empty-content mapping (`502`)
- Added helper-level tests for `describe_image`:
  - structured content-array normalization
  - empty content detection to upstream error
- Verification run:
  - `cd frontend-prototype/server && uv run pytest tests/test_api.py -q` -> `31 passed`
  - `cd frontend-prototype/server && uv run pytest tests/ -v` -> `31 passed`

### Visual prototype docs setup
- Added `docs/FRONTEND-PROTOTYPE-PLAN-VISUAL.md` for Android-first camera/gallery image description flow.
- Added `docs/FRONTEND-PROTOTYPE-IMPLEMENTATION-VISUAL.md` with milestone-based implementation and verification gates.
- Clarified visual implementation contract:
  - integrate into existing `App.svelte` and `server/server/app.py`
  - fixed model `mistral-large-latest`
  - fixed server-side prompt `Describe this image`
  - explicit `Describe` submit action
  - backend error/test coverage includes `500` missing-key case
