"""
Multi-strategy URL content fetcher for process-quick-note workflow.

Exit codes:
  0 — success, content written to /tmp/note_content.txt
  2 — all strategies exhausted, URL inaccessible
  1 — bad args / unexpected error
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request

TARGET = sys.argv[1] if len(sys.argv) > 1 else ""
OUT_FILE = "/tmp/note_content.txt"  # nosec: B108
MIN_CHARS = 500

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str, timeout: int = 30) -> tuple[str | None, str, object]:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None, url, f"unsupported scheme: {parsed.scheme}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec: B310
            return r.read().decode("utf-8", errors="replace"), r.geturl(), r.status
    except Exception as exc:
        return None, url, str(exc)


def strip_html(html: str) -> str:
    text = re.sub(
        r"<(script|style|nav|footer|header)[^>]*>.*?</(script|style|nav|footer|header)>",
        " ", html, flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())


def extract_real_url(html: str) -> str | None:
    for pat in [
        r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:url["\']',
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\'][^;]+;\s*url=([^"\']+)["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if candidate.startswith("http"):
                return candidate
    return None


def meaningful(text: str) -> bool:
    return len(text) >= MIN_CHARS


def main() -> None:
    if not TARGET:
        print("ERROR: no URL argument", file=sys.stderr)
        sys.exit(1)

    html: str | None = None
    final_url = TARGET
    status: object = None

    # Strategy 1 — direct fetch
    print(f"[fetch] Strategy 1 — direct: {TARGET}")
    html, final_url, status = fetch(TARGET)
    text = strip_html(html) if html else ""

    # Strategy 2 — follow og:url / canonical (redirect-wrapper pages)
    if html and not meaningful(text):
        real = extract_real_url(html)
        if real and real != TARGET:
            print(f"[fetch] Strategy 2 — resolved canonical URL: {real}")
            html2, final_url2, status2 = fetch(real)
            text2 = strip_html(html2) if html2 else ""
            if meaningful(text2):
                html, final_url, status, text = html2, final_url2, status2, text2

    # Strategy 3 — Jina AI Reader (renders JavaScript; works for SPAs, X.com, etc.)
    if not meaningful(text):
        jina_url = "https://r.jina.ai/" + TARGET
        print(f"[fetch] Strategy 3 — Jina AI Reader: {jina_url}")
        html3, final_url3, status3 = fetch(jina_url, timeout=45)
        if html3:
            text3 = strip_html(html3) if "<html" in html3.lower() else html3
            if meaningful(text3):
                html, final_url, status, text = html3, final_url3, status3, text3

    # Strategy 4 — Nitter mirror (x.com / twitter.com only)
    if not meaningful(text) and re.search(r"https?://(x|twitter)\.com", TARGET):
        nitter = re.sub(r"https?://(x|twitter)\.com", "https://nitter.net", TARGET)
        print(f"[fetch] Strategy 4 — Nitter: {nitter}")
        html4, final_url4, status4 = fetch(nitter)
        text4 = strip_html(html4) if html4 else ""
        if meaningful(text4):
            html, final_url, status, text = html4, final_url4, status4, text4

    # Strategy 5 — Google Cache
    if not meaningful(text):
        cache_url = (
            "https://webcache.googleusercontent.com/search?q=cache:"
            + urllib.parse.quote(TARGET, safe="")
        )
        print(f"[fetch] Strategy 5 — Google Cache: {cache_url}")
        html, final_url, status = fetch(cache_url)
        text = strip_html(html) if html else ""

    # Strategy 6 — Wayback Machine
    if not meaningful(text):
        wb_url = "https://web.archive.org/web/" + urllib.parse.quote(TARGET, safe="")
        print(f"[fetch] Strategy 6 — Wayback Machine: {wb_url}")
        html, final_url, status = fetch(wb_url)
        text = strip_html(html) if html else ""

    if not meaningful(text):
        print(
            f"ERROR: Could not retrieve meaningful content from {TARGET} "
            f"(got {len(text)} chars after all fallbacks). Last status: {status}",
            file=sys.stderr,
        )
        sys.exit(2)

    with open(OUT_FILE, "w") as f:  # nosec: B603
        f.write(f"Source URL: {TARGET}\nFetched from: {final_url}\n\n{text[:6000]}")
    print(f"[fetch] OK — {len(text)} chars from {final_url}")


if __name__ == "__main__":
    main()
