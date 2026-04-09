"""agent/browser.py — Browser Automation

Controls a real browser via Playwright so the agent can interact with
dynamic web pages: click buttons, fill forms, take screenshots, and read
rendered content — not just fetch raw HTML.

Requires: ``pip install playwright && playwright install chromium``

When Playwright is not installed the session runs in *stub mode*: all
actions return a failure result with a clear installation hint rather than
raising an exception.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("qwen-browser")

_INSTALL_HINT = (
    "Playwright is not installed. "
    "Run: pip install playwright && playwright install chromium"
)


@dataclass
class BrowserAction:
    action: str
    args: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    success: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "args": self.args,
            "result": self.result,
            "success": self.success,
        }


@dataclass
class PageState:
    url: str
    title: str
    content_preview: str   # first 500 chars of visible text

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content_preview": self.content_preview,
        }


class BrowserSession:
    """Async Playwright browser session.

    Usage::

        session = BrowserSession()
        await session.start()
        await session.navigate("https://example.com")
        await session.screenshot("/tmp/screen.png")
        state = await session.get_state()
        await session.stop()
    """

    def __init__(self) -> None:
        self._page: Any = None
        self._browser: Any = None
        self._pw: Any = None
        self._available = self._check_playwright()

    # ------------------------------------------------------------------
    # Capability check
    # ------------------------------------------------------------------

    def _check_playwright(self) -> bool:
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            log.info("playwright not installed — BrowserSession running in stub mode")
            return False

    @property
    def available(self) -> bool:
        """True if Playwright is installed and ready to use."""
        return self._available

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, *, headless: bool = True) -> None:
        if not self._available:
            log.warning(_INSTALL_HINT)
            return
        from playwright.async_api import async_playwright  # type: ignore[import]
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=headless)
        self._page = await self._browser.new_page()
        log.info("Browser session started (headless=%s)", headless)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._page = self._browser = self._pw = None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def navigate(self, url: str) -> BrowserAction:
        if not self._page:
            return BrowserAction("navigate", {"url": url}, _not_started(), False)
        try:
            await self._page.goto(url)
            title = await self._page.title()
            return BrowserAction("navigate", {"url": url}, f"Navigated to: {title}")
        except Exception as exc:
            return BrowserAction("navigate", {"url": url}, str(exc), False)

    async def click(self, selector: str) -> BrowserAction:
        if not self._page:
            return BrowserAction("click", {"selector": selector}, _not_started(), False)
        try:
            await self._page.click(selector)
            return BrowserAction("click", {"selector": selector}, "clicked")
        except Exception as exc:
            return BrowserAction("click", {"selector": selector}, str(exc), False)

    async def fill(self, selector: str, value: str) -> BrowserAction:
        if not self._page:
            return BrowserAction("fill", {"selector": selector, "value": value}, _not_started(), False)
        try:
            await self._page.fill(selector, value)
            return BrowserAction("fill", {"selector": selector, "value": value}, "filled")
        except Exception as exc:
            return BrowserAction("fill", {"selector": selector, "value": value}, str(exc), False)

    async def screenshot(self, path: str) -> BrowserAction:
        if not self._page:
            return BrowserAction("screenshot", {"path": path}, _not_started(), False)
        try:
            await self._page.screenshot(path=path)
            return BrowserAction("screenshot", {"path": path}, f"saved to {path}")
        except Exception as exc:
            return BrowserAction("screenshot", {"path": path}, str(exc), False)

    async def evaluate(self, expression: str) -> BrowserAction:
        """Evaluate a JavaScript expression in the page context."""
        if not self._page:
            return BrowserAction("evaluate", {"expression": expression}, _not_started(), False)
        try:
            result = await self._page.evaluate(expression)
            return BrowserAction("evaluate", {"expression": expression}, str(result))
        except Exception as exc:
            return BrowserAction("evaluate", {"expression": expression}, str(exc), False)

    async def get_state(self) -> PageState | None:
        """Return a summary of the current page state."""
        if not self._page:
            return None
        try:
            url = self._page.url
            title = await self._page.title()
            text = await self._page.evaluate("document.body?.innerText || ''")
            return PageState(url=url, title=title, content_preview=str(text)[:500])
        except Exception:
            return None


def _not_started() -> str:
    return "Browser not started. Call await session.start() first."
