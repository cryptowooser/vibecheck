# Frontend Prototype: Voxtral STT -> ElevenLabs TTS

Minimal mobile-first voice loop prototype:

1. Record audio in browser
2. Send audio to `/api/stt` (Voxtral via backend proxy)
3. Show transcript
4. Send transcript to `/api/tts` (ElevenLabs via backend proxy)
5. Play synthesized audio in browser

## Environment

Required on the backend process:

- `MISTRAL_API_KEY`
- `ELEVENLABS_API_KEY`

If your shell does not already include these, load your shell profile first:

```bash
source ~/.bashrc
```

Optional:

- `ELEVENLABS_DEFAULT_VOICE_ID` (defaults to `JBFqnCBsd6RMkjVDRZzb`)
- `STT_MAX_UPLOAD_BYTES` (defaults to `10485760`)
- `STT_MIN_AUDIO_BYTES` (defaults to `2048`)

## Run backend

```bash
cd frontend-prototype/server
uv run uvicorn server.app:app --reload --port 8780
```

## Run frontend

```bash
cd frontend-prototype/frontend
npm install
npm run dev
```

The frontend dev server proxies `/api/*` to `http://localhost:8780`.

## Tests

```bash
cd frontend-prototype/server && uv run pytest tests -v
cd frontend-prototype/frontend && npm run build
cd frontend-prototype/frontend && npm run test
cd frontend-prototype/frontend && npm run test:e2e
cd frontend-prototype/frontend && npm run test:secrets
```

## Manual Mobile QA

Run physical-device checks for Milestone 5 using:

- `frontend-prototype/MOBILE-QA-CHECKLIST.md`

## Recommended Voice for Japanese

Otani