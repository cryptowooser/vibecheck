from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"

app = FastAPI(title="elevenlabs-tts-proxy-prototype")


class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    voice_id: str | None = None


async def stream_tts(api_key: str, text: str, voice_id: str) -> AsyncIterator[bytes]:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": DEFAULT_MODEL_ID,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise HTTPException(status_code=response.status_code, detail=body.decode("utf-8", errors="ignore"))
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk


@app.post("/api/tts")
async def tts(request: TTSRequest) -> StreamingResponse:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY is not set")

    voice_id = request.voice_id or DEFAULT_VOICE_ID
    return StreamingResponse(stream_tts(api_key, request.text, voice_id), media_type="audio/mpeg")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
