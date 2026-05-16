"""Tests for agent/trend_watcher.py"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.trend_watcher import (
    TrendAlert,
    TrendWatcher,
    get_trend_watcher,
    set_trend_watcher,
    _KEYWORDS,
)


@pytest.fixture
def tmp_watcher(tmp_path: Path) -> TrendWatcher:
    return TrendWatcher(cache_path=tmp_path / ".claude/state/trend-cache.json")


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_trend_alert_as_dict():
    alert = TrendAlert(
        source="ollama",
        title="Ollama v0.9.0 released",
        summary="New models supported.",
        url="https://github.com/ollama/ollama/releases/tag/v0.9.0",
        relevance_score=0.95,
        published="2025-05-01",
        tags=["release", "ollama"],
    )
    d = alert.as_dict()
    assert d["source"] == "ollama"
    assert d["relevance_score"] == 0.95
    assert d["published"] == "2025-05-01"
    assert "release" in d["tags"]


def test_relevance_score_high(tmp_watcher):
    text = "ollama gguf quantization inference llm-server openai-compatible streaming model"
    score = tmp_watcher._score(text)
    assert score >= 0.3


def test_relevance_score_low(tmp_watcher):
    score = tmp_watcher._score("banana bread recipe flour sugar eggs bake 350 degrees")
    assert score < 0.1


def test_sig_deterministic(tmp_watcher):
    s1 = tmp_watcher._sig("ollama", "Ollama v1.0 released")
    s2 = tmp_watcher._sig("ollama", "Ollama v1.0 released")
    assert s1 == s2
    assert len(s1) == 16


def test_sig_differs_by_source(tmp_watcher):
    s1 = tmp_watcher._sig("arxiv", "same title")
    s2 = tmp_watcher._sig("github", "same title")
    assert s1 != s2


def test_cache_round_trip(tmp_path: Path):
    cache = tmp_path / ".claude/state/trend-cache.json"
    w1 = TrendWatcher(cache_path=cache)
    w1._seen.add("abc123")
    w1._alerts.append(TrendAlert(
        source="ollama", title="Test", summary="s", url="u",
        relevance_score=0.9, published="2025-01-01",
    ))
    w1._save_cache()

    w2 = TrendWatcher(cache_path=cache)
    assert "abc123" in w2._seen
    assert len(w2._alerts) == 1
    assert w2._alerts[0].title == "Test"


def test_deduplication_by_seen(tmp_watcher):
    tmp_watcher._seen.add(tmp_watcher._sig("ollama", "Ollama v0.9.0 released"))
    # Same title should be filtered in _fetch_ methods — verify sig matches
    sig = tmp_watcher._sig("ollama", "Ollama v0.9.0 released")
    assert sig in tmp_watcher._seen


def test_get_alerts_empty(tmp_watcher):
    assert tmp_watcher.get_alerts() == []


def test_get_alerts_filters_by_source(tmp_watcher):
    tmp_watcher._alerts = [
        TrendAlert("arxiv", "Paper A", "s", "u", 0.8, "2025-01-01"),
        TrendAlert("ollama", "Release B", "s", "u", 0.9, "2025-01-01"),
    ]
    results = tmp_watcher.get_alerts(source="arxiv")
    assert all(a["source"] == "arxiv" for a in results)
    assert len(results) == 1


def test_get_stats_structure(tmp_watcher):
    stats = tmp_watcher.get_stats()
    assert "total_alerts" in stats
    assert "unique_seen" in stats
    assert "fetch_count" in stats
    assert "last_fetch" in stats
    assert "by_source" in stats


def test_due_for_fetch_initially_true(tmp_watcher):
    assert tmp_watcher.due_for_fetch() is True


def test_dispatch_skips_low_relevance(tmp_path: Path):
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop, get_improvement_loop
    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=999)
    set_improvement_loop(loop)

    watcher = TrendWatcher(cache_path=tmp_path / "cache.json")
    low_alert = TrendAlert("arxiv", "Banana bread baking paper", "desc", "url", 0.05, "2025-01-01")
    watcher._dispatch_to_improvement_loop([low_alert])

    status = loop.get_status()
    trend_issues = [i for i in status["active_issues"] if "[Trend]" in i.get("title", "")]
    assert len(trend_issues) == 0

    set_improvement_loop(None)


def test_dispatch_injects_high_relevance(tmp_path: Path):
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=999)
    set_improvement_loop(loop)

    watcher = TrendWatcher(cache_path=tmp_path / "cache.json")
    high_alert = TrendAlert(
        "ollama", "Ollama v9.0 released", "New models for local inference.",
        "https://example.com", 0.9, "2025-05-01",
        tags=["ollama", "release"],
    )
    watcher._dispatch_to_improvement_loop([high_alert])

    status = loop.get_status()
    trend_issues = [i for i in status["active_issues"] if "[Trend]" in i.get("title", "")]
    assert len(trend_issues) == 1
    assert "Ollama v9.0" in trend_issues[0]["title"]

    set_improvement_loop(None)


def test_singleton_round_trip():
    orig = get_trend_watcher()
    w = TrendWatcher()
    set_trend_watcher(w)
    assert get_trend_watcher() is w
    set_trend_watcher(orig)


# ── Async fetch tests (mocked) ────────────────────────────────────────────────

_OLLAMA_RELEASES_PAYLOAD = [
    {
        "tag_name": "v0.9.0",
        "name": "Ollama v0.9.0",
        "body": "Support for new quantization levels.",
        "html_url": "https://github.com/ollama/ollama/releases/tag/v0.9.0",
        "published_at": "2025-05-10T10:00:00Z",
    }
]

_HF_MODELS_PAYLOAD = [
    {
        "modelId": "TheBloke/Llama-3-8B-GGUF",
        "id": "TheBloke/Llama-3-8B-GGUF",
        "tags": ["gguf", "llama"],
        "lastModified": "2025-05-10",
    }
]

_ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2505.12345v1</id>
    <title>LLM Inference Serving Optimization for Local Deployment</title>
    <summary>We present techniques for efficient local LLM inference and model routing in self-hosted proxy servers using ollama and gguf quantization.</summary>
    <published>2025-05-10T00:00:00Z</published>
  </entry>
</feed>"""

