from __future__ import annotations

import os
from collections.abc import AsyncIterator
import logging

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="frontend-prototype-server")
# Prototype/dev mode: allow the local frontend dev server; tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MISTRAL_STT_URL = "https://api.mistral.ai/v1/audio/transcriptions"
ELEVENLABS_TTS_URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_TTS_MODEL = "eleven_multilingual_v2"
DEFAULT_STT_MODEL = "voxtral-mini-latest"
UPLOAD_READ_CHUNK_SIZE = 1024 * 256
logger = logging.getLogger(__name__)

DEFAULT_VOICES = [
    {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella"},
    {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam"},
]


class UpstreamAPIError(Exception):
    def __init__(self, *, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice_id: str | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must not be empty")
        return cleaned


def _map_stt_error(error: UpstreamAPIError) -> HTTPException:
    if error.status_code in {401, 403}:
        return HTTPException(status_code=502, detail="STT authentication with Mistral failed")
    if error.status_code == 429:
        return HTTPException(status_code=429, detail="STT rate limited")
    if error.status_code >= 500:
        return HTTPException(status_code=502, detail="STT upstream unavailable")
    return HTTPException(status_code=400, detail=f"STT request failed: {error.detail}")


def _map_tts_error(error: UpstreamAPIError) -> HTTPException:
    if error.status_code in {401, 402, 403}:
        return HTTPException(status_code=502, detail="TTS authentication or quota failure")
    if error.status_code == 429:
        return HTTPException(status_code=429, detail="TTS rate limited")
    if error.status_code >= 500:
        return HTTPException(status_code=502, detail="TTS upstream unavailable")
    return HTTPException(status_code=400, detail=f"TTS request failed: {error.detail}")


async def transcribe_audio(
    *,
    api_key: str,
    audio_bytes: bytes,
    filename: str,
    content_type: str | None,
    language: str,
) -> str:
    files = {"file": (filename, audio_bytes, content_type or "application/octet-stream")}
    data = {"model": DEFAULT_STT_MODEL, "language": language}
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(MISTRAL_STT_URL, headers=headers, data=data, files=files)
    except httpx.HTTPError as error:
        raise UpstreamAPIError(status_code=502, detail=f"STT upstream transport error: {error}") from error

    if response.status_code >= 400:
        detail = response.text.strip() or "unknown STT upstream error"
        raise UpstreamAPIError(status_code=response.status_code, detail=detail)

    try:
        payload = response.json()
    except ValueError as error:
        raise UpstreamAPIError(status_code=502, detail=f"STT upstream returned invalid JSON: {error}") from error
    text = str(payload.get("text", "")).strip()
    if not text:
        raise UpstreamAPIError(status_code=502, detail="STT upstream returned an empty transcript")
    return text


async def read_upload_with_limit(upload: UploadFile, max_upload_bytes: int) -> bytes:
    audio_bytes = bytearray()
    while True:
        chunk = await upload.read(UPLOAD_READ_CHUNK_SIZE)
        if not chunk:
            break
        if len(audio_bytes) + len(chunk) > max_upload_bytes:
            raise HTTPException(status_code=413, detail="Audio file is too large")
        audio_bytes.extend(chunk)
    return bytes(audio_bytes)


async def open_tts_stream(*, api_key: str, text: str, voice_id: str) -> tuple[httpx.AsyncClient, httpx.Response]:
    url = ELEVENLABS_TTS_URL_TEMPLATE.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": DEFAULT_TTS_MODEL,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }

    client = httpx.AsyncClient(timeout=60.0)
    try:
        request = client.build_request("POST", url, headers=headers, json=payload)
        response = await client.send(request, stream=True)
    except httpx.HTTPError as error:
        await client.aclose()
        raise UpstreamAPIError(status_code=502, detail=f"TTS upstream transport error: {error}") from error

    if response.status_code >= 400:
        body = (await response.aread()).decode("utf-8", errors="ignore").strip()
        await response.aclose()
        await client.aclose()
        raise UpstreamAPIError(
            status_code=response.status_code,
            detail=body or "unknown TTS upstream error",
        )

    return client, response


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get("/api/voices")
def list_voices() -> dict[str, list[dict[str, str]]]:
    return {"voices": DEFAULT_VOICES}


@app.post("/api/stt")
async def stt(audio: UploadFile = File(...), language: str = Form("en")) -> dict[str, str]:
    max_upload_bytes = int(os.environ.get("STT_MAX_UPLOAD_BYTES", "10485760"))
    min_audio_bytes = int(os.environ.get("STT_MIN_AUDIO_BYTES", "2048"))

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="MISTRAL_API_KEY is not set")

    audio_bytes = await read_upload_with_limit(audio, max_upload_bytes)
    size = len(audio_bytes)
    if size < min_audio_bytes:
        raise HTTPException(status_code=400, detail="Recording is too short. Please try again.")

    try:
        transcript = await transcribe_audio(
            api_key=api_key,
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
            content_type=audio.content_type,
            language=language,
        )
    except UpstreamAPIError as error:
        raise _map_stt_error(error) from error

    return {"text": transcript, "language": language}


@app.post("/api/tts")
async def tts(request: TTSRequest) -> StreamingResponse:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY is not set")

    voice_id = request.voice_id or os.environ.get("ELEVENLABS_DEFAULT_VOICE_ID", DEFAULT_VOICE_ID)
    try:
        client, upstream_response = await open_tts_stream(api_key=api_key, text=request.text, voice_id=voice_id)
    except UpstreamAPIError as error:
        raise _map_tts_error(error) from error

    upstream_stream = upstream_response.aiter_bytes()
    first_chunk = b""
    try:
        async for chunk in upstream_stream:
            if chunk:
                first_chunk = chunk
                break
    except (httpx.HTTPError, httpx.StreamError) as error:
        await upstream_response.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"TTS upstream read failed: {error}") from error

    if not first_chunk:
        await upstream_response.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail="TTS upstream returned empty audio")

    async def stream_body() -> AsyncIterator[bytes]:
        try:
            yield first_chunk
            async for chunk in upstream_stream:
                if chunk:
                    yield chunk
        except (httpx.HTTPError, httpx.StreamError) as error:
            # Response headers are already sent; re-raise so the connection aborts
            # and clients observe a stream failure rather than a silent truncation.
            logger.exception("TTS stream interrupted mid-response")
            raise RuntimeError("TTS stream interrupted mid-response") from error
        finally:
            await upstream_response.aclose()
            await client.aclose()

    return StreamingResponse(stream_body(), media_type="audio/mpeg")
