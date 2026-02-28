from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import httpx

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


def list_voices(api_key: str) -> None:
    response = httpx.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    voices = payload.get("voices", [])
    print(f"voices: {len(voices)}")
    for voice in voices[:10]:
        print(f"- {voice.get('name')} ({voice.get('voice_id')})")


def synthesize(api_key: str, text: str, voice_id: str, out_path: Path, model_id: str) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }

    start = time.perf_counter()
    first_byte_at: float | None = None
    total = 0

    with httpx.stream("POST", url, headers=headers, json=payload, timeout=60) as response:
        response.raise_for_status()
        with out_path.open("wb") as file_handle:
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                if first_byte_at is None:
                    first_byte_at = time.perf_counter()
                total += len(chunk)
                file_handle.write(chunk)

    end = time.perf_counter()
    first_byte_ms = ((first_byte_at or end) - start) * 1000
    total_ms = (end - start) * 1000

    print(f"wrote: {out_path}")
    print(f"bytes: {total}")
    print(f"latency_first_byte_ms: {first_byte_ms:.1f}")
    print(f"latency_total_ms: {total_ms:.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ElevenLabs streaming TTS prototype")
    parser.add_argument("text", nargs="?", default="Hello from vibecheck")
    parser.add_argument("--voice-id", default=DEFAULT_VOICE_ID)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--out", default="/tmp/elevenlabs-tts.mp3")
    parser.add_argument("--list-voices", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY is required")

    if args.list_voices:
        list_voices(api_key)
        return

    synthesize(api_key, args.text, args.voice_id, Path(args.out), args.model_id)


if __name__ == "__main__":
    main()
