"""agent/trend_watcher.py — Internet-connected AI trend intelligence.

Fetches from a wide variety of public sources to discover:
  • arXiv research papers (LLM serving, inference, routing)
  • New Ollama model releases (GitHub)
  • Trending GGUF-compatible models on HuggingFace
  • Trending LLM-serving repos on GitHub
  • Reddit: r/LocalLLaMA, r/MachineLearning, r/artificial
  • Google News RSS: AI / LLM topics
  • Hacker News (Algolia Search API) — AI / LLM stories
  • Nvidia Developer Blog RSS (CUDA, TensorRT, GPU inference)
  • Papers With Code (trending ML methods/tasks)
  • Substack AI newsletters (The Batch, Interconnects, The AI Edge)

High-relevance findings are registered as DetectedIssue items in the
improvement loop so the CEO + Dev agents can evaluate and act on them.
All network calls are read-only, use only public / anonymous endpoints,
and require no API keys.
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
from urllib.parse import quote_plus

import httpx

log = logging.getLogger("qwen-proxy")

# ── Domain relevance keywords ──────────────────────────────────────────────────
# Expanded to cover Nvidia / GPU acceleration, agents, RAG, fine-tuning, etc.
_KEYWORDS = frozenset({
    # Serving & proxy
    "ollama", "llm-server", "llm server", "local llm", "openai-compatible",
    "inference server", "model router", "llm proxy", "llm routing",
    # Formats & quantisation
    "gguf", "ggml", "quantization", "quantisation", "int4", "int8", "awq", "gptq",
    # Inference engines
    "vllm", "lmstudio", "mlx", "llama.cpp", "tensorrt-llm", "trt-llm",
    "text-generation-inference", "tgi", "llamafile", "koboldcpp",
    # GPU / Nvidia
    "nvidia", "cuda", "tensorrt", "h100", "a100", "rtx", "gpu inference",
    "flash attention", "paged attention", "speculative decoding",
    # Streaming / chat
    "streaming chat", "chat completion", "function calling", "tool use",
    # Hosting patterns
    "self-hosted", "open weights", "model serving", "private ai",
    # Observability
    "langfuse", "observability", "context caching", "mixture of experts", "moe",
    # Agents & RAG
    "ai agent", "autonomous agent", "agentic", "rag", "retrieval augmented",
    "multi-agent", "agent orchestration", "tool calling", "claude code",
    "aider", "goose", "cursor", "copilot",
    # Fine-tuning
    "lora", "qlora", "fine-tuning", "finetuning", "adapter",
    # Models we care about
    "qwen", "deepseek", "mistral", "llama", "phi", "gemma", "hermes",
    "yi ", "command-r", "mixtral",
    # General AI infra
    "openai api", "anthropic", "langchain", "langgraph", "semantic kernel",
})

# ── Source URLs ────────────────────────────────────────────────────────────────
_ARXIV_API    = "https://export.arxiv.org/api/query"
_HF_API       = "https://huggingface.co/api/models"
_GH_OLLAMA    = "https://api.github.com/repos/ollama/ollama/releases"
_GH_SEARCH    = "https://api.github.com/search/repositories"
_GH_HEADERS   = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

# Reddit JSON — no auth needed for public subreddits
_REDDIT_SUBS  = ["LocalLLaMA", "MachineLearning", "artificial", "singularity"]
_REDDIT_BASE  = "https://www.reddit.com/r/{sub}/new.json?limit=20&sort=new"

# Google News RSS
_GNEWS_TERMS  = [
    "local LLM inference server",
    "ollama model release",
    "LLM proxy openai compatible",
    "Nvidia GPU AI inference 2025",
    "open source AI agent 2025",
]
_GNEWS_BASE   = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Hacker News via Algolia
_HN_API       = "https://hn.algolia.com/api/v1/search"

# Nvidia Developer Blog
_NVIDIA_RSS   = "https://developer.nvidia.com/blog/feed/"

# Papers With Code — trending papers
_PWC_TRENDING = "https://paperswithcode.com/api/v1/papers/?ordering=-github_stars&items_per_page=15"

# AI newsletter RSS feeds (public Substack feeds + others)
_NEWSLETTER_FEEDS: dict[str, str] = {
    "The Batch (deeplearning.ai)": "https://www.deeplearning.ai/the-batch/feed/",
    "Interconnects (Nathan Lambert)": "https://www.interconnects.ai/feed",
    "The AI Edge": "https://newsletter.theaiedge.io/feed",
    "Simon Willison's Blog": "https://simonwillison.net/atom/everything/",
    "Sebastian Raschka (Magazine)": "https://magazine.sebastianraschka.com/feed",
}

FETCH_INTERVAL_HOURS = 6
MIN_RELEVANCE        = 0.25

# Reddit user-agent (required or Reddit returns 429/403)
_REDDIT_HEADERS = {"User-Agent": "local-llm-server/4.1 (trend-watcher; +https://github.com/strikersam/local-llm-server)"}


@dataclass
class TrendAlert:
    source: str
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
    """Fetches AI trend signals from many public sources and surfaces relevant ones."""

    _ALL_SOURCES = frozenset({
        "arxiv", "huggingface", "ollama", "github",
        "reddit", "google_news", "hackernews", "nvidia",
        "paperswithcode", "newsletter",
    })

    def __init__(
        self,
        cache_path: Path | None = None,
        min_relevance: float = MIN_RELEVANCE,
    ) -> None:
        self._cache_path    = cache_path or Path(".claude/state/trend-cache.json")
        self._min_relevance = min_relevance
        self._alerts: list[TrendAlert] = []
        self._seen:   set[str]         = set()
        self._last_fetch:  float = 0.0
        self._fetch_count: int   = 0
        self._load_cache()

    # ── Cache ──────────────────────────────────────────────────────────────────

    def _load_cache(self) -> None:
        if not self._cache_path.exists():
            return
        try:
            data = json.loads(self._cache_path.read_text())
            self._seen        = set(data.get("seen", []))
            self._last_fetch  = float(data.get("last_fetch", 0.0))
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
                "seen":        list(self._seen),
                "last_fetch":  self._last_fetch,
                "fetch_count": self._fetch_count,
                "alerts":      [a.as_dict() for a in self._alerts[-200:]],
            }, indent=2))
        except Exception as exc:
            log.debug("TrendWatcher: cache save error: %s", exc)

    # ── Relevance scoring ──────────────────────────────────────────────────────

    def _score(self, *texts: str) -> float:
        combined = " ".join(t.lower() for t in texts if t)
        hits = sum(1 for kw in _KEYWORDS if kw in combined)
        return min(hits / max(len(_KEYWORDS) * 0.15, 1), 1.0)

    def _sig(self, source: str, title: str) -> str:
        return hashlib.sha256(f"{source}:{title}".encode()).hexdigest()[:16]

    def _ts_from_epoch(self, epoch: float | int | None) -> str:
        if not epoch:
            return ""
        try:
            return time.strftime("%Y-%m-%d", time.gmtime(float(epoch)))
        except Exception:
            return ""

    # ── Fetch: arXiv ─────────────────────────────────────────────────────────

    async def _fetch_arxiv(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_ARXIV_API, params={
                "search_query": (
                    "ti:llm-serving OR ti:local-llm OR ti:inference-serving "
                    "OR ti:llm-routing OR ti:ollama OR abs:model-routing "
                    "OR ti:openai-compatible OR ti:speculative-decoding "
                    "OR ti:mixture-of-experts OR ti:rag-retrieval"
                ),
                "start": 0, "max_results": 20,
                "sortBy": "submittedDate", "sortOrder": "descending",
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
                sig     = self._sig("arxiv", title)
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
                    source="ollama", title=title,
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
                "sort": "trending", "limit": 25, "filter": "gguf",
            }, timeout=15)
            if r.status_code != 200:
                return alerts
            for m in r.json()[:10]:
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
                    source="huggingface", title=title,
                    summary=(
                        f"Model `{model_id}` is trending on HuggingFace in GGUF format. "
                        f"Consider adding to the Ollama model registry."
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

    # ── Fetch: GitHub trending LLM repos ─────────────────────────────────────

    async def _fetch_github_trending(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_GH_SEARCH, headers=_GH_HEADERS, params={
                "q": "local LLM server proxy ollama openai-compatible stars:>200 pushed:>2024-01-01",
                "sort": "updated", "order": "desc", "per_page": 10,
            }, timeout=15)
            if r.status_code != 200:
                return alerts
            for repo in r.json().get("items", [])[:6]:
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

    # ── Fetch: Reddit ─────────────────────────────────────────────────────────

    async def _fetch_reddit(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        for sub in _REDDIT_SUBS:
            try:
                r = await client.get(
                    _REDDIT_BASE.format(sub=sub),
                    headers=_REDDIT_HEADERS, timeout=12,
                )
                if r.status_code != 200:
                    continue
                posts = r.json().get("data", {}).get("children", [])
                for post_wrap in posts[:15]:
                    post = post_wrap.get("data", {})
                    title   = (post.get("title") or "").strip()
                    selftext = (post.get("selftext") or "").strip()[:300]
                    url     = post.get("url") or f"https://reddit.com{post.get('permalink','')}"
                    created = self._ts_from_epoch(post.get("created_utc"))
                    sig     = self._sig(f"reddit-{sub}", title)
                    if sig in self._seen or not title:
                        continue
                    score = self._score(title, selftext, sub)
                    if score >= self._min_relevance:
                        alerts.append(TrendAlert(
                            source="reddit",
                            title=f"r/{sub}: {title[:100]}",
                            summary=selftext or f"Hot post in r/{sub}",
                            url=url,
                            relevance_score=score,
                            published=created,
                            tags=[f"r/{sub}", "community", "reddit"],
                        ))
                        self._seen.add(sig)
            except Exception as exc:
                log.debug("TrendWatcher: Reddit r/%s error: %s", sub, exc)
        return alerts

    # ── Fetch: Google News RSS ────────────────────────────────────────────────

    async def _fetch_google_news(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        for term in _GNEWS_TERMS[:3]:
            try:
                url = _GNEWS_BASE.format(q=quote_plus(term))
                r = await client.get(url, timeout=15)
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.text)
                items = root.findall(".//item")
                for item in items[:8]:
                    title   = (item.findtext("title") or "").strip()
                    desc    = (item.findtext("description") or "").strip()
                    link    = (item.findtext("link") or "").strip()
                    pub_raw = (item.findtext("pubDate") or "")
                    sig     = self._sig("google_news", title)
                    if sig in self._seen or not title:
                        continue
                    score = self._score(title, desc, term)
                    if score >= self._min_relevance:
                        alerts.append(TrendAlert(
                            source="google_news",
                            title=title[:120],
                            summary=desc[:300] or f"Google News result for '{term}'",
                            url=link,
                            relevance_score=score,
                            published=pub_raw[:10] if pub_raw else "",
                            tags=["news", "google-news", "media"],
                        ))
                        self._seen.add(sig)
            except Exception as exc:
                log.debug("TrendWatcher: Google News error term=%r: %s", term, exc)
        return alerts

    # ── Fetch: Hacker News ────────────────────────────────────────────────────

    async def _fetch_hackernews(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        hn_queries = [
            "local LLM ollama inference",
            "vllm llama.cpp quantization",
            "AI agent autonomous LLM",
        ]
        for q in hn_queries[:2]:
            try:
                r = await client.get(_HN_API, params={
                    "query": q, "tags": "story",
                    "hitsPerPage": 10,
                    "numericFilters": f"created_at_i>{int(time.time()) - 7 * 86400}",
                }, timeout=10)
                if r.status_code != 200:
                    continue
                for hit in r.json().get("hits", []):
                    title = (hit.get("title") or "").strip()
                    url   = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID','')}"
                    pts   = hit.get("points", 0) or 0
                    pub   = self._ts_from_epoch(hit.get("created_at_i"))
                    sig   = self._sig("hackernews", title)
                    if sig in self._seen or not title:
                        continue
                    score = self._score(title, hit.get("story_text") or "", q)
                    if score >= self._min_relevance or pts >= 50:
                        score = max(score, 0.35)
                        alerts.append(TrendAlert(
                            source="hackernews",
                            title=f"HN ({pts}pts): {title[:100]}",
                            summary=f"{pts} points on Hacker News. {(hit.get('story_text') or '')[:250]}",
                            url=url,
                            relevance_score=min(score + pts / 1000, 1.0),
                            published=pub,
                            tags=["hackernews", "community", "discussion"],
                        ))
                        self._seen.add(sig)
            except Exception as exc:
                log.debug("TrendWatcher: HN error: %s", exc)
        return alerts

    # ── Fetch: Nvidia Developer Blog ──────────────────────────────────────────

    async def _fetch_nvidia(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_NVIDIA_RSS, timeout=15)
            if r.status_code != 200:
                return alerts
            root = ET.fromstring(r.text)
            items = root.findall(".//item")
            for item in items[:12]:
                title   = (item.findtext("title") or "").strip()
                desc    = (item.findtext("description") or "").strip()
                link    = (item.findtext("link") or "").strip()
                pub_raw = (item.findtext("pubDate") or "")
                sig     = self._sig("nvidia", title)
                if sig in self._seen or not title:
                    continue
                score = self._score(title, desc)
                # Boost GPU-related Nvidia posts
                gpu_terms = ("tensorrt", "cuda", "inference", "llm", "gpu", "h100", "a100", "rtx", "triton")
                if any(t in title.lower() or t in desc.lower() for t in gpu_terms):
                    score = max(score, 0.45)
                if score >= self._min_relevance:
                    alerts.append(TrendAlert(
                        source="nvidia",
                        title=title[:120],
                        summary=desc[:300],
                        url=link,
                        relevance_score=score,
                        published=pub_raw[:10] if pub_raw else "",
                        tags=["nvidia", "gpu", "cuda", "inference"],
                    ))
                    self._seen.add(sig)
        except Exception as exc:
            log.debug("TrendWatcher: Nvidia blog error: %s", exc)
        return alerts

    # ── Fetch: Papers With Code ───────────────────────────────────────────────

    async def _fetch_papers_with_code(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        try:
            r = await client.get(_PWC_TRENDING, timeout=15)
            if r.status_code != 200:
                return alerts
            for paper in r.json().get("results", [])[:10]:
                title   = (paper.get("title") or "").strip()
                abstract = (paper.get("abstract") or "").strip()[:350]
                url_paper = paper.get("url_abs") or paper.get("arxiv_id") or ""
                if url_paper and not url_paper.startswith("http"):
                    url_paper = f"https://arxiv.org/abs/{url_paper}"
                pub = (paper.get("published") or "")[:10]
                sig = self._sig("paperswithcode", title)
                if sig in self._seen or not title:
                    continue
                score = self._score(title, abstract)
                if score >= self._min_relevance:
                    alerts.append(TrendAlert(
                        source="paperswithcode",
                        title=title[:120],
                        summary=abstract,
                        url=url_paper,
                        relevance_score=score,
                        published=pub,
                        tags=["research", "paper", "paperswithcode"],
                    ))
                    self._seen.add(sig)
        except Exception as exc:
            log.debug("TrendWatcher: Papers With Code error: %s", exc)
        return alerts

    # ── Fetch: AI newsletters (RSS) ───────────────────────────────────────────

    async def _fetch_newsletters(self, client: httpx.AsyncClient) -> list[TrendAlert]:
        alerts: list[TrendAlert] = []
        for newsletter_name, feed_url in _NEWSLETTER_FEEDS.items():
            try:
                r = await client.get(feed_url, timeout=15)
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.text)
                # Support both RSS <item> and Atom <entry>
                ns_atom = {"a": "http://www.w3.org/2005/Atom"}
                items = root.findall(".//item") or root.findall("a:entry", ns_atom)
                for item in items[:8]:
                    title_el  = item.find("title") or item.find("{http://www.w3.org/2005/Atom}title")
                    link_el   = item.find("link")  or item.find("{http://www.w3.org/2005/Atom}link")
                    desc_el   = item.find("description") or item.find("{http://www.w3.org/2005/Atom}summary")
                    pub_el    = item.find("pubDate") or item.find("{http://www.w3.org/2005/Atom}published")
                    title     = (title_el.text or "").strip() if title_el is not None else ""
                    link      = (link_el.text or link_el.get("href", "") if link_el is not None else "")
                    desc      = (desc_el.text or "").strip()[:300] if desc_el is not None else ""
                    pub_raw   = (pub_el.text or "")[:10] if pub_el is not None else ""
                    sig = self._sig(f"newsletter-{newsletter_name}", title)
                    if sig in self._seen or not title:
                        continue
                    score = self._score(title, desc, newsletter_name)
                    if score >= self._min_relevance:
                        alerts.append(TrendAlert(
                            source="newsletter",
                            title=f"[{newsletter_name}] {title[:100]}",
                            summary=desc,
                            url=link,
                            relevance_score=score,
                            published=pub_raw,
                            tags=["newsletter", newsletter_name.lower().replace(" ", "-"), "curated"],
                        ))
                        self._seen.add(sig)
            except Exception as exc:
                log.debug("TrendWatcher: newsletter %r error: %s", newsletter_name, exc)
        return alerts

    # ── Main fetch ────────────────────────────────────────────────────────────

    async def fetch(self) -> list[TrendAlert]:
        """Fetch all sources in parallel; return new alerts sorted by relevance."""
        log.info("TrendWatcher: starting fetch cycle (%d sources)", len(self._ALL_SOURCES))
        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = await asyncio.gather(
                self._fetch_arxiv(client),
                self._fetch_ollama_releases(client),
                self._fetch_hf_trending(client),
                self._fetch_github_trending(client),
                self._fetch_reddit(client),
                self._fetch_google_news(client),
                self._fetch_hackernews(client),
                self._fetch_nvidia(client),
                self._fetch_papers_with_code(client),
                self._fetch_newsletters(client),
                return_exceptions=True,
            )
        new_alerts: list[TrendAlert] = []
        for r in results:
            if isinstance(r, list):
                new_alerts.extend(r)
            elif isinstance(r, Exception):
                log.debug("TrendWatcher: a source raised: %s", r)

        new_alerts.sort(key=lambda a: a.relevance_score, reverse=True)
        self._alerts.extend(new_alerts)
        self._last_fetch  = time.time()
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
                        f"Evaluate if this is actionable for local-llm-server. "
                        f"For Ollama releases: update router/registry.py. "
                        f"For research techniques: create a GitHub issue. "
                        f"For Nvidia GPU features: evaluate TRT-LLM integration."
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
            "total_alerts":  len(self._alerts),
            "unique_seen":   len(self._seen),
            "fetch_count":   self._fetch_count,
            "last_fetch": (
                datetime.fromtimestamp(self._last_fetch, tz=timezone.utc).isoformat()
                if self._last_fetch else None
            ),
            "by_source": {
                s: sum(1 for a in self._alerts if a.source == s)
                for s in self._ALL_SOURCES
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
