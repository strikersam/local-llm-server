#!/usr/bin/env python3
"""Live probe — makes a tiny real API call to every configured provider.

Usage (in Render Shell or locally with keys set):
    python scripts/probe_live_providers.py

Each provider gets a 15-second timeout. Results show ✓ / ✗ with error detail.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provider_router import ProviderRouter

PROBE_PAYLOAD = {
    "model": "",          # filled in per provider
    "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
    "max_tokens": 10,
    "temperature": 0,
}
TIMEOUT = 15.0


async def probe_one(router: ProviderRouter, provider) -> tuple[bool, str]:
    payload = {**PROBE_PAYLOAD, "model": provider.default_model or ""}
    t0 = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            router._try_one_provider(
                provider, payload,
                original_model=payload["model"],
                model_fallbacks=[],
                is_primary=True,
                max_retries=0,
                attempts=[],
                provider_timeout_sec=TIMEOUT,
            ),
            timeout=TIMEOUT + 2,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        if result is not None:
            try:
                body = result.response.json()
                text = (
                    body.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    or ""
                ).strip()[:60]
            except Exception:
                text = "(non-JSON response)"
            return True, f"{elapsed}ms  reply: {text!r}"
        return False, "no result returned"
    except asyncio.TimeoutError:
        return False, f"timed out after {TIMEOUT}s"
    except Exception as exc:
        return False, str(exc)[:120]


async def main() -> None:
    router = ProviderRouter.from_env()

    if not router.providers:
        print("No providers discovered — no API keys found in environment.")
        return

    print(f"\nProbing {len(router.providers)} provider(s)...\n")
    print(f"{'Provider':<26} {'Model':<42} {'Result'}")
    print("-" * 100)

    passed = failed = 0
    for provider in router.providers:
        model = provider.default_model or "(none)"
        ok, detail = await probe_one(router, provider)
        icon = "✓" if ok else "✗"
        status = f"{icon}  {detail}"
        print(f"{provider.provider_id:<26} {model:<42} {status}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("-" * 100)
    print(f"\n{passed} passed  |  {failed} failed  |  {len(router.providers)} total\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
