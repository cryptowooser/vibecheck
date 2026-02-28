#!/usr/bin/env python3
"""
Test Ministral 8B — small, fast model for notification intelligence.

Model: ministral-8b-latest
  - 128k context, open-weight
  - Optimized for low-latency, high-throughput edge/on-device use
  - Our use: notification copy, urgency classification, tool call summaries

Docs:
  https://docs.mistral.ai/getting-started/models/

Usage:
  export MISTRAL_API_KEY=your_key
  uv run python scripts/test_ministral8b.py
"""

import json
import os
from mistralai import Mistral

MODEL = "ministral-8b-latest"


def test_notification_copy():
    """Test generating short, friendly notification text from a raw tool call."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"=== Ministral 8B ({MODEL}) — Notification Copy ===\n")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short push notification messages for a mobile app "
                    "called vibecheck. The app lets users approve AI coding agent "
                    "actions from their phone. Keep messages under 80 characters, "
                    "calm and slightly playful. Never use ALL CAPS."
                ),
            },
            {
                "role": "user",
                "content": (
                    "The coding agent wants to run this command and needs approval:\n"
                    "Tool: bash\n"
                    "Command: npm test -- --coverage\n\n"
                    "Write a push notification title (max 40 chars) and body (max 80 chars)."
                ),
            },
        ],
        temperature=0.7,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_urgency_classification():
    """Test classifying tool call urgency for notification priority."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Ministral 8B ({MODEL}) — Urgency Classification ===\n")

    tool_calls = [
        {"tool": "bash", "args": "rm -rf node_modules && npm install"},
        {"tool": "read_file", "args": "src/config.json"},
        {"tool": "bash", "args": "git push origin main --force"},
        {"tool": "write_file", "args": "src/auth.py (47 lines)"},
        {"tool": "bash", "args": "python -m pytest tests/"},
    ]

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You classify AI coding agent tool calls by urgency for push "
                    "notifications. Respond in JSON array format.\n"
                    "Levels: critical (destructive/irreversible), high (writes/executes), "
                    "medium (tests/builds), low (reads/safe). "
                    "Include a 1-line summary for each (max 60 chars)."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Classify these tool calls:\n"
                    + "\n".join(
                        f"{i+1}. {tc['tool']}: {tc['args']}"
                        for i, tc in enumerate(tool_calls)
                    )
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_tool_summary():
    """Test generating a 1-line summary for the approval banner."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Ministral 8B ({MODEL}) — Tool Call Summary ===\n")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarize coding agent tool calls in one short sentence "
                    "(max 60 chars) for a mobile approval banner. "
                    "Be specific about what the tool does, not just its name. "
                    "Respond as a plain string, no quotes."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Tool: write_file\n"
                    "Path: src/api/routes/auth.py\n"
                    "Content: (63 lines — FastAPI router with login/logout/refresh endpoints)"
                ),
            },
        ],
        temperature=0.3,
    )

    print(f"Summary: {response.choices[0].message.content}")
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_idle_nudge():
    """Test generating escalating idle messages (for Intensity system)."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Ministral 8B ({MODEL}) — Idle Nudge Messages ===\n")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write escalating idle reminder messages for a coding agent "
                    "monitor app. The agent has been idle (waiting for user input). "
                    "Write 4 messages at increasing urgency, each under 80 chars. "
                    "Go from gentle to persistent. The last one should reference "
                    "Ralph Wiggum (the app's max intensity level is called 'Ralph'). "
                    "Respond as a JSON array of strings."
                ),
            },
            {
                "role": "user",
                "content": "The agent has been idle for 15 minutes waiting for approval on: bash: npm test",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


if __name__ == "__main__":
    test_notification_copy()
    test_urgency_classification()
    test_tool_summary()
    test_idle_nudge()
