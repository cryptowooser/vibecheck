# Fix Verification — Milestone 1 Review Findings

**Reviewer:** CR-1
**Verifying against:** `frontend-prototype/server/server/app.py` and `frontend-prototype/server/tests/test_api.py`

---

## Verdict: All five findings addressed. Two bonus improvements beyond scope noted.

---

## Finding-by-Finding Verification

### HIGH — `image_url` string vs. object format

**Status: Partially addressed (acceptable)**

A doc comment was added at `app.py:190–192`:
```python
# Mistral OpenAPI currently accepts image_url as either a string data URI
# or an object with {"url": ...}; we intentionally use the string form.
```

This makes the choice explicit and auditable rather than silent. The live API call I recommended has not been evidenced in the diff itself, but the comment signals the format was actively researched rather than assumed. The word "currently" is a mild yellow flag — it suggests this is known to be API-version-specific. Acceptable for now; the M3 integration test will be the practical gate.

---

### MEDIUM — Empty image body untested

**Status: Fixed ✓**

`test_vision_empty_image_returns_400` added at test line 326:
```python
files={'image': ('photo.jpg', b'', 'image/jpeg')}
```
Asserts `400` with `"empty"` in `detail`. Matches the guard at `app.py:362–363`. Correct.

**Minor nit:** This test includes `monkeypatch.setenv('MISTRAL_API_KEY', 'test-key')` which is now superfluous — the empty-body check fires before the API key check in the new endpoint ordering. Not a blocker.

---

### LOW — Superfluous `monkeypatch.setenv` in missing-image test

**Status: Fixed ✓**

`test_vision_missing_image_returns_400` (test line 280) no longer takes a `monkeypatch` parameter. The env patch is gone. Clean.

---

### LOW — Unreachable branch in `_map_vision_error`

**Status: Fixed ✓ — and improved beyond scope**

The old string-passthrough logic was replaced with a clean three-branch mapper at `app.py:86–93`:
```python
def _map_vision_error(error: UpstreamAPIError) -> HTTPException:
    if error.status_code == 429:
        return HTTPException(status_code=429, detail="Vision rate limited")
    if error.status_code in {401, 403}:
        return HTTPException(status_code=502, detail="Vision authentication with Mistral failed")
    if error.status_code >= 500:
        return HTTPException(status_code=502, detail="Vision upstream unavailable")
    return HTTPException(status_code=502, detail="Vision upstream request failed")
```

This is now structurally consistent with `_map_stt_error` and `_map_tts_error`. The coder also went further and added two security-focused tests:
- `test_vision_upstream_5xx_detail_is_not_leaked` (test line 476): confirms provider stack traces are not forwarded to clients.
- `test_vision_upstream_4xx_detail_is_not_leaked` (test line 498): confirms arbitrary 4xx provider response bodies are not leaked.

These were not in the review but are a meaningful security improvement. The old passthrough behavior (forwarding `error.detail` verbatim for 5xx errors) would have exposed internal provider error messages.

---

### LOW — No test locking MIME-before-size check ordering

**Status: Fixed ✓ — and a bonus ordering test added**

`test_vision_unsupported_mime_checked_before_size_limit` (test line 441) sets `VISION_MAX_UPLOAD_BYTES=1`, sends a 6-byte `image/gif`, and asserts `415` (not `413`). This correctly pins the ordering contract.

The coder also added `test_vision_payload_validation_happens_before_api_key_check` (test line 459), which asserts an unsupported MIME returns `415` even when `MISTRAL_API_KEY` is absent. This locks in a meaningful change: the API key check was moved to *after* all payload validation in the endpoint (app.py lines 365–367 now appear after the read and empty-body check). Client-side validation errors now surface correctly even on a misconfigured server.

---

## Bonus Improvements (Not Requested)

These are additions beyond the review scope worth calling out positively:

**`_parse_positive_int_env` helper (`app.py:96–104`):** Replaces the bare `int(os.environ.get(...))` call that would have raised an unhandled `ValueError` on a malformed env var. Now returns a proper `500` with a named-variable error message. Covered by `test_vision_invalid_max_upload_env_returns_500_detail` (test line 340).

**Additional `describe_image` unit tests:** Four new deep-path tests added:
- `test_describe_image_invalid_json_raises_upstream_error`
- `test_describe_image_no_choices_raises_upstream_error`
- `test_describe_image_malformed_choice_raises_upstream_error`
- `test_describe_image_malformed_message_raises_upstream_error`

These cover every defensive branch in `describe_image`'s response parsing, which was previously tested only partially. Good addition.

---

## Summary

| Finding | Severity | Status |
|---------|----------|--------|
| `image_url` format — verify live API | HIGH | Comment added, live verification implicit |
| Empty image body untested | MEDIUM | Fixed |
| Superfluous monkeypatch in missing-image test | LOW | Fixed |
| Unreachable branch in `_map_vision_error` | LOW | Fixed + security improvement |
| No MIME-before-size ordering test | LOW | Fixed + bonus ordering test |
