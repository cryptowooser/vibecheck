#!/usr/bin/env python3
"""
Test Devstral 2 — Mistral's frontier code agents model.

Model: devstral-latest (Devstral 2)
  - 256k context, open-weight
  - Optimized for SWE tasks: codebase exploration, multi-file editing, tool use

Docs:
  https://docs.mistral.ai/getting-started/models/
  https://docs.mistral.ai/models/devstral-2-25-12
  https://docs.mistral.ai/capabilities/coding/

Pricing: $0.40/M input, $2.00/M output

Usage:
  export MISTRAL_API_KEY=your_key
  uv run python scripts/test_devstral2.py
"""

import os
import json
from mistralai import Mistral

MODEL = "devstral-latest"


def test_code_generation():
    """Test basic code generation."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"=== Devstral 2 ({MODEL}) — Code Generation ===\n")

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Write a Python function that takes a list of audio file paths "
                    "and returns their durations in seconds using the wave module. "
                    "Include type hints and a docstring."
                ),
            }
        ],
        temperature=0.2,
    )

    print(response.choices[0].message.content)
    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


def test_tool_use():
    """Test function calling / tool use (key for agentic workflows)."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    print(f"\n=== Devstral 2 ({MODEL}) — Tool Use ===\n")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file at the given path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The file path to read.",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Search for a pattern in the codebase.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory to search in.",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
    ]

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "I need to find all Python files that import asyncio in the src/ "
                    "directory, then read the main entry point file at src/main.py."
                ),
            }
        ],
        tools=tools,
        tool_choice="auto",
        temperature=0.1,
    )

    msg = response.choices[0].message
    if msg.tool_calls:
        print("Tool calls requested:")
        for tc in msg.tool_calls:
            print(f"  {tc.function.name}({tc.function.arguments})")
    else:
        print(msg.content)

    print(f"\n--- Usage: {response.usage.prompt_tokens} in / "
          f"{response.usage.completion_tokens} out ---")


if __name__ == "__main__":
    test_code_generation()
    test_tool_use()
