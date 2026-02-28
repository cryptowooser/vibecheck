# Milestone 4 Review: Hardening + Android QA

## Overall Assessment

Milestone 4 addressed all five issues raised in the M3 review. The stale-guard correctness hole is fixed, the stale-guard test was added, the network-failure frontend test was added, and the `ConnectError` backend test for `describe_image` was added. The e2e suite grew by four new vision tests and picker disablement is now verified at both the unit and e2e levels.

The milestone exit criteria are mostly satisfied, with two verifiable gaps and one soft gap described below.

---

## What's Done Well

**Stale-guard gap from M3 closed (`App.svelte`)**

The JSON-parse-failure branch (M3 Issue #2) now has a stale guard check before calling `setVisionError`:

```js
} catch {
  if (requestId !== visionSequenceCounter) {
    return
  }
  setVisionError('Vision response was invalid.', { allowRetry: true })
  return
}
```

All four `await` suspension points in `describeSelectedImage` now consistently check the requestId. Good.

**Stale guard test added (`App.test.js:1375`)**

`ignores stale invalid-json failure from an outdated describe request` correctly exercises the sequence: first describe in-flight → second image selected (counter advanced) → deferred JSON rejection arrives → UI state is not overwritten. This is the right structure.

**Network-failure frontend test added (`App.test.js:1421`)**

`shows retryable error when vision request cannot reach backend` mocks a thrown `TypeError` from `fetch` and verifies the error message, retry guidance, and Describe re-enablement. Closes M3 Issue #4.

**`ConnectError` backend test added (`test_api.py:888`)**

`test_describe_image_connect_error_raises_upstream_error` adds symmetric coverage matching the existing `ConnectError` test in `transcribe_audio`. Closes M3 Issue #6.

**E2e suite extended with four new vision tests**

The Playwright suite now covers: upload → describe lifecycle + in-flight button disablement; transient failure + retry; prior-valid image retention after invalid replacement; idle reset on cancel with no prior image. These tests run in Pixel 7 and iPhone 12 emulation, which partially addresses the Android QA exit criterion for the UI layer.

**In-flight picker disablement**

`launchTakePhotoPicker` and `launchUploadPhotoPicker` both guard against `visionState === VISION_STATE_DESCRIBING` at call time. The Describe button is `disabled` while describing via its `disabled` attribute binding. Unit test `disables picker buttons while visual describe is in progress` uses a deferred promise to assert the disabled state mid-flight and re-enablement after resolution. The corresponding e2e test in `mobile-smoke.spec.js` also asserts this at the browser level.

---

## Issues

**1. Stale guard success path is not tested (required by spec)**

The stale guard at lines 407–409 (after successful JSON parse, before rendering the description text) has no test. Every current stale-guard test terminates the in-flight request by either rejection or non-2xx response. The most likely production stale case — new image selected while a describe is in-flight and the old response arrives 200 with valid text — is not covered.

The fix requires one additional test that parallels the existing M3 stale test: select first image → click Describe (hold response with deferred) → select second image → resolve deferred with `{ text: 'stale text' }` → assert state is `image_selected` and stale text is not rendered. The guard code is correct; only the test is missing.

**2. E2e secret and proxy check does not cover vision**

The `mobile browser uses local proxy routes only and does not send provider auth headers` test monitors `request` events and checks for direct calls to `api.mistral.ai` / `api.elevenlabs.io`, and asserts no `Authorization` or `xi-api-key` headers on STT/TTS calls. Vision is not included. No vision fetch is triggered in that test, so a future regression that leaks the Mistral key in a vision request would not be caught by e2e.

The `check-no-secrets.mjs` static scan provides partial coverage via source and build artifact inspection, but does not substitute for a runtime check. Extending the existing e2e test to also perform a describe call and assert no direct provider traffic and no `Authorization` header on `/api/vision` calls would close this gap.

**3. Stale guard test covers only the JSON-parse-failure await point**

Related to Issue #1 but distinct: the stale test defers the `json()` call specifically. There are three other await points in `describeSelectedImage` with stale guards — the `fetch()` itself, the `getVisionFailureDetail()` call inside the `!response.ok` branch, and the final guard before rendering. None of these are tested in a stale scenario.

The `fetch()` guard (lines 376–381) is the least likely to need coverage since browsers don't usually suspend at the network call itself for timing purposes. The `!response.ok` + `getVisionFailureDetail` path (lines 387–393) is worth one test: hold the vision response at the JSON-parse step inside `getVisionFailureDetail`, select a new image, resolve, and assert no error overlay. Low priority but a gap.

**4. Android real-device QA not evidenced**

The M4 exit criterion requires "Confirm Android-first capture/upload behavior with real-device sanity pass." There is no WORKLOG entry, bug report, or artifact that records this having been done. The Playwright tests run in Pixel 7 and iPhone 12 browser emulation, which validates DOM/JS behavior but cannot confirm native camera intent dispatch or gallery picker behavior on Android. This is a soft gap — the automated coverage is as good as it can reasonably be without device access — but it should be explicitly noted as pending rather than implicitly satisfied.

**5. UX guidance inconsistency from M3 not addressed**

`setVisionError` uses `'Tap Describe to retry.'` for all `allowRetry: true` cases, including when a new image fails client-side validation while a prior valid image is retained. The more precise message would distinguish between "retry with prior image" and "retry after a network failure." This was flagged in the M3 review. It remains unaddressed. Still a minor UX issue, not a functional defect.

---

## Summary

| Area | Status |
|------|--------|
| Stale guard — correctness (all branches) | Pass |
| Stale guard — test (JSON parse failure path) | Pass |
| Stale guard — test (success path) | **Fail (no test)** |
| Stale guard — test (error body / `getVisionFailureDetail` path) | Minor gap |
| Network failure frontend test | Pass |
| ConnectError backend test | Pass |
| Picker button disablement during in-flight | Pass (unit + e2e) |
| E2e vision lifecycle tests | Pass |
| Secret/proxy e2e check — STT/TTS | Pass |
| Secret/proxy e2e check — vision | **Fail (not covered)** |
| Android real-device QA | Soft gap (emulation only, no device evidence) |
| UX guidance consistency (retained-image error) | Minor gap (carried from M3) |

The milestone is substantially complete. The stale guard is implemented correctly and the main behavioral coverage is in place. Before closing, add a test for the stale success path (Issue #1) and extend the e2e proxy test to include a vision call (Issue #2). These are the two verifiable gaps that directly map to M4 exit criteria.
