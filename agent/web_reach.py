"""agent/web_reach.py — Web Reach: zero-key internet access for agents.

Gives every agent read access to the open web without any new secret, API key,
or external CLI dependency — general web pages, YouTube transcripts, web
search, and RSS/Atom feeds. Modelled on the "ordered backend + health check"
idea from github.com/Panniantong/Agent-Reach, but implemented natively against
this repo's own stack (httpx + stdlib) rather than shelling out to third-party
CLI tools (twitter-cli, bili-cli, gh, mcporter, ...), which this repo's
containers don't ship and which would need per-platform credentials.

Login-gated platforms (Twitter/X, Reddit, Facebook, Instagram, LinkedIn,
Xiaohongshu) are out of scope: the constitution forbids `os.environ.get()`
outside config modules and half-finished implementations, and those all need
credentials this repo has no secret slot for. GitHub is already covered by
the existing `github_*` tools in `agent/loop.py` — no need to duplicate.

Single source of truth for the two hardest pieces of this — the
multi-strategy page-fetch fallback chain and YouTube caption extraction —
stays in `.github/scripts/fetch_url.py` / `video_transcript.py`, already
proven and unit-tested (`tests/test_video_transcript.py`). This module loads
them dynamically by file path (the same technique that test file already
uses) instead of re-implementing that logic, per the "never duplicate logic"
rule.
"""
from __future__ import annotations

import ipaddress
import importlib.util
import logging
import re
import socket
import time
import urllib.parse
import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx

log = logging.getLogger("qwen-proxy")

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / ".github" / "scripts"

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 20.0
MAX_CHARS = 6000

# Every content-bearing result from this module carries this marker so any consumer
# — not only the Executor prompt fence — can tell that the payload is external text
# fetched from an attacker-influenceable source. It is DATA, never instructions
# (rule 14 covers where it may be fetched from; this covers how it must be treated
# once fetched). Defence-in-depth alongside the untrusted-observation fence in
# agent/prompts.py::build_tool_prompt.
UNTRUSTED_EXTERNAL = "untrusted-external"


