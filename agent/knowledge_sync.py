"""agent/knowledge_sync.py — Wiki + Sources knowledge ingestion pipeline.

Bridges internet-fetched trend intelligence into the local RAG system:

  • fetch_and_store(url, title, tags) — ingest any URL into Sources so it is
    available for RAG-augmented responses.
  • sync_trends() — run after each TrendWatcher.fetch(); pushes high-relevance
    trend URLs to Sources and creates a dated Wiki digest page.
  • run_weekly_sync() — standalone cron entry-point called by the scheduler.

All HTTP calls go to the proxy itself (PROXY_BASE_URL) using the internal API
key so no external auth credentials are needed beyond what agency.py already
uses.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger("qwen-proxy")

PROXY_BASE_URL: str = os.environ.get("AGENCY_PROXY_URL", "http://localhost:8000")

# Minimum relevance score to auto-ingest a trend into Sources.
MIN_INGEST_RELEVANCE: float = float(os.environ.get("KNOWLEDGE_MIN_RELEVANCE", "0.45"))

# Max concurrent ingest requests per sync run.
_MAX_CONCURRENT: int = 4

# Timeout for each Sources/Wiki API call (seconds).
_TIMEOUT: float = 30.0


# ── helpers ───────────────────────────────────────────────────────────────────

def _api_key() -> str:
    return (
        os.environ.get("PROXY_API_KEY")
        or os.environ.get("ADMIN_TOKEN")
        or "knowledge-sync-internal"
    )


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_api_key()}"}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


# ── core API helpers ──────────────────────────────────────────────────────────

async def fetch_and_store(
    url: str,
    title: str,
    tags: list[str] | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Ingest a URL into the Sources database so it becomes RAG-searchable.

    Returns the Sources API response dict, or an error dict on failure.
    Callers may pass an existing AsyncClient to reuse the connection pool.
    """
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True)
    try:
        data: dict[str, Any] = {"url": url, "title": title}
        if tags:
            data["tags"] = ",".join(tags)
        resp = await client.post(
            f"{PROXY_BASE_URL}/api/sources/ingest",
            data=data,
            headers=_auth_headers(),
        )
        if resp.status_code in (200, 201):
            log.info("knowledge_sync: ingested source url=%s title=%r", url, title)
            return resp.json()
        else:
            log.warning(
                "knowledge_sync: source ingest failed url=%s status=%d body=%s",
                url, resp.status_code, resp.text[:200],
            )
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as exc:
        log.warning("knowledge_sync: source ingest error url=%s err=%s", url, exc)
        return {"error": str(exc)}
    finally:
        if own_client:
            await client.aclose()


