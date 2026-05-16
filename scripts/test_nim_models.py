#!/usr/bin/env python3
"""Quick smoke-test for NVIDIA NIM model IDs.

Usage:
    NVIDIA_API_KEY=nvapi-... python scripts/test_nim_models.py

Tests each model with a single token response and reports pass/fail.
"""
from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error
import ssl

BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MODELS_TO_TEST = {
    "planner":           "qwen/qwen3-coder-480b-a35b-instruct",
    "executor/verifier": "nvidia/nemotron-3-super-120b-a12b",
    "judge":             "deepseek-ai/deepseek-v4-pro",
}


def test_model(api_key: str, role: str, model_id: str) -> bool:
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with just the word OK"}],
        "max_tokens": 5,
        "stream": False,
    }).encode()

    req = urllib.request.Request(BASE_URL, data=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            body = json.loads(resp.read())
            content = body["choices"][0]["message"]["content"]
            print(f"  ✓  [{role}] {model_id!r}  →  {content!r}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  ✗  [{role}] {model_id!r}  →  HTTP {e.code}: {body[:120]}")
        return False
    except Exception as e:
        print(f"  ✗  [{role}] {model_id!r}  →  {type(e).__name__}: {e}")
        return False


def main() -> None:
    api_key = (
        os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("NVidiaApiKey")
        or ""
    ).strip()
    if not api_key:
        print("ERROR: set NVIDIA_API_KEY in the environment before running.")
        sys.exit(1)

    print(f"Testing {len(MODELS_TO_TEST)} NIM models...\n")
    results = {}
    for role, model_id in MODELS_TO_TEST.items():
        results[model_id] = test_model(api_key, role, model_id)

    passed = sum(results.values())
    total = len(results)
    print(f"\n{passed}/{total} models responding.")
    if passed < total:
        print("\nFailed models — do NOT use these as defaults:")
        for m, ok in results.items():
            if not ok:
                print(f"  {m}")
        sys.exit(1)


if __name__ == "__main__":
    main()