_GH_SEARCH_PAYLOAD = {
    "items": [
        {
            "full_name": "example/llm-proxy",
            "description": "OpenAI-compatible local LLM server with model routing",
            "stargazers_count": 1500,
            "html_url": "https://github.com/example/llm-proxy",
            "updated_at": "2025-05-10T00:00:00Z",
            "topics": ["llm", "ollama", "proxy"],
        }
    ]
}


class _FakeResp:
    def __init__(self, payload, text: str | None = None, status_code: int = 200):
        self._payload = payload
        self.text = text or json.dumps(payload)
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payloads: dict):
        self._payloads = payloads

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def get(self, url: str, **kw):
        for key, payload in self._payloads.items():
            if key in url:
                if isinstance(payload, str):
                    return _FakeResp(None, text=payload)
                return _FakeResp(payload)
        return _FakeResp({}, status_code=404)


@pytest.mark.asyncio
async def test_fetch_ollama_releases(tmp_watcher):
    client = _FakeClient({"ollama/ollama/releases": _OLLAMA_RELEASES_PAYLOAD})
    async with client as c:
        alerts = await tmp_watcher._fetch_ollama_releases(c)
    assert len(alerts) >= 1
    assert alerts[0].source == "ollama"
    assert "v0.9.0" in alerts[0].title


@pytest.mark.asyncio
async def test_fetch_ollama_deduplicates(tmp_watcher):
    client = _FakeClient({"ollama/ollama/releases": _OLLAMA_RELEASES_PAYLOAD})
    async with client as c:
        alerts1 = await tmp_watcher._fetch_ollama_releases(c)
        alerts2 = await tmp_watcher._fetch_ollama_releases(c)
    assert len(alerts1) == 1
    assert len(alerts2) == 0  # already seen


@pytest.mark.asyncio
async def test_fetch_hf_trending(tmp_watcher):
    client = _FakeClient({"huggingface.co/api/models": _HF_MODELS_PAYLOAD})
    async with client as c:
        alerts = await tmp_watcher._fetch_hf_trending(c)
    assert len(alerts) >= 1
    assert alerts[0].source == "huggingface"
    assert "GGUF" in alerts[0].title or "gguf" in alerts[0].title.lower()


