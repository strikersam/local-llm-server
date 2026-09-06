"""Shared free-cloud-brain candidate list and failover for the auto-PR scripts.

``autonomous_agent.py`` and ``autonomous_fix.py`` each picked exactly one
provider (by which key was set, in Cerebras -> Groq -> Mistral -> NVIDIA NIM
order) and called it with a bare ``raise_for_status()``. On 2026-09-06 the
Cerebras account's paid tier lapsed: every call answered ``402 Payment
Required``, ``autonomous_agent.py`` had no fallback for that response, and the
hourly workflow crashed on every run instead of moving to Groq or NVIDIA —
exactly the gap CLAUDE.md rule 4 exists to close, and exactly the model
``implement_agent.py`` already follows via ``packages/ai/router.py``'s
provider chain.

This module is deliberately free of any top-level side effects (no env reads,
no network calls at import time) so it can be imported and unit tested in
isolation — unlike the two scripts above, which both fetch from the GitHub API
at import time.
"""
from __future__ import annotations

import os

import httpx

# Priority order mirrors CLAUDE.md's documented free-cloud chain for these
# auto-PR scripts: Cerebras -> Groq -> Mistral -> NVIDIA NIM.
_PROVIDERS: tuple[tuple[str, str, str, str], ...] = (
    ("cerebras", "https://api.cerebras.ai/v1/chat/completions", "CEREBRAS_API_KEY", "gpt-oss-120b"),
    ("groq", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    ("mistral", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-small-latest"),
    ("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_API_KEY",
     "nvidia/nemotron-3-super-120b-a12b"),
)


def brain_candidates() -> list[tuple[str, str, str, str]]:
    """(provider, url, api_key, model) for every provider with a key set.

    Order follows ``_PROVIDERS``. A provider with no key configured is
    omitted entirely — callers used to always get an NVIDIA entry even with
    an empty key string and had to remember to check truthiness themselves.
    """
    return [
        (provider, url, os.environ[env_var], model)
        for provider, url, env_var, model in _PROVIDERS
        if os.environ.get(env_var)
    ]


def call_brain_with_failover(candidates, messages, *, max_tokens=4096, temperature=0.3, timeout=120.0):
    """POST *messages* to each candidate in order; return the first success.

    Returns ``(provider, model, content)`` from the first candidate that
    answers with a 2xx status. A candidate that raises an HTTP error (rate
    limit, payment required, server error) or a transport error (timeout,
    connection failure) is logged and skipped rather than taking the whole
    run down. Raises ``RuntimeError`` only when every candidate has failed.
    """
    errors = []
    for provider, url, api_key, model in candidates:
        print(f"Calling brain: {provider} / {model} ...")
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            print(f"  {provider} call failed ({exc!r}) — trying next provider")
            errors.append(f"{provider}: {exc}")
            continue
        content = resp.json()["choices"][0]["message"]["content"]
        print(f"{provider} response received")
        return provider, model, content
    raise RuntimeError("all configured brain providers failed: " + "; ".join(errors))
