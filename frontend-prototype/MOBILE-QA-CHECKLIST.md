# Mobile QA Checklist (Milestone 5)

Run this checklist on physical phones to satisfy Milestone 5 manual validation requirements.

## Preconditions

- Backend running: `cd frontend-prototype/server && uv run uvicorn server.app:app --host 0.0.0.0 --port 8780`
- Frontend running: `cd frontend-prototype/frontend && npm run dev -- --host 0.0.0.0 --port 5178`
- Phone can reach the frontend URL (same LAN, VPN, or deployed host).

## Device Matrix

- iOS Safari (real device)
- Android Chrome (real device)

## Test Cases (run on both devices)

1. Baseline rendering and controls
- Open app URL.
- Confirm `Record` button, `Voice` selector, transcript panel, and state pill render.

2. STT -> TTS happy path
- Tap `Record`, speak, tap `Stop`.
- Confirm transcript appears.
- Confirm playback completes and status returns to `Playback complete`.

3. STT failure + retry
- Induce STT failure (temporary backend stub/failure mode if needed).
- Confirm error panel appears with `Retry STT`.
- Tap `Retry STT` and confirm recovery to successful playback.

4. TTS failure + retry
- Induce TTS failure.
- Confirm error panel appears with `Retry TTS`.
- Tap `Retry TTS` and confirm recovery to successful playback.

5. In-flight control locking
- While transcription is in progress, verify non-essential controls are disabled.
- Confirm controls re-enable after completion/error.

6. Voice fallback
- Force `/api/voices` failure.
- Confirm fallback voices (`George`, `Bella`, `Adam`) populate the selector.

7. Secret/proxy behavior sanity check
- Confirm browser requests target app proxy routes (`/api/stt`, `/api/tts`, `/api/voices`).
- Confirm no provider keys are present in browser request headers.

## Results Log

Record execution date and outcome:

- Date:
- Tester:
- iOS Safari result: PASS / FAIL
- Android Chrome result: PASS / FAIL
- Notes / defects:
