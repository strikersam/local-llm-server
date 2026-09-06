"""Regression test for the auto-PR scripts' brain failover.

On 2026-09-06 the Cerebras paid tier lapsed: every call answered ``402
Payment Required``. ``autonomous_agent.py`` picked Cerebras as its only
candidate (by which key was set) and called ``raise_for_status()`` with no
try/except around it, so the hourly workflow crashed on every run instead of
moving to Groq or NVIDIA — the two other providers the workflow already
passes as secrets. ``.github/scripts/gh_brain_failover.py`` replaces the
crash-on-first-error selection with a candidate list plus a loop that tries
each configured provider in order and only gives up once all of them fail.

Named ``test_gh_brain_failover.py`` (not ``test_brain_failover.py``) because
that name is already taken by the unrelated in-app ``services/brain_failover``
suite; this file covers only the ``.github/scripts/`` module.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GITHUB_SCRIPTS = REPO_ROOT / ".github" / "scripts"


@pytest.fixture()
def gh_brain_failover(monkeypatch):
    monkeypatch.syspath_prepend(str(GITHUB_SCRIPTS))
    sys.modules.pop("gh_brain_failover", None)
    module = importlib.import_module("gh_brain_failover")
    yield module
    sys.modules.pop("gh_brain_failover", None)


class _Response:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}", request=httpx.Request("POST", "https://x"),
                response=httpx.Response(self.status_code, request=httpx.Request("POST", "https://x")),
            )

    def json(self):
        return self._body


class TestBrainCandidates:
    def test_orders_by_priority_and_skips_missing_keys(self, gh_brain_failover, monkeypatch):
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-key")
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        candidates = gh_brain_failover.brain_candidates()
        assert [c[0] for c in candidates] == ["groq", "nvidia"]

    def test_empty_key_is_treated_as_absent(self, gh_brain_failover, monkeypatch):
        """An empty string is falsy — this used to be returned as a live
        NVIDIA candidate anyway and only failed later on ``if not brain_key``."""
        monkeypatch.setenv("NVIDIA_API_KEY", "")
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        assert gh_brain_failover.brain_candidates() == []

    def test_no_keys_configured_returns_empty_list(self, gh_brain_failover, monkeypatch):
        for var in ("CEREBRAS_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        assert gh_brain_failover.brain_candidates() == []


class TestCallBrainWithFailover:
    def test_falls_over_to_the_next_provider_on_an_http_error(self, gh_brain_failover, monkeypatch):
        """The regression itself: a 402 (or any non-2xx) must not be fatal
        while another configured provider is still untried."""
        calls = []

        def fake_post(url, **kwargs):
            calls.append(url)
            if "cerebras" in url:
                return _Response(402)
            return _Response(200, {"choices": [{"message": {"content": "ok from groq"}}]})

        monkeypatch.setattr(gh_brain_failover.httpx, "post", fake_post)
        candidates = [
            ("cerebras", "https://api.cerebras.ai/v1/chat/completions", "ck", "gpt-oss-120b"),
            ("groq", "https://api.groq.com/openai/v1/chat/completions", "gk", "openai/gpt-oss-120b"),
        ]
        provider, model, content = gh_brain_failover.call_brain_with_failover(candidates, [{"role": "user", "content": "hi"}])
        assert provider == "groq"
        assert content == "ok from groq"
        assert len(calls) == 2, "must actually try both providers, not just the first"

    def test_falls_over_on_a_transport_error_too(self, gh_brain_failover, monkeypatch):
        def fake_post(url, **kwargs):
            if "cerebras" in url:
                raise httpx.ConnectTimeout("timed out", request=httpx.Request("POST", url))
            return _Response(200, {"choices": [{"message": {"content": "ok"}}]})

        monkeypatch.setattr(gh_brain_failover.httpx, "post", fake_post)
        candidates = [
            ("cerebras", "https://api.cerebras.ai/v1/chat/completions", "ck", "gpt-oss-120b"),
            ("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions", "nk", "nvidia/nemotron-3-super-120b-a12b"),
        ]
        provider, _model, content = gh_brain_failover.call_brain_with_failover(candidates, [])
        assert provider == "nvidia"
        assert content == "ok"

    def test_stops_at_the_first_success_without_calling_later_candidates(self, gh_brain_failover, monkeypatch):
        calls = []

        def fake_post(url, **kwargs):
            calls.append(url)
            return _Response(200, {"choices": [{"message": {"content": "first"}}]})

        monkeypatch.setattr(gh_brain_failover.httpx, "post", fake_post)
        candidates = [
            ("cerebras", "https://api.cerebras.ai/v1/chat/completions", "ck", "gpt-oss-120b"),
            ("groq", "https://api.groq.com/openai/v1/chat/completions", "gk", "openai/gpt-oss-120b"),
        ]
        gh_brain_failover.call_brain_with_failover(candidates, [])
        assert len(calls) == 1

    def test_raises_only_when_every_candidate_has_failed(self, gh_brain_failover, monkeypatch):
        monkeypatch.setattr(gh_brain_failover.httpx, "post", lambda url, **kw: _Response(500))
        candidates = [
            ("cerebras", "https://api.cerebras.ai/v1/chat/completions", "ck", "gpt-oss-120b"),
            ("groq", "https://api.groq.com/openai/v1/chat/completions", "gk", "openai/gpt-oss-120b"),
        ]
        with pytest.raises(RuntimeError, match="cerebras.*groq|groq.*cerebras"):
            gh_brain_failover.call_brain_with_failover(candidates, [])

    def test_empty_candidate_list_raises_rather_than_indexing(self, gh_brain_failover):
        with pytest.raises(RuntimeError):
            gh_brain_failover.call_brain_with_failover([], [])


class TestAutonomousAgentUsesTheSharedFailover:
    """Guards the actual regression: the crash-prone single-call site is gone."""

    def test_no_unguarded_raise_for_status_remains(self):
        source = (GITHUB_SCRIPTS / "autonomous_agent.py").read_text(encoding="utf-8")
        assert "nim_resp.raise_for_status()" not in source
        assert "from gh_brain_failover import brain_candidates, call_brain_with_failover" in source

    def test_autonomous_fix_shares_the_same_candidate_list(self):
        source = (GITHUB_SCRIPTS / "autonomous_fix.py").read_text(encoding="utf-8")
        assert "from gh_brain_failover import brain_candidates" in source
