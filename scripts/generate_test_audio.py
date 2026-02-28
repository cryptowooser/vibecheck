#!/usr/bin/env python3
"""
Generate test audio files for Voxtral API testing.

Creates:
  - test_audio.mp3  (for batch transcription)
  - test_audio.wav  (PCM 16-bit mono 16kHz, for realtime streaming)

Requires: uv pip install gtts pydub
Also requires ffmpeg: sudo pacman -S ffmpeg (Arch/CachyOS)

Docs:
  https://docs.mistral.ai/capabilities/audio_transcription/offline_transcription
  https://docs.mistral.ai/capabilities/audio_transcription/realtime_transcription
"""

import os
import sys
import struct
import wave
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MP3_PATH = os.path.join(SCRIPT_DIR, "test_audio.mp3")
WAV_PATH = os.path.join(SCRIPT_DIR, "test_audio.wav")

TEST_TEXT_EN = (
    "Hello, this is a test of the Voxtral transcription API. "
    "We are building vibecheck, a mobile bridge for Mistral Vibe. "
    "This audio was generated for preflight testing at the Tokyo hackathon."
)

TEST_TEXT_JA = (
    "こんにちは、これはVoxtral文字起こしAPIのテストです。"
    "東京ハッカソンのためのプリフライトテストです。"
)


def generate_with_gtts(text: str, mp3_path: str, wav_path: str, lang: str = "en"):
    """Generate MP3 with gTTS, then convert to PCM WAV for realtime testing."""
    from gtts import gTTS

    print(f"Generating MP3 with gTTS ({lang})...")
    tts = gTTS(text=text, lang=lang)
    tts.save(mp3_path)
    print(f"  Saved: {mp3_path}")

    print("Converting to PCM WAV (16-bit mono 16kHz)...")
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        audio.export(wav_path, format="wav")
        print(f"  Saved: {wav_path}")
    except Exception as e:
        print(f"  pydub conversion failed ({e}), trying ffmpeg directly...")
        import subprocess

        subprocess.run(
            [
                "ffmpeg", "-y", "-i", mp3_path,
                "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
                wav_path,
            ],
            check=True,
            capture_output=True,
        )
        print(f"  Saved: {wav_path}")


def generate_sine_wave_fallback(wav_path: str):
    """Fallback: generate a simple sine wave WAV (won't transcribe as speech)."""
    print("Generating sine wave fallback WAV (for connectivity testing only)...")
    sample_rate = 16000
    duration_s = 3
    freq = 440  # A4
    n_samples = sample_rate * duration_s

    with wave.open(wav_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            sample = int(16000 * math.sin(2 * math.pi * freq * i / sample_rate))
            wf.writeframes(struct.pack("<h", sample))

    print(f"  Saved: {wav_path} (sine wave — not speech)")


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    text = TEST_TEXT_JA if lang == "ja" else TEST_TEXT_EN

    try:
        generate_with_gtts(text, MP3_PATH, WAV_PATH, lang=lang)
    except ImportError:
        print("gTTS not installed. uv pip install gtts pydub")
        print("Falling back to sine wave (connectivity test only)...")
        generate_sine_wave_fallback(WAV_PATH)

    print("\nDone! Use these files with:")
    print(f"  uv run python scripts/test_voxtral_transcribe.py {MP3_PATH}")
    print(f"  uv run python scripts/test_voxtral_realtime.py {WAV_PATH}")


if __name__ == "__main__":
    main()
