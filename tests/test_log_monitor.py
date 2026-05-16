"""Tests for agent/log_monitor.py"""
from __future__ import annotations

import logging
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.log_monitor import (
    LogMonitor,
    _sig,
    get_log_monitor,
    set_log_monitor,
    COOLDOWN_SECONDS,
    IGNORED_LOGGERS,
)


def test_sig_is_deterministic():
    s1 = _sig("qwen-proxy", "Some error message")
    s2 = _sig("qwen-proxy", "Some error message")
    assert s1 == s2
    assert len(s1) == 16


def test_sig_differs_by_logger():
    s1 = _sig("logger-a", "Same message")
    s2 = _sig("logger-b", "Same message")
    assert s1 != s2


def test_monitor_attach_detach():
    monitor = LogMonitor()
    root = logging.getLogger()
    initial_count = len(root.handlers)

    monitor.attach()
    assert len(root.handlers) == initial_count + 1

    monitor.detach()
    assert len(root.handlers) == initial_count


def test_attach_idempotent():
    monitor = LogMonitor()
    root = logging.getLogger()
    initial_count = len(root.handlers)

    monitor.attach()
    monitor.attach()  # second call should be no-op
    assert len(root.handlers) == initial_count + 1

    monitor.detach()


def test_get_stats_not_attached():
    monitor = LogMonitor()
    stats = monitor.get_stats()
    assert stats["attached"] is False
    assert stats["tasks_created"] == 0


def test_get_stats_attached():
    monitor = LogMonitor()
    monitor.attach()
    stats = monitor.get_stats()
    assert stats["attached"] is True
    monitor.detach()


def test_cooldown_prevents_duplicate_tasks():
    monitor = LogMonitor()
    dispatched: list[str] = []

    with patch("agent.log_monitor._dispatch_async", side_effect=lambda t, d: dispatched.append(t)):
        monitor._on_log_error("some.module", "ERROR", "database connection failed")
        monitor._on_log_error("some.module", "ERROR", "database connection failed")  # duplicate

    assert len(dispatched) == 1


def test_cooldown_allows_different_errors():
    monitor = LogMonitor()
    dispatched: list[str] = []

    with patch("agent.log_monitor._dispatch_async", side_effect=lambda t, d: dispatched.append(t)):
        monitor._on_log_error("some.module", "ERROR", "error A")
        monitor._on_log_error("some.module", "ERROR", "error B")  # different message

    assert len(dispatched) == 2


def test_ignored_loggers_are_skipped():
    monitor = LogMonitor()
    dispatched: list[str] = []

    with patch("agent.log_monitor._dispatch_async", side_effect=lambda t, d: dispatched.append(t)):
        for logger_name in IGNORED_LOGGERS:
            monitor._on_log_error(logger_name, "ERROR", "some error from noisy logger")

    assert len(dispatched) == 0


def test_task_count_increments():
    monitor = LogMonitor()
    with patch("agent.log_monitor._dispatch_async"):
        monitor._on_log_error("my.module", "CRITICAL", "fatal error " + "A")
        monitor._on_log_error("my.module", "CRITICAL", "fatal error " + "B")
    assert monitor.get_stats()["tasks_created"] == 2


def test_singleton():
    orig = get_log_monitor()
    m = LogMonitor()
    set_log_monitor(m)
    assert get_log_monitor() is m
    set_log_monitor(orig)