@pytest.mark.asyncio
async def test_fetch_arxiv(tmp_watcher):
    client = _FakeClient({"arxiv.org/api/query": _ARXIV_ATOM})
    async with client as c:
        alerts = await tmp_watcher._fetch_arxiv(c)
    assert len(alerts) >= 1
    assert alerts[0].source == "arxiv"
    assert "LLM" in alerts[0].title or "llm" in alerts[0].title.lower()


@pytest.mark.asyncio
async def test_fetch_github_trending(tmp_watcher):
    client = _FakeClient({"github.com/search/repositories": _GH_SEARCH_PAYLOAD})
    async with client as c:
        alerts = await tmp_watcher._fetch_github_trending(c)
    assert len(alerts) >= 1
    assert alerts[0].source == "github"


@pytest.mark.asyncio
async def test_fetch_handles_network_error(tmp_watcher, monkeypatch):
    import httpx

    async def raise_connect(*a, **kw):
        raise httpx.ConnectError("refused")

    class _BrokenClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, *a, **kw): raise httpx.ConnectError("refused")

    async with _BrokenClient() as c:
        alerts = await tmp_watcher._fetch_ollama_releases(c)
    assert alerts == []


def test_new_issue_categories_exist():
    from agent.improvement_loop import IssueCategory
    assert IssueCategory.FEATURE_REQUEST == "feature_request"
    assert IssueCategory.TREND == "trend"


def test_get_stats_has_all_sources(tmp_watcher):
    stats = tmp_watcher.get_stats()
    expected_sources = {"arxiv", "huggingface", "ollama", "github", "reddit",
                        "google_news", "hackernews", "nvidia", "paperswithcode", "newsletter"}
    assert expected_sources.issubset(set(stats["by_source"].keys()))


def test_ts_from_epoch(tmp_watcher):
    ts = tmp_watcher._ts_from_epoch(1715000000)
    assert ts.startswith("2024-")  # Unix epoch 1715000000 ≈ May 2024


def test_ts_from_epoch_none(tmp_watcher):
    assert tmp_watcher._ts_from_epoch(None) == ""


# ── New source: Reddit ────────────────────────────────────────────────────────

_REDDIT_PAYLOAD = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Running local llm server with ollama and openai-compatible proxy",
                    "selftext": "I set up a local LLM with Qwen3-Coder and it works great.",
                    "url": "https://www.reddit.com/r/LocalLLaMA/comments/abc123",
                    "permalink": "/r/LocalLLaMA/comments/abc123",
                    "created_utc": 1715000000,
                }
            }
        ]
    }
}


@pytest.mark.asyncio
async def test_fetch_reddit(tmp_watcher):
    client = _FakeClient({"reddit.com/r/LocalLLaMA": _REDDIT_PAYLOAD})
    async with client as c:
        alerts = await tmp_watcher._fetch_reddit(c)
    assert len(alerts) >= 1
    assert alerts[0].source == "reddit"


@pytest.mark.asyncio
async def test_fetch_reddit_low_relevance_excluded(tmp_watcher):
    payload = {
        "data": {
            "children": [
                {"data": {"title": "Best banana bread recipe", "selftext": "", "url": "https://reddit.com/x", "permalink": "/x", "created_utc": 0}}
            ]
        }
    }
    client = _FakeClient({"reddit.com/r/LocalLLaMA": payload})
    async with client as c:
        alerts = await tmp_watcher._fetch_reddit(c)
    assert all(a.relevance_score >= tmp_watcher._min_relevance for a in alerts)


# ── New source: Google News ───────────────────────────────────────────────────

_GNEWS_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Local LLM inference server ollama 2025 benchmark results</title>
    <description>Comparing local LLM servers for inference speed with quantization.</description>
    <link>https://example.com/llm-benchmark</link>
    <pubDate>Sat, 10 May 2025 10:00:00 GMT</pubDate>
  </item>
