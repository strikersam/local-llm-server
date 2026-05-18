"""Tests for agent/knowledge_sync.py"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.knowledge_sync import (
    KnowledgeSync,
    SyncResult,
    _api_key,
    _auth_headers,
    _build_digest_markdown,
    create_wiki_page,
    fetch_and_store,
    get_knowledge_sync,
    set_knowledge_sync,
    sync_trends,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_alert(score: float = 0.7, source: str = "ollama", url: str = "https://example.com") -> dict:
    return {
        "source": source,
        "title": f"Test alert from {source}",
        "summary": "Summary text about llm inference ollama.",
        "url": url,
        "relevance_score": score,
        "published": "2025-05-01",
        "tags": ["test"],
    }


class _FakeResp:
    def __init__(self, status_code: int, data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, post_resp: _FakeResp | None = None):
        self._post_resp = post_resp or _FakeResp(201, {"id": "page-1"})

    async def post(self, url: str, **kwargs):
        return self._post_resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ── Unit: _api_key and headers ────────────────────────────────────────────────

def test_api_key_fallback(monkeypatch):
    monkeypatch.delenv("PROXY_API_KEY", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    key = _api_key()
    assert key == "knowledge-sync-internal"


def test_api_key_uses_proxy_api_key(monkeypatch):
    monkeypatch.setenv("PROXY_API_KEY", "test-key-abc")
    assert _api_key() == "test-key-abc"


def test_auth_headers_include_bearer():
    headers = _auth_headers()
    assert headers.get("Authorization", "").startswith("Bearer ")


# ── Unit: digest builder ──────────────────────────────────────────────────────

def test_build_digest_no_alerts():
    md = _build_digest_markdown([], "Week of 2025-05-01")
    assert "2025-05-01" in md
    assert "No high-relevance" in md


def test_build_digest_includes_high_relevance():
    alerts = [_make_alert(score=0.8, source="arxiv", url="https://arxiv.org/abs/1234")]
    md = _build_digest_markdown(alerts, "Week of 2025-05-01")
    assert "80%" in md
    assert "https://arxiv.org/abs/1234" in md


def test_build_digest_includes_low_relevance_section():
    alerts = [_make_alert(score=0.1, source="github")]
    md = _build_digest_markdown(alerts, "Week of 2025-05-01")
    assert "Lower-relevance" in md


# ── Async: fetch_and_store ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_and_store_success() -> None:
    client = _FakeClient(_FakeResp(201, {"id": "src-1", "title": "My source"}))
    result = await fetch_and_store(
        url="https://example.com/article",
        title="Test article",
        tags=["ai", "llm"],
        client=client,
    )
    assert result.get("id") == "src-1"


@pytest.mark.asyncio
async def test_fetch_and_store_non_200_returns_error() -> None:
    client = _FakeClient(_FakeResp(422, text="Unprocessable"))
    result = await fetch_and_store(
        url="https://example.com",
        title="Bad",
        client=client,
    )
    assert "error" in result
    assert result.get("status_code") == 422


@pytest.mark.asyncio
async def test_fetch_and_store_network_error() -> None:
    async def _fail(*a, **kw):
        raise httpx.ConnectError("refused")

    client = MagicMock()
    client.post = _fail
    result = await fetch_and_store(url="https://x.com", title="fail", client=client)
    assert "error" in result


# ── Async: create_wiki_page ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_wiki_page_success() -> None:
    client = _FakeClient(_FakeResp(201, {"id": "page-42", "title": "My page"}))
    result = await create_wiki_page(
        title="AI Trend Digest — Week of 2025-05-01",
        content="# Digest\n\nContent here.",
        tags=["auto-generated"],
        client=client,
    )
    assert result.get("id") == "page-42"


@pytest.mark.asyncio
async def test_create_wiki_page_409_returns_skipped() -> None:
    client = _FakeClient(_FakeResp(409, text="Conflict"))
    result = await create_wiki_page(title="duplicate", content="x", client=client)
    assert result.get("skipped") is True


# ── Async: sync_trends ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_trends_no_watcher_returns_empty() -> None:
    with patch("agent.trend_watcher.get_trend_watcher", return_value=None):
        result = await sync_trends()
    assert isinstance(result, SyncResult)
    assert result.ingested == 0


@pytest.mark.asyncio
async def test_sync_trends_empty_alerts() -> None:
    result = await sync_trends(alerts=[])
    assert result.ingested == 0
    assert result.errors == 0


@pytest.mark.asyncio
async def test_sync_trends_ingests_high_relevance(monkeypatch) -> None:
    alerts = [_make_alert(score=0.8, url="https://ollama.ai/blog/release")]
    post_calls: list[dict] = []

    async def _mock_post(url, **kwargs):
        post_calls.append({"url": url, "kwargs": kwargs})
        return _FakeResp(201, {"id": "x"})

    mock_client = MagicMock()
    mock_client.post = _mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("agent.knowledge_sync.httpx.AsyncClient", return_value=mock_client):
        result = await sync_trends(alerts=alerts)

    # One ingest call + one wiki call
    assert result.ingested >= 1


@pytest.mark.asyncio
async def test_sync_trends_skips_low_relevance(monkeypatch) -> None:
    alerts = [_make_alert(score=0.1, url="https://example.com/irrelevant")]
    wiki_calls: list = []

    async def _mock_post(url, **kwargs):
        if "/api/wiki" in url:
            wiki_calls.append(url)
            return _FakeResp(201, {"id": "wiki"})
        return _FakeResp(201, {"id": "src"})

    mock_client = MagicMock()
    mock_client.post = _mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("agent.knowledge_sync.httpx.AsyncClient", return_value=mock_client):
        result = await sync_trends(alerts=alerts)

    # Low-relevance alert should NOT be ingested into Sources
    assert result.ingested == 0


# ── Singleton ─────────────────────────────────────────────────────────────────

def test_knowledge_sync_singleton_round_trip():
    ks = KnowledgeSync()
    set_knowledge_sync(ks)
    assert get_knowledge_sync() is ks


def test_knowledge_sync_defaults_none_before_set():
    import agent.knowledge_sync as ks_mod
    original = ks_mod._instance
    ks_mod._instance = None
    assert get_knowledge_sync() is None
    ks_mod._instance = original


# ── KnowledgeSync class methods ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_knowledge_sync_ingest_url() -> None:
    ks = KnowledgeSync()
    with patch("agent.knowledge_sync.fetch_and_store", new_callable=AsyncMock, return_value={"id": "s1"}) as mock_fn:
        result = await ks.ingest_url("https://x.com", "Test", ["tag1"])
    mock_fn.assert_called_once()
    assert result == {"id": "s1"}


@pytest.mark.asyncio
async def test_knowledge_sync_create_page() -> None:
    ks = KnowledgeSync()
    with patch("agent.knowledge_sync.create_wiki_page", new_callable=AsyncMock, return_value={"id": "p1"}) as mock_fn:
        result = await ks.create_page("Title", "Content")
    mock_fn.assert_called_once()
    assert result == {"id": "p1"}
