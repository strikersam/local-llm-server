"""Tests for agent/browser.py — Browser Automation (stub-mode tests)."""
import asyncio

import pytest

from agent.browser import BrowserSession, PageState


def test_session_created():
    session = BrowserSession()
    assert isinstance(session.available, bool)


def test_stub_mode_navigate():
    """When Playwright is not installed, navigate returns a failed BrowserAction."""
    session = BrowserSession()
    if session.available:
        pytest.skip("Playwright is installed; stub-mode test not applicable")
    result = asyncio.run(session.navigate("https://example.com"))
    assert result.success is False
    assert "not started" in result.result.lower()


def test_stub_mode_click():
    session = BrowserSession()
    if session.available:
        pytest.skip("Playwright installed")
    result = asyncio.run(session.click("#btn"))
    assert result.success is False


def test_stub_mode_fill():
    session = BrowserSession()
    if session.available:
        pytest.skip("Playwright installed")
    result = asyncio.run(session.fill("#inp", "value"))
    assert result.success is False


def test_stub_mode_screenshot():
    session = BrowserSession()
    if session.available:
        pytest.skip("Playwright installed")
    result = asyncio.run(session.screenshot("/tmp/snap.png"))
    assert result.success is False


def test_stub_mode_get_state():
    session = BrowserSession()
    if session.available:
        pytest.skip("Playwright installed")
    result = asyncio.run(session.get_state())
    assert result is None


def test_browser_action_as_dict():
    from agent.browser import BrowserAction
    a = BrowserAction(action="navigate", args={"url": "http://x"}, result="ok", success=True)
    d = a.as_dict()
    assert d["action"] == "navigate"
    assert d["success"] is True