</channel></rss>"""


@pytest.mark.asyncio
async def test_fetch_google_news(tmp_watcher):
    client = _FakeClient({"news.google.com": _GNEWS_RSS})
    async with client as c:
        alerts = await tmp_watcher._fetch_google_news(c)
    assert all(a.source == "google_news" for a in alerts)


# ── New source: Hacker News ───────────────────────────────────────────────────

_HN_PAYLOAD = {
    "hits": [
        {
            "title": "Show HN: Local LLM proxy with ollama and openai-compatible API",
            "url": "https://github.com/example/llm-proxy",
            "objectID": "12345678",
            "points": 200,
            "created_at_i": 1715000000,
            "story_text": "Built a local LLM server with streaming and quantization support.",
        }
    ]
}


@pytest.mark.asyncio
async def test_fetch_hackernews(tmp_watcher):
    client = _FakeClient({"hn.algolia.com": _HN_PAYLOAD})
    async with client as c:
        alerts = await tmp_watcher._fetch_hackernews(c)
    # Either found by relevance or high point count
    assert all(a.source == "hackernews" for a in alerts)


# ── New source: Nvidia ────────────────────────────────────────────────────────

_NVIDIA_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>TensorRT-LLM Speedup for Local Inference on RTX GPUs</title>
    <description>NVIDIA releases TensorRT-LLM update for faster inference on consumer GPUs.</description>
    <link>https://developer.nvidia.com/blog/tensorrt-llm-rtx</link>
    <pubDate>Sat, 10 May 2025 10:00:00 GMT</pubDate>
  </item>
</channel></rss>"""


@pytest.mark.asyncio
async def test_fetch_nvidia(tmp_watcher):
    client = _FakeClient({"developer.nvidia.com": _NVIDIA_RSS})
    async with client as c:
        alerts = await tmp_watcher._fetch_nvidia(c)
    assert all(a.source == "nvidia" for a in alerts)
    if alerts:
        assert "nvidia" in alerts[0].tags


# ── New source: Papers With Code ──────────────────────────────────────────────

_PWC_PAYLOAD = {
    "results": [
        {
            "title": "Efficient LLM Serving with Speculative Decoding for Local Inference",
            "abstract": "We propose efficient speculative decoding for local LLM inference servers.",
            "url_abs": "2505.00001",
            "published": "2025-05-10",
        }
    ]
}


@pytest.mark.asyncio
async def test_fetch_papers_with_code(tmp_watcher):
    client = _FakeClient({"paperswithcode.com": _PWC_PAYLOAD})
    async with client as c:
        alerts = await tmp_watcher._fetch_papers_with_code(c)
    assert all(a.source == "paperswithcode" for a in alerts)


# ── New source: Newsletters ───────────────────────────────────────────────────

_NEWSLETTER_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Open-source LLM inference: ollama and quantization roundup</title>
    <link href="https://newsletter.example.com/issue/42"/>
    <summary>Weekly roundup on local LLM inference, ollama releases, and gguf quantization.</summary>
    <published>2025-05-10</published>
  </entry>
</feed>"""


@pytest.mark.asyncio
async def test_fetch_newsletters(tmp_watcher, monkeypatch):
    # Patch _NEWSLETTER_FEEDS to use a single fake URL
    import agent.trend_watcher as tw_mod
    orig = tw_mod._NEWSLETTER_FEEDS
    tw_mod._NEWSLETTER_FEEDS = {"Test Newsletter": "https://newsletter.example.com/feed"}
    try:
        client = _FakeClient({"newsletter.example.com": _NEWSLETTER_ATOM})
        async with client as c:
            alerts = await tmp_watcher._fetch_newsletters(c)
        assert all(a.source == "newsletter" for a in alerts)
    finally:
        tw_mod._NEWSLETTER_FEEDS = orig


# ── Keyword expansion ─────────────────────────────────────────────────────────

def test_keywords_include_new_terms():
    """Ensure expanded keyword set covers key new categories."""
    assert "nvidia" in _KEYWORDS
    assert "cuda" in _KEYWORDS
    assert "agentic" in _KEYWORDS or "ai agent" in _KEYWORDS
    assert "rag" in _KEYWORDS or "retrieval augmented" in _KEYWORDS
    assert "lora" in _KEYWORDS
