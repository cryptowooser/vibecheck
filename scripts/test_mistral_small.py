#!/usr/bin/env python3
"""
Test Mistral Small — fast, efficient model for EN↔JA translation.

Model: mistral-small-latest
  - 128k context
  - Good balance of speed, cost, and quality for translation tasks
  - Our use: per-message EN→JA and JA→EN translation in vibecheck

Docs:
  https://docs.mistral.ai/getting-started/models/
  https://docs.mistral.ai/capabilities/chat_completions/

Usage:
  export MISTRAL_API_KEY=your_key
  uv run python scripts/test_mistral_small.py
"""

import os
import time
from mistralai import Mistral

MODEL = "mistral-small-latest"


def test_en_to_ja():
    """Test English → Japanese translation of agent output."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"=== Mistral Small ({MODEL}) — EN → JA ===\n")

    # Typical agent output with code references that should stay untranslated
    agent_output = (
        "I've created the authentication module in `src/auth.py` with three endpoints:\n\n"
        "1. `POST /api/login` — validates credentials and returns a JWT token\n"
        "2. `POST /api/logout` — invalidates the current session\n"
        "3. `GET /api/me` — returns the authenticated user's profile\n\n"
        "I'll run `pytest tests/test_auth.py` next to verify everything works."
    )

    start = time.time()
    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a translator for a coding assistant app. "
                    "Translate the following English text to Japanese. "
                    "IMPORTANT: Preserve all code blocks, file paths, function names, "
                    "API endpoints, command names, and markdown formatting exactly as-is. "
                    "Only translate the natural language portions."
                ),
            },
            {
                "role": "user",
                "content": agent_output,
            },
        ],
        temperature=0.1,
    )
    elapsed = time.time() - start

    print(f"Original:\n{agent_output}\n")
    print(f"Translation:\n{response.choices[0].message.content}\n")
    print(f"--- {elapsed:.2f}s | {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_ja_to_en():
    """Test Japanese → English translation of user voice input."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Mistral Small ({MODEL}) — JA → EN ===\n")

    # Simulated Japanese voice input (what Voxtral would transcribe)
    ja_input = "テストを実行して、失敗したらエラーログを見せて"

    start = time.time()
    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a translator for a coding assistant app. "
                    "Translate the following Japanese text to English. "
                    "This is a user instruction to an AI coding agent. "
                    "Keep it as a natural command/instruction in English."
                ),
            },
            {
                "role": "user",
                "content": ja_input,
            },
        ],
        temperature=0.1,
    )
    elapsed = time.time() - start

    print(f"Original: {ja_input}")
    print(f"Translation: {response.choices[0].message.content}\n")
    print(f"--- {elapsed:.2f}s | {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_code_preserving_translation():
    """Test that code blocks survive translation intact."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Mistral Small ({MODEL}) — Code-Preserving Translation ===\n")

    mixed_content = (
        "The function `calculate_total(items: list[dict]) -> float` in "
        "`src/billing/calculator.py` has a bug on line 42. The issue is that "
        "`item['price'] * item['quantity']` doesn't account for the discount field. "
        "I've fixed it with:\n\n"
        "```python\n"
        "total = sum(\n"
        "    item['price'] * item['quantity'] * (1 - item.get('discount', 0))\n"
        "    for item in items\n"
        ")\n"
        "```\n\n"
        "All 12 tests in `tests/test_billing.py` now pass."
    )

    start = time.time()
    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a translator for a coding assistant app. "
                    "Translate the following English text to Japanese. "
                    "CRITICAL RULES:\n"
                    "- Keep ALL code blocks (```...```) exactly as-is, do not translate code\n"
                    "- Keep inline code (`...`) exactly as-is\n"
                    "- Keep file paths, function names, variable names untranslated\n"
                    "- Keep markdown formatting intact\n"
                    "- Only translate natural language sentences"
                ),
            },
            {
                "role": "user",
                "content": mixed_content,
            },
        ],
        temperature=0.1,
    )
    elapsed = time.time() - start

    translated = response.choices[0].message.content

    print(f"Original:\n{mixed_content}\n")
    print(f"Translation:\n{translated}\n")

    # Quick sanity check: code block should survive
    checks = [
        ("```python" in translated, "code block opening preserved"),
        ("item['price']" in translated, "code variables preserved"),
        ("test_billing.py" in translated, "file path preserved"),
        ("calculate_total" in translated, "function name preserved"),
    ]
    print("Sanity checks:")
    for passed, desc in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {desc}")

    print(f"\n--- {elapsed:.2f}s | {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_streaming_translation():
    """Test streaming translation for responsive UX."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Mistral Small ({MODEL}) — Streaming Translation ===\n")

    start = time.time()
    stream = client.chat.stream(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Translate to Japanese. Preserve code and file paths as-is."
                ),
            },
            {
                "role": "user",
                "content": (
                    "I've added error handling to the WebSocket connection. "
                    "If the server disconnects, the client will automatically "
                    "retry with exponential backoff (1s, 2s, 4s, max 30s)."
                ),
            },
        ],
        temperature=0.1,
    )

    first_token_time = None
    for chunk in stream:
        content = chunk.data.choices[0].delta.content
        if content:
            if first_token_time is None:
                first_token_time = time.time()
            print(content, end="", flush=True)
    elapsed = time.time() - start
    ttft = (first_token_time - start) if first_token_time else 0

    print(f"\n\n--- {elapsed:.2f}s total | {ttft:.2f}s TTFT ---")


if __name__ == "__main__":
    test_en_to_ja()
    test_ja_to_en()
    test_code_preserving_translation()
    test_streaming_translation()