async def create_wiki_page(
    title: str,
    content: str,
    tags: list[str] | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Create (or silently skip if duplicate title) a Wiki page."""
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True)
    try:
        payload: dict[str, Any] = {"title": title, "content": content}
        if tags:
            payload["tags"] = tags
        resp = await client.post(
            f"{PROXY_BASE_URL}/api/wiki/pages",
            json=payload,
            headers=_auth_headers(),
        )
        if resp.status_code in (200, 201):
            log.info("knowledge_sync: wiki page created title=%r", title)
            return resp.json()
        elif resp.status_code == 409:
            log.debug("knowledge_sync: wiki page already exists title=%r", title)
            return {"skipped": True, "title": title}
        else:
            log.warning(
                "knowledge_sync: wiki create failed title=%r status=%d body=%s",
                title, resp.status_code, resp.text[:200],
            )
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as exc:
        log.warning("knowledge_sync: wiki create error title=%r err=%s", title, exc)
        return {"error": str(exc)}
    finally:
        if own_client:
            await client.aclose()


# ── digest builder ────────────────────────────────────────────────────────────

def _build_digest_markdown(alerts: list[dict[str, Any]], week_label: str) -> str:
    """Render a markdown digest from a list of TrendAlert dicts."""
    lines = [
        f"# AI Trend Digest — {week_label}",
        "",
        f"*Auto-generated by KnowledgeSync on {_now_iso()}.*",
        "",
        "## High-relevance findings",
        "",
    ]
    high = [a for a in alerts if a.get("relevance_score", 0) >= MIN_INGEST_RELEVANCE]
    low  = [a for a in alerts if a.get("relevance_score", 0) < MIN_INGEST_RELEVANCE]

    if not high:
        lines.append("*No high-relevance findings this period.*")
    else:
        for alert in sorted(high, key=lambda a: a.get("relevance_score", 0), reverse=True):
            score_pct = int(alert.get("relevance_score", 0) * 100)
            lines += [
                f"### [{alert.get('title', 'Untitled')}]({alert.get('url', '')})",
                f"**Source:** {alert.get('source', '?')}  "
                f"**Relevance:** {score_pct}%  "
                f"**Published:** {alert.get('published', '?')}",
                "",
                alert.get("summary", ""),
                "",
            ]

    if low:
        lines += [
            "## Lower-relevance signals",
            "",
        ]
        for alert in low[:10]:
            lines.append(
                f"- [{alert.get('title', 'Untitled')}]({alert.get('url', '')}) "
                f"({alert.get('source', '?')})"
            )
        lines.append("")

    lines += [
        "---",
        "*This page is updated automatically. Sources are indexed for RAG search.*",
    ]
    return "\n".join(lines)


# ── main sync entry-points ────────────────────────────────────────────────────

@dataclass
class SyncResult:
    ingested: int = 0
    skipped: int = 0
    errors: int = 0
    wiki_created: bool = False
    wiki_title: str = ""
    details: list[dict[str, Any]] = field(default_factory=list)


async def sync_trends(alerts: list[dict[str, Any]] | None = None) -> SyncResult:
    """Push trend alerts into Sources + create a Wiki digest page.

    If *alerts* is None, uses whatever is cached in the TrendWatcher singleton.
    """
    from agent.trend_watcher import get_trend_watcher

    if alerts is None:
        watcher = get_trend_watcher()
        if watcher is None:
            log.warning("knowledge_sync: TrendWatcher not initialised — nothing to sync")
            return SyncResult()
        alerts = watcher.get_alerts(limit=50)

    result = SyncResult()
    if not alerts:
        log.info("knowledge_sync: no alerts to sync")
        return result

    # ── ingest high-relevance URLs into Sources ──────────────────────────────
    to_ingest = [a for a in alerts if a.get("relevance_score", 0) >= MIN_INGEST_RELEVANCE and a.get("url")]

    import asyncio

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        # Batch with limited concurrency
        sem = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _ingest_one(alert: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                tags = ["ai-trend", alert.get("source", "unknown")]
                tags.extend(alert.get("tags", []))
                resp = await fetch_and_store(
                    url=alert["url"],
                    title=alert.get("title", "Untitled trend"),
                    tags=list(dict.fromkeys(tags)),  # deduplicate, preserve order
                    client=client,
                )
                return {"alert_url": alert["url"], "resp": resp}

        tasks = [_ingest_one(a) for a in to_ingest]
        ingest_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in ingest_results:
            if isinstance(r, Exception):
                result.errors += 1
                result.details.append({"error": str(r)})
            elif isinstance(r, dict):
                resp = r.get("resp", {})
                if "error" in resp:
                    result.errors += 1
                elif resp.get("skipped"):
                    result.skipped += 1
                else:
                    result.ingested += 1
                result.details.append(r)

        # ── create Wiki digest page ──────────────────────────────────────────
        week_label = time.strftime("Week of %Y-%m-%d", time.gmtime())
        wiki_title = f"AI Trend Digest — {week_label}"
        digest_md = _build_digest_markdown(alerts, week_label)

        wiki_resp = await create_wiki_page(
            title=wiki_title,
            content=digest_md,
            tags=["ai-trends", "auto-generated", "weekly-digest"],
            client=client,
        )
        result.wiki_created = "id" in wiki_resp or "page" in wiki_resp
        result.wiki_title = wiki_title

    log.info(
        "knowledge_sync: sync_trends done ingested=%d skipped=%d errors=%d wiki=%s",
        result.ingested, result.skipped, result.errors, result.wiki_title,
    )
    return result


async def run_weekly_sync() -> SyncResult:
    """Cron entry-point: fetch fresh trends then sync everything to Wiki+Sources."""
    from agent.trend_watcher import get_trend_watcher

    watcher = get_trend_watcher()
    if watcher is not None:
        try:
            await watcher.fetch()
        except Exception as exc:
            log.warning("knowledge_sync: trend fetch failed before sync: %s", exc)

    return await sync_trends()


# ── singleton ─────────────────────────────────────────────────────────────────

_instance: "KnowledgeSync | None" = None


class KnowledgeSync:
    """Lightweight handle used as a singleton so proxy.py can reference it."""

    async def sync(self, alerts: list[dict[str, Any]] | None = None) -> SyncResult:
        return await sync_trends(alerts)

    async def weekly(self) -> SyncResult:
        return await run_weekly_sync()

    async def ingest_url(self, url: str, title: str, tags: list[str] | None = None) -> dict[str, Any]:
        return await fetch_and_store(url, title, tags)

    async def create_page(self, title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        return await create_wiki_page(title, content, tags)


def get_knowledge_sync() -> KnowledgeSync | None:
    return _instance


def set_knowledge_sync(ks: KnowledgeSync) -> None:
    global _instance
    _instance = ks
