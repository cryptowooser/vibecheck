#!/usr/bin/env python3
"""
Test Voxtral Realtime — live streaming audio transcription.

Model: voxtral-mini-transcribe-realtime-2602
  - Ultra-low latency (configurable 80ms–2.4s, recommend 480ms)
  - Streaming architecture: transcribes audio as it arrives
  - 13 languages, open-weight (Apache 2.0) for self-hosting
  - Audio format: PCM 16-bit mono (pcm_s16le), 16kHz

Docs:
  https://docs.mistral.ai/capabilities/audio_transcription/realtime_transcription

Pricing: ~$0.006/min
Requires: uv pip install \"mistralai[realtime]\"

Usage:
  export MISTRAL_API_KEY=your_key

  # Stream from a WAV file (generate first with generate_test_audio.py):
  uv run python scripts/test_voxtral_realtime.py test_audio.wav

  # Stream from microphone (requires pyaudio):
  uv run python scripts/test_voxtral_realtime.py --mic
"""

import asyncio
import os
import sys
import wave
from typing import AsyncIterator

from mistralai import Mistral
from mistralai.extra.realtime import UnknownRealtimeEvent
from mistralai.models import (
    AudioFormat,
    RealtimeTranscriptionError,
    RealtimeTranscriptionSessionCreated,
    TranscriptionStreamDone,
    TranscriptionStreamTextDelta,
)

MODEL = "voxtral-mini-transcribe-realtime-2602"
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 480  # recommended sweet spot for latency vs accuracy


async def audio_from_file(
    filepath: str,
    chunk_duration_ms: int = CHUNK_DURATION_MS,
    sample_rate: int = SAMPLE_RATE,
) -> AsyncIterator[bytes]:
    """Stream PCM audio chunks from a WAV file, simulating real-time input."""
    chunk_samples = int(sample_rate * chunk_duration_ms / 1000)

    with wave.open(filepath, "rb") as wf:
        assert wf.getnchannels() == 1, f"Expected mono, got {wf.getnchannels()} channels"
        assert wf.getsampwidth() == 2, f"Expected 16-bit, got {wf.getsampwidth() * 8}-bit"
        assert wf.getframerate() == sample_rate, (
            f"Expected {sample_rate}Hz, got {wf.getframerate()}Hz"
        )

        while True:
            data = wf.readframes(chunk_samples)
            if not data:
                break
            yield data
            # Simulate real-time pacing
            await asyncio.sleep(chunk_duration_ms / 1000)


async def audio_from_microphone(
    sample_rate: int = SAMPLE_RATE,
    chunk_duration_ms: int = CHUNK_DURATION_MS,
) -> AsyncIterator[bytes]:
    """Stream PCM audio chunks from the microphone using PyAudio."""
    import pyaudio

    p = pyaudio.PyAudio()
    chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_samples,
    )
    loop = asyncio.get_running_loop()

    print("🎤 Microphone active — speak now (Ctrl+C to stop)\n")

    try:
        while True:
            data = await loop.run_in_executor(
                None, stream.read, chunk_samples, False
            )
            yield data
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


async def transcribe_stream(audio_stream: AsyncIterator[bytes]):
    """Run realtime transcription on an audio stream."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    audio_format = AudioFormat(encoding="pcm_s16le", sample_rate=SAMPLE_RATE)

    print(f"=== Voxtral Realtime ({MODEL}) ===")
    print(f"    Chunk: {CHUNK_DURATION_MS}ms | Sample rate: {SAMPLE_RATE}Hz\n")

    try:
        async for event in client.audio.realtime.transcribe_stream(
            audio_stream=audio_stream,
            model=MODEL,
            audio_format=audio_format,
            # target_streaming_delay_ms=480,  # optional: tune latency vs accuracy
        ):
            if isinstance(event, RealtimeTranscriptionSessionCreated):
                print("✅ Session created — streaming...\n")
            elif isinstance(event, TranscriptionStreamTextDelta):
                print(event.text, end="", flush=True)
            elif isinstance(event, TranscriptionStreamDone):
                print("\n\n✅ Transcription complete.")
            elif isinstance(event, RealtimeTranscriptionError):
                print(f"\n❌ Error: {event}")
            elif isinstance(event, UnknownRealtimeEvent):
                print(f"\n⚠️  Unknown event: {event}")
    except KeyboardInterrupt:
        print("\n\nStopped.")


async def main():
    if "--mic" in sys.argv:
        audio_stream = audio_from_microphone()
    else:
        filepath = None
        for arg in sys.argv[1:]:
            if not arg.startswith("--"):
                filepath = arg
                break

        if filepath is None:
            default_path = os.path.join(os.path.dirname(__file__), "test_audio.wav")
            if os.path.exists(default_path):
                filepath = default_path

        if not filepath or not os.path.exists(filepath):
            print("Usage:")
            print("  uv run python scripts/test_voxtral_realtime.py <audio.wav>   # from file")
            print("  uv run python scripts/test_voxtral_realtime.py --mic         # from microphone")
            print()
            print("Generate test audio first: uv run python scripts/generate_test_audio.py")
            sys.exit(1)

        print(f"Streaming from file: {filepath}\n")
        audio_stream = audio_from_file(filepath)

    await transcribe_stream(audio_stream)


if __name__ == "__main__":
    asyncio.run(main())
