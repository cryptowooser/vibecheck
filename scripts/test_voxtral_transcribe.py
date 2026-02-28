#!/usr/bin/env python3
"""
Test Voxtral Mini Transcribe V2 — batch/offline audio transcription.

Model: voxtral-mini-latest (points to voxtral-mini-2602 for transcription)
  - Batch transcription with diarization, context biasing, word-level timestamps
  - 13 languages, up to 3 hours per request
  - Formats: mp3, wav, m4a, flac, ogg, webm

Docs:
  https://docs.mistral.ai/capabilities/audio_transcription/offline_transcription
  https://docs.mistral.ai/getting-started/models/

Pricing: ~$0.003/min

Usage:
  export MISTRAL_API_KEY=your_key
  uv run python scripts/test_voxtral_transcribe.py [path_to_audio.mp3]

Generate test audio first:
  uv run python scripts/generate_test_audio.py
"""

import os
import sys
from mistralai import Mistral

MODEL = "voxtral-mini-latest"


def test_transcribe_from_file(filepath: str):
    """Transcribe a local audio file."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"=== Voxtral Mini Transcribe ({MODEL}) — File Upload ===\n")
    print(f"File: {filepath}\n")

    with open(filepath, "rb") as f:
        response = client.audio.transcriptions.complete(
            model=MODEL,
            file={"content": f, "file_name": os.path.basename(filepath)},
            # language="en",  # optional, boosts accuracy if known
        )

    print("Transcription:")
    print(response.text)
    print()


def test_transcribe_from_url():
    """Transcribe audio from a URL (Mistral's sample)."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    url = "https://docs.mistral.ai/audio/obama.mp3"
    print(f"=== Voxtral Mini Transcribe ({MODEL}) — URL ===\n")
    print(f"URL: {url}\n")

    response = client.audio.transcriptions.complete(
        model=MODEL,
        file_url=url,
    )

    print("Transcription:")
    print(response.text)
    print()


def test_transcribe_with_timestamps():
    """Transcribe with segment-level timestamps."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    url = "https://docs.mistral.ai/audio/obama.mp3"
    print(f"=== Voxtral Mini Transcribe ({MODEL}) — Timestamps ===\n")

    response = client.audio.transcriptions.complete(
        model=MODEL,
        file_url=url,
        timestamp_granularities=["segment"],
        # NOTE: timestamp_granularities is not compatible with language param
    )

    print("Transcription:")
    print(response.text)
    if hasattr(response, "segments") and response.segments:
        print("\nSegments:")
        for seg in response.segments:
            print(f"  [{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}")
    print()


def test_transcribe_with_context_bias():
    """Transcribe with context biasing for domain-specific terms."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    url = "https://docs.mistral.ai/audio/obama.mp3"
    print(f"=== Voxtral Mini Transcribe ({MODEL}) — Context Bias ===\n")

    response = client.audio.transcriptions.complete(
        model=MODEL,
        file_url=url,
        context_bias=(
            "vibecheck,Voxtral,Mistral,hackathon,Tokyo,"
            "transcription,diarization,WebSocket"
        ),
    )

    print("Transcription (with context bias):")
    print(response.text)
    print()


if __name__ == "__main__":
    # Test with URL first (always works, no local file needed)
    test_transcribe_from_url()
    test_transcribe_with_timestamps()

    # Test with local file if provided
    filepath = sys.argv[1] if len(sys.argv) > 1 else None
    if filepath is None:
        default_path = os.path.join(os.path.dirname(__file__), "test_audio.mp3")
        if os.path.exists(default_path):
            filepath = default_path

    if filepath and os.path.exists(filepath):
        test_transcribe_from_file(filepath)
    else:
        print("Skipping local file test (no file provided).")
        print("Generate test audio: uv run python scripts/generate_test_audio.py")
        print("Then: uv run python scripts/test_voxtral_transcribe.py test_audio.mp3")
