"""agent/trend_watcher.py — Internet-connected AI trend intelligence.

Periodically fetches from public APIs to discover:
  • New Ollama model releases
  • Trending GGUF-compatible models on HuggingFace
  • Relevant AI/LLM research from arXiv
  • Trending LLM-serving repos on GitHub

High-relevance findings are registered as DetectedIssue items in the
improvement loop so the CEO + Dev agents can evaluate and act on them.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("qwen-proxy")

# ── Domain relevance keywords ──────────────────────────────────────────────────
_KEYWORDS = frozenset({
    "ollama", "llm-server", "llm server", "local llm", "openai-compatible",
    "inference server", "model router", "llm proxy", "llm routing",
    "gguf", "ggml", "quantization", "vllm", "lmstudio", "mlx",
    "streaming chat", "self-hosted", "open weights", "model serving",
    "langfuse", "observability", "context caching", "speculative decoding",
    "mixture of experts", "moe", "function calling", "tool use",
})

# Sources
_ARXIV_API = "https://export.arxiv.org/api/query"
_HF_API    = "https://huggingface.co/api/models"
_GH_OLLAMA = "https://api.github.com/repos/ollama/ollama/releases"
_GH_SEARCH = "https://api.github.com/search/repositories"
_GH_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

FETCH_INTERVAL_HOURS = 6
MIN_RELEVANCE = 0.25


@dataclass
class TrendAlert:
    source: str          # arxiv | huggingface | ollama | github
    title: str
    summary: str
    url: str
    relevance_score: float
    published: str
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary[:300],
            "url": self.url,
            "relevance_score": round(self.relevance_score, 3),
            "published": self.published,
            "tags": self.tags,
        }


class TrendWatcher:
    """Fetches AI trend signals from public APIs and surfaces relevant ones."""

    def __init__(
        self,
        cache_path: Path | None = None,
        min_relevance: float = MIN_RELEVANCE,
    ) -> None:
        self._cache_path = cache_path or Path(".claude/state/trend-cache.json")
        self._min_relevance = min_relevance
        self._alerts: list[TrendAlert] = []
        self._seen: set[str] = set()
        self._last_fetch: float = 0.0
        self._fetch_count: int = 0
        self._load_cache()

    # ── Cache ──────────────────────────────────────────────────────────────────

    def _load_cache(self) -> None:
        if not self._cache_path.exists():
            return
        try:
            data = json.loads(self._cache_path.read_text())
            self._seen = set(data.get("seen", []))
            self._last_fetch = float(data.get("last_fetch", 0.0))
            self._fetch_count = int(data.get("fetch_count", 0))
            for a in data.get("alerts", []):
                try:
                    self._alerts.append(TrendAlert(**a))
                except Exception:
                    pass
        except Exception as exc:
            log.debug("TrendWatcher: cache load error: %s", exc)

    def _save_cache(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps({
                "seen": list(self._seen),
                "last_fetch": self._last_fetch,
                "fetch_count": self._fetch_count,
                "alerts": [a.as_dict() for a in self._alerts[-100:]],
            }, indent=2))
        except Exception as exc:
            log.debug("TrendWatcher: cache save error: %s", exc)

    # ── Relevance scoring ──────────────────────────────────────────────────────

    def _score(self, *texts: str) -> float:
        combined = " ".join(t.lower() for t in texts if t)
        hits = sum(1 for kw in _KEYWORDS if kw in combined)
        return min(hits / max(len(_KEYWORDS) * 0.2, 1), 1.0)

    def _sig(self, source: str, title: str) -> str:
        return hashlib.sha256(f"{source}:{title}".encode()).hexdigest()[:16]

    # ── Fetch: arXiv ──────────────────────────────────────────────────────────

    async def _fetch_arxiv(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_ARXIV_API, params={
                "search_query": (
                    "ti:llm-serving OR ti:local-llm OR ti:inference-serving "
                    "OR ti:llm-routing OR ti:ollama OR abs:model-routing "
                    "OR ti:openai-compatible"
                ),
                "start": 0,
                "max_results": 15,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }, timeout=20)
            if r.status_code != 200:
                return alerts

            ns = {"a": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(r.text)
            for entry in root.findall("a:entry", ns):
                title   = (entry.findtext("a:title", "", ns) or "").strip()
                summary = (entry.findtext("a:summary", "", ns) or "").strip()
                url     = (entry.findtext("a:id", "", ns) or "").strip()
                pub     = (entry.findtext("a:published", "", ns) or "")[:10]
                sig = self._sig("arxiv", title)
                if sig in self._seen:
                    continue
                score = self._score(title, summary)
                if score >= self._min_relevance:
                    alerts.append(TrendAlert(
                        source="arxiv", title=title[:120], summary=summary[:400],
                        url=url, relevance_score=score, published=pub,
                        tags=["research", "paper"],
                    ))
                    self._seen.add(sig)
        except Exception as exc:
            log.warning("TrendWatcher: arXiv error: %s", exc)
        return alerts

    # ── Fetch: Ollama releases ────────────────────────────────────────────────

    async def _fetch_ollama_releases(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_GH_OLLAMA, headers=_GH_HEADERS, timeout=10)
            if r.status_code != 200:
                return alerts
            for rel in r.json()[:5]:
                tag   = rel.get("tag_name", "")
                title = f"Ollama {tag} released"
                sig   = self._sig("ollama", title)
                if sig in self._seen:
                    continue
                body = (rel.get("body") or "")[:500]
                alerts.append(TrendAlert(
                    source="ollama",
                    title=title,
                    summary=body or f"New Ollama release {tag}. Check for new model support and API changes.",
                    url=rel.get("html_url", ""),
                    relevance_score=0.95,
                    published=(rel.get("published_at") or "")[:10],
                    tags=["ollama", "release", "model-support", "action-required"],
                ))
                self._seen.add(sig)
        except Exception as exc:
            log.warning("TrendWatcher: Ollama releases error: %s", exc)
        return alerts

    # ── Fetch: HuggingFace trending GGUF models ───────────────────────────────

    async def _fetch_hf_trending(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_HF_API, params={
                "sort": "trending", "limit": 20, "filter": "gguf",
            }, timeout=15)
            if r.status_code != 200:
                return alerts
            for m in r.json()[:8]:
                model_id = m.get("modelId") or m.get("id", "")
                if not model_id:
                    continue
                title = f"Trending GGUF model: {model_id}"
                sig   = self._sig("huggingface", title)
                if sig in self._seen:
                    continue
                tags  = m.get("tags", [])
                score = max(self._score(model_id, " ".join(str(t) for t in tags)), 0.5)
                alerts.append(TrendAlert(
                    source="huggingface",
                    title=title,
                    summary=(
                        f"Model `{model_id}` is trending on HuggingFace in GGUF format. "
                        f"Consider adding to the Ollama model registry if it fits our routing needs."
                    ),
                    url=f"https://huggingface.co/{model_id}",
                    relevance_score=score,
                    published=(m.get("lastModified") or "")[:10],
                    tags=["model", "gguf", "ollama-candidate"],
                ))
                self._seen.add(sig)
        except Exception as exc:
            log.warning("TrendWatcher: HuggingFace error: %s", exc)
        return alerts

    # ── Fetch: GitHub trending LLM-serving repos ──────────────────────────────

    async def _fetch_github_trending(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_GH_SEARCH, headers=_GH_HEADERS, params={
                "q": "local LLM server proxy ollama openai-compatible stars:>200 pushed:>2024-01-01",
                "sort": "updated",
                "order": "desc",
                "per_page": 10,
            }, timeout=15)
            if r.status_code != 200:
                return alerts
            for repo in r.json().get("items", [])[:5]:
                full_name = repo.get("full_name", "")
                desc      = repo.get("description") or ""
                stars     = repo.get("stargazers_count", 0)
                sig       = self._sig("github", full_name)
                if sig in self._seen:
                    continue
                score = self._score(full_name, desc, " ".join(repo.get("topics", [])))
                if score >= self._min_relevance:
                    alerts.append(TrendAlert(
                        source="github",
                        title=f"GitHub: {full_name} ({stars:,} ★)",
                        summary=desc[:400],
                        url=repo.get("html_url", ""),
                        relevance_score=score,
                        published=(repo.get("updated_at") or "")[:10],
                        tags=(repo.get("topics", [])[:4] + ["trending-repo"]),
                    ))
                    self._seen.add(sig)
        except Exception as exc:
            log.warning("TrendWatcher: GitHub trending error: %s", exc)
        return alerts

    # ── Main fetch ────────────────────────────────────────────────────────────

    async def fetch(self) -> list[TrendAlert]:
        """Fetch all sources in parallel; return new alerts sorted by relevance."""
        log.info("TrendWatcher: starting fetch cycle")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = await asyncio.gather(
                self._fetch_arxiv(client),
                self._fetch_ollama_releases(client),
                self._fetch_hf_trending(client),
                self._fetch_github_trending(client),
                return_exceptions=True,
            )
        new_alerts: list[TrendAlert] = []
        for r in results:
            if isinstance(r, list):
                new_alerts.extend(r)

        new_alerts.sort(key=lambda a: a.relevance_score, reverse=True)
        self._alerts.extend(new_alerts)
        self._last_fetch = time.time()
        self._fetch_count += 1
        self._save_cache()

        log.info("TrendWatcher: fetch complete — %d new alert(s)", len(new_alerts))
        self._dispatch_to_improvement_loop(new_alerts)
        return new_alerts

    # ── Improvement loop integration ──────────────────────────────────────────

    def _dispatch_to_improvement_loop(self, alerts: list[TrendAlert]) -> None:
        try:
            from agent.improvement_loop import (
                DetectedIssue, IssueCategory, IssueSeverity, get_improvement_loop,
            )
            loop = get_improvement_loop()
            if not loop:
                return
            for alert in alerts:
                if alert.relevance_score < 0.6:
                    continue
                issue = DetectedIssue(
                    issue_id=f"trend_{self._sig(alert.source, alert.title)}",
                    category=IssueCategory.DOCUMENTATION,
                    severity=IssueSeverity.LOW,
                    title=f"[Trend] {alert.title}",
                    description=(
                        f"Source: {alert.source}\n"
                        f"URL: {alert.url}\n"
                        f"Published: {alert.published}\n\n"
                        f"{alert.summary}\n\n"
                        f"Evaluate if this is actionable for the local-llm-server repo. "
                        f"If the Ollama release adds new models, update router/registry.py. "
                        f"If a research technique is applicable, create a GitHub issue."
                    ),
                )
                loop._register_issue(issue)
        except Exception as exc:
            log.debug("TrendWatcher: dispatch error: %s", exc)

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_alerts(self, limit: int = 30, source: str | None = None) -> list[dict]:
        alerts = self._alerts
        if source:
            alerts = [a for a in alerts if a.source == source]
        return [a.as_dict() for a in reversed(alerts[-limit:])]

    def get_stats(self) -> dict[str, Any]:
        from datetime import datetime, timezone
        return {
            "total_alerts": len(self._alerts),
            "unique_seen": len(self._seen),
            "fetch_count": self._fetch_count,
            "last_fetch": (
                datetime.fromtimestamp(self._last_fetch, tz=timezone.utc).isoformat()
                if self._last_fetch else None
            ),
            "by_source": {
                s: sum(1 for a in self._alerts if a.source == s)
                for s in ("arxiv", "huggingface", "ollama", "github")
            },
        }

    def due_for_fetch(self) -> bool:
        return (time.time() - self._last_fetch) > (FETCH_INTERVAL_HOURS * 3600)


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: TrendWatcher | None = None


def get_trend_watcher() -> TrendWatcher | None:
    return _instance


def set_trend_watcher(w: TrendWatcher) -> None:
    global _instance
    _instance = w