def unsafe_target_reason(url: str) -> str | None:
    """Return why *url* must not be fetched, or None if it's a safe public target.

    These tools take URLs chosen by an LLM — including URLs quoted inside
    content the LLM itself fetched or read from an issue/PR body, i.e. an
    attacker-controlled source in the classic SSRF sense. Unlike the
    CI-only `.github/scripts/fetch_url.py` (throwaway GitHub Actions runner,
    no internal network to reach), this module runs inside the production
    backend process, which does sit on a network with a database, an admin
    API, and cloud metadata endpoints. Every entry point here must reject
    loopback/private/link-local/reserved targets before making a request.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return "malformed URL"
    if parsed.scheme not in ("http", "https"):
        return f"unsupported scheme: {parsed.scheme!r}"
    host = parsed.hostname
    if not host:
        return "URL has no host"
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        return f"could not resolve host: {exc}"
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return f"host resolves to a non-public address ({addr})"
    return _egress_policy_reason(host)


def _egress_policy_reason(host: str) -> str | None:
    """Return why governance policy blocks *host*, or None.

    Runs strictly *after* the SSRF checks above and never replaces them. The
    two answer different questions: the SSRF check asks "could this reach
    something private?" and is unconditional; this asks "is this destination
    approved for agents?" and is policy-driven. Collapsing them would let a
    permissive policy switch off the SSRF guard, which must never be
    possible — so this function is only ever consulted once the address checks
    have already passed.

    Returns None unless governance is enabled *and* the policy is in
    ``enforce`` mode, so the shipped observe-mode default leaves Web Reach's
    behaviour exactly as it was. The would-block signal is still recorded in
    the audit trail by the policy engine, which is how an operator sees what
    an egress allow-list would have caught before turning it on.
    """
    try:
        from packages.governance.enforcement import governance_enabled

        if not governance_enabled():
            return None
        from packages.governance.policy import Decision, Surface, get_policy_engine

        decision = get_policy_engine().evaluate(Surface.NETWORK, host)
        if decision.effective is Decision.DENY:
            return f"blocked by egress policy: {decision.reason}"
    except Exception as exc:  # noqa: BLE001 - policy must never break web reach
        log.debug("Egress policy check skipped for %s: %s", host, exc)
    return None


def _load_script_module(name: str) -> ModuleType | None:
    """Dynamically load a pure-stdlib helper module from .github/scripts/.

    Returns None if the file is missing or fails to import — callers must
    treat that as "strategy unavailable" and fall back, never raise.
    """
    path = _SCRIPTS_DIR / f"{name}.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(f"_web_reach_{name}", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        log.warning("web_reach: could not load %s: %s", name, exc)
        return None


class WebReach:
    """Zero-key internet access: pages, YouTube transcripts, search, RSS.

    Every public method returns a plain dict and never raises — callers
    (the agent tool-call loop) get a structured failure instead of an
    exception, matching the fail-soft style of ``agent/browser.py``.
    """

    def __init__(self, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self._fetch_url_mod: ModuleType | None | bool = False  # False = not attempted yet
        self._video_mod: ModuleType | None | bool = False

    # ------------------------------------------------------------------
    # Lazy-loaded delegate modules
    # ------------------------------------------------------------------

    def _fetch_mod(self) -> ModuleType | None:
        if self._fetch_url_mod is False:
            self._fetch_url_mod = _load_script_module("fetch_url")
        return self._fetch_url_mod  # type: ignore[return-value]

    def _video(self) -> ModuleType | None:
        if self._video_mod is False:
            self._video_mod = _load_script_module("video_transcript")
        return self._video_mod  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Web pages
    # ------------------------------------------------------------------

    def fetch_page(self, url: str) -> dict[str, Any]:
        """Read a web page as plain text, following the same fallback chain
        (direct -> canonical -> Jina AI Reader -> Nitter -> Wayback) proven
        in the quick-note pipeline. Tries a YouTube transcript first when the
        URL is a video — a rendered watch page has no spoken content.
        """
        reason = unsafe_target_reason(url)
        if reason:
            return {"ok": False, "url": url, "error": f"refused: {reason}"}

        video = self._video()
        if video is not None:
            try:
                if video.is_video_url(url):
                    transcript = video.fetch_transcript(url, timeout=int(self.timeout))
                    if transcript:
                        return {
                            "ok": True,
                            "url": url,
                            "final_url": url,
                            "source": "youtube_transcript",
                            "trust": UNTRUSTED_EXTERNAL,
                            "text": transcript[:MAX_CHARS],
                        }
            except Exception as exc:  # noqa: BLE001 - fall through to page fetch
                log.debug("web_reach: transcript strategy failed for %s: %s", url, exc)

        fetch_mod = self._fetch_mod()
        if fetch_mod is not None:
            return self._fetch_via_script(fetch_mod, url)
        return self._fetch_direct(url)

    def _fetch_via_script(self, fetch_mod: ModuleType, url: str) -> dict[str, Any]:
        # `url` and, below, `real` (the canonical/og:url target) are the only
        # attacker-influenced hosts in this chain — jina/nitter/wayback are
        # fixed, known-public hosts. Both are pre-validated. fetch_mod.fetch()
        # itself follows redirects via urllib without re-validating each hop
        # (unlike self._safe_get); a redirect-based SSRF bypass on `url` or
        # `real` is a bounded, accepted residual gap of reusing that shared,
        # tested CI script rather than forking its redirect handling here.
        html, final_url, status = fetch_mod.fetch(url, timeout=int(self.timeout))
        text = fetch_mod.strip_html(html) if html else ""
        source = "direct"

        if html and not fetch_mod.meaningful(text):
            real = fetch_mod.extract_real_url(html)
            if real and real != url and unsafe_target_reason(real) is None:
                html2, final_url2, status2 = fetch_mod.fetch(real, timeout=int(self.timeout))
                text2 = fetch_mod.strip_html(html2) if html2 else ""
                if fetch_mod.meaningful(text2):
                    html, final_url, status, text = html2, final_url2, status2, text2
                    source = "canonical"

        if not fetch_mod.meaningful(text):
            jina_url = "https://r.jina.ai/" + url
            html3, final_url3, status3 = fetch_mod.fetch(jina_url, timeout=int(self.timeout) + 15)
            if html3:
                text3 = fetch_mod.strip_html(html3) if "<html" in html3.lower() else html3
                if fetch_mod.meaningful(text3):
                    html, final_url, status, text = html3, final_url3, status3, text3
                    source = "jina_reader"

        if not fetch_mod.meaningful(text) and re.search(r"https?://(x|twitter)\.com", url):
            nitter = re.sub(r"https?://(x|twitter)\.com", "https://nitter.net", url)
            html4, final_url4, status4 = fetch_mod.fetch(nitter, timeout=int(self.timeout))
            text4 = fetch_mod.strip_html(html4) if html4 else ""
            if fetch_mod.meaningful(text4):
                html, final_url, status, text = html4, final_url4, status4, text4
                source = "nitter"

        if not fetch_mod.meaningful(text):
            wb_url = "https://web.archive.org/web/" + urllib.parse.quote(url, safe="")
            html5, final_url5, status5 = fetch_mod.fetch(wb_url, timeout=int(self.timeout))
            text5 = fetch_mod.strip_html(html5) if html5 else ""
            if fetch_mod.meaningful(text5):
                html, final_url, status, text = html5, final_url5, status5, text5
                source = "wayback"

        if not fetch_mod.meaningful(text):
            return {
                "ok": False,
                "url": url,
                "error": f"could not retrieve meaningful content (last status: {status})",
            }
        return {
            "ok": True,
            "url": url,
            "final_url": final_url,
            "source": source,
            "trust": UNTRUSTED_EXTERNAL,
            "text": text[:MAX_CHARS],
        }

    def _safe_get(self, url: str, *, max_redirects: int = 5) -> httpx.Response:
        """GET *url*, re-validating every redirect hop against
        ``unsafe_target_reason`` — a server that 302s from a validated public
        host to an internal address is a standard SSRF bypass that plain
        ``follow_redirects=True`` would walk straight through."""
        reason = unsafe_target_reason(url)
        if reason:
            raise ValueError(f"refused: {reason}")
        with httpx.Client(headers={"User-Agent": _UA}, timeout=self.timeout, follow_redirects=False) as client:
            current = url
            for _ in range(max_redirects + 1):
                resp = client.get(current)
                if resp.is_redirect:
                    raw_nxt = str(resp.next_request.url) if resp.next_request else resp.headers.get("location", "")
                    nxt = urllib.parse.urljoin(current, raw_nxt)
                    reason = unsafe_target_reason(nxt)
                    if reason:
                        raise ValueError(f"refused redirect target ({nxt}): {reason}")
                    current = nxt
                    continue
                resp.raise_for_status()
                return resp
        raise ValueError("too many redirects")

    def _fetch_direct(self, url: str) -> dict[str, Any]:
        """httpx-only fallback used when the .github/scripts helpers can't be
        loaded (e.g. a deploy image that excludes that directory)."""
        try:
            resp = self._safe_get(url)
        except Exception as exc:
            return {"ok": False, "url": url, "error": str(exc)}

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = re.sub(r"\n{3,}", "\n\n", soup.get_text(separator="\n").strip())
        if len(text) < 200:
            return {"ok": False, "url": url, "error": "no meaningful content extracted"}
        return {
            "ok": True,
            "url": url,
            "final_url": str(resp.url),
            "source": "httpx_direct",
            "trust": UNTRUSTED_EXTERNAL,
            "text": text[:MAX_CHARS],
        }

    # ------------------------------------------------------------------
    # YouTube transcripts (also reachable directly, not only via fetch_page)
    # ------------------------------------------------------------------

    def youtube_transcript(self, url: str) -> dict[str, Any]:
        reason = unsafe_target_reason(url)
        if reason:
            return {"ok": False, "url": url, "error": f"refused: {reason}"}
        video = self._video()
        if video is None:
            return {"ok": False, "url": url, "error": "video_transcript backend unavailable"}
        if not video.is_video_url(url):
            return {"ok": False, "url": url, "error": "not a recognised YouTube URL"}
        transcript = video.fetch_transcript(url, timeout=int(self.timeout))
        if not transcript:
            return {"ok": False, "url": url, "error": "no captions available for this video"}
        return {"ok": True, "url": url, "trust": UNTRUSTED_EXTERNAL, "text": transcript[:MAX_CHARS]}

    # ------------------------------------------------------------------
    # Web search — DuckDuckGo HTML (no API key)
    # ------------------------------------------------------------------

    def search_web(self, query: str, limit: int = 8) -> dict[str, Any]:
        """Free-text web search with no API key, via DuckDuckGo's HTML-only
        endpoint. Best-effort: DuckDuckGo can change markup at any time —
        ``doctor()`` reports when this backend stops parsing."""
        if not query.strip():
            return {"ok": False, "query": query, "error": "empty query"}
        try:
            resp = httpx.get(
                "https://lite.duckduckgo.com/lite/",
                params={"q": query},
                headers={"User-Agent": _UA},
                timeout=self.timeout,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception as exc:
            return {"ok": False, "query": query, "error": str(exc)}

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict[str, str]] = []
        for link in soup.select("a.result-link"):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not href or not title:
                continue
            results.append({"title": title, "url": href})
            if len(results) >= limit:
                break

        if not results:
            return {"ok": False, "query": query, "error": "no results parsed (backend markup may have changed)"}
        return {"ok": True, "query": query, "trust": UNTRUSTED_EXTERNAL, "results": results}

    # ------------------------------------------------------------------
    # RSS / Atom feeds — stdlib XML, no new dependency
    # ------------------------------------------------------------------

    def fetch_rss(self, url: str, limit: int = 10) -> dict[str, Any]:
        try:
            resp = self._safe_get(url)
        except Exception as exc:
            return {"ok": False, "url": url, "error": str(exc)}

        try:
            # Same stdlib-XML approach already used for RSS/Atom parsing
            # throughout agent/trend_watcher.py (see its `# nosec B314` sites).
            root = ET.fromstring(resp.content)  # nosec B314
        except ET.ParseError as exc:
            return {"ok": False, "url": url, "error": f"not a well-formed feed: {exc}"}

        items = root.findall(".//item")   # RSS 2.0
        is_atom = False
        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//atom:entry", ns)
            is_atom = True

        entries: list[dict[str, str]] = []
        for item in items[:limit]:
            if is_atom:
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                title = (item.findtext("atom:title", default="", namespaces=ns) or "").strip()
                link_el = item.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
            else:
                title = (item.findtext("title", default="") or "").strip()
                link = (item.findtext("link", default="") or "").strip()
            if title or link:
                entries.append({"title": title, "url": link})

        if not entries:
            return {"ok": False, "url": url, "error": "feed parsed but contained no entries"}
        return {"ok": True, "url": url, "trust": UNTRUSTED_EXTERNAL, "entries": entries}

    # ------------------------------------------------------------------
    # Diagnostics — mirrors `agent-reach doctor`
    # ------------------------------------------------------------------

    def doctor(self) -> dict[str, Any]:
        """Health-check each backend with a short timeout. Never raises."""
        checks: dict[str, dict[str, Any]] = {}
        short = min(self.timeout, 8.0)

        def _ping(name: str, url: str) -> None:
            start = time.monotonic()
            try:
                r = httpx.get(url, headers={"User-Agent": _UA}, timeout=short, follow_redirects=True)
                checks[name] = {
                    "ok": r.status_code < 500,
                    "status_code": r.status_code,
                    "latency_ms": round((time.monotonic() - start) * 1000),
                }
            except Exception as exc:
                checks[name] = {"ok": False, "error": str(exc)}

        _ping("direct_fetch", "https://example.com")
        _ping("jina_reader", "https://r.jina.ai/https://example.com")
        _ping("duckduckgo_search", "https://lite.duckduckgo.com/lite/?q=test")
        _ping("youtube", "https://www.youtube.com")

        checks["fetch_url_script"] = {"ok": self._fetch_mod() is not None}
        checks["video_transcript_script"] = {"ok": self._video() is not None}

        return {
            "ok": all(c.get("ok") for c in checks.values()),
            "backends": checks,
        }


_web_reach: WebReach | None = None


def get_web_reach() -> WebReach:
    """Module-level singleton, mirroring `agent.capability_registry.get_tool_registry`."""
    global _web_reach
    if _web_reach is None:
        _web_reach = WebReach()
    return _web_reach
