#!/usr/bin/env python3
"""
Test Mistral Large 3 — state-of-the-art general-purpose multimodal model.

Model: mistral-large-latest (mistral-large-2512)
  - 256k context, open-weight
  - Multimodal (text + vision), function calling, structured output

Docs:
  https://docs.mistral.ai/getting-started/models/
  https://docs.mistral.ai/capabilities/chat_completions/
  https://docs.mistral.ai/capabilities/vision/

Usage:
  export MISTRAL_API_KEY=your_key
  uv run python scripts/test_mistral_large3.py
  uv run python scripts/test_mistral_large3.py image.png   # vision test with local image
"""

import base64
import os
import sys
from mistralai import Mistral

MODEL = "mistral-large-latest"


def test_chat():
    """Test basic chat completion."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"=== Mistral Large 3 ({MODEL}) — Chat ===\n")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant for a hackathon team in Tokyo.",
            },
            {
                "role": "user",
                "content": (
                    "We're building 'vibecheck', a mobile bridge for Mistral Vibe. "
                    "Give us a 3-sentence elevator pitch in both English and Japanese."
                ),
            },
        ],
        temperature=0.7,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_structured_output():
    """Test JSON structured output."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Mistral Large 3 ({MODEL}) — Structured Output ===\n")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "List 3 Mistral API models useful for a hackathon project. "
                    "For each, provide: name, best_for, and price_per_million_tokens. "
                    "Respond in JSON array format."
                ),
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_streaming():
    """Test streaming chat completion."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Mistral Large 3 ({MODEL}) — Streaming ===\n")

    stream = client.chat.stream(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": "Explain WebSocket push notifications in 2 sentences.",
            }
        ],
        temperature=0.3,
    )

    for chunk in stream:
        content = chunk.data.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
    print()


def test_vision_url():
    """Test vision with a public image URL."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Mistral Large 3 ({MODEL}) — Vision (URL) ===\n")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in detail. If there is any text, transcribe it.",
                    },
                    {
                        "type": "image_url",
                        "image_url": "https://docs.mistral.ai/img/eiffel-tower-paris.jpg",
                    },
                ],
            }
        ],
        temperature=0.3,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_vision_local(filepath: str):
    """Test vision/OCR with a local image file (base64 encoded)."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Mistral Large 3 ({MODEL}) — Vision/OCR (Local File) ===\n")
    print(f"File: {filepath}\n")

    with open(filepath, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(filepath)[1].lstrip(".").lower()
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}
    mime = mime_map.get(ext, "image/png")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this image. If it contains text or a document, "
                            "perform OCR and transcribe all visible text. "
                            "If it's a photo or diagram, describe it in detail."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:{mime};base64,{image_data}",
                    },
                ],
            }
        ],
        temperature=0.2,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


if __name__ == "__main__":
    test_chat()
    test_structured_output()
    test_streaming()
    test_vision_url()

    # Test local image if provided as CLI arg
    local_image = None
    for arg in sys.argv[1:]:
        if os.path.exists(arg):
            local_image = arg
            break

    if local_image:
        test_vision_local(local_image)
    else:
        print("\nTip: pass a local image to test OCR:")
        print("  python test_mistral_large3.py screenshot.png")
