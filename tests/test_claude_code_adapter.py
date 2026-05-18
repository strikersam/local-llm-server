"""Tests for runtimes/adapters/claude_code.py"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from runtimes.adapters.claude_code import ClaudeCodeAdapter
from runtimes.base import RuntimeTier, IntegrationMode, RuntimeCapability


@pytest.fixture
def adapter():
    return ClaudeCodeAdapter()


def test_adapter_metadata(adapter: ClaudeCodeAdapter):
    assert adapter.RUNTIME_ID == "claude_code"
    assert adapter.TIER == RuntimeTier.FIRST_CLASS
    assert adapter.INTEGRATION_MODE == IntegrationMode.EXTERNAL_PROCESS
    assert RuntimeCapability.CODE_GENERATION in adapter.CAPABILITIES
    assert RuntimeCapability.AUTONOMOUS_LOOP in adapter.CAPABILITIES
    assert RuntimeCapability.MULTI_FILE_EDIT in adapter.CAPABILITIES


@pytest.mark.asyncio
async def test_health_check_binary_not_found(adapter: ClaudeCodeAdapter, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    health = await adapter.health_check()
    assert health.available is False
    assert "not found" in (health.error or "").lower()


@pytest.mark.asyncio
async def test_health_check_no_api_key(adapter: ClaudeCodeAdapter, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    health = await adapter.health_check()
    assert health.available is False
    assert "ANTHROPIC_API_KEY" in (health.error or "")


@pytest.mark.asyncio
async def test_health_check_success(adapter: ClaudeCodeAdapter, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"1.0.0\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", new_callable=AsyncMock, return_value=(b"1.0.0\n", b"")):
            health = await adapter.health_check()

    assert health.runtime_id == "claude_code"


@pytest.mark.asyncio
async def test_execute_binary_not_found(adapter: ClaudeCodeAdapter, monkeypatch) -> None:
    from runtimes.base import RuntimeUnavailableError, TaskSpec
    monkeypatch.setattr("shutil.which", lambda _: None)
    spec = TaskSpec(task_id="t1", instruction="do something", task_type="code_generation")
    with pytest.raises(RuntimeUnavailableError):
        await adapter.execute(spec)


@pytest.mark.asyncio
async def test_execute_no_api_key(adapter: ClaudeCodeAdapter, monkeypatch) -> None:
    from runtimes.base import RuntimeUnavailableError, TaskSpec
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    spec = TaskSpec(task_id="t1", instruction="do something", task_type="code_generation")
    with pytest.raises(RuntimeUnavailableError):
        await adapter.execute(spec)


@pytest.mark.asyncio
async def test_execute_success(adapter: ClaudeCodeAdapter, monkeypatch) -> None:
    from runtimes.base import TaskSpec
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"Task completed successfully.\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", new_callable=AsyncMock,
                   return_value=(b"Task completed successfully.\n", b"")):
            spec = TaskSpec(task_id="t2", instruction="Fix the bug", task_type="code_generation")
            result = await adapter.execute(spec)

    assert result.runtime_id == "claude_code"
    assert result.success is True
    assert "completed" in result.output


@pytest.mark.asyncio
async def test_execute_failure_returns_result(adapter: ClaudeCodeAdapter, monkeypatch) -> None:
    from runtimes.base import TaskSpec
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"Error: could not complete task\n"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", new_callable=AsyncMock,
                   return_value=(b"", b"Error: could not complete task\n")):
            spec = TaskSpec(task_id="t3", instruction="Do something", task_type="code_generation")
            result = await adapter.execute(spec)

    assert result.success is False
    assert result.metadata.get("exit_code") == 1


def test_required_dependencies_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    adapter = ClaudeCodeAdapter()
    deps = adapter.required_dependencies()
    dep_names = [d.name for d in deps]
    assert "ANTHROPIC_API_KEY" in dep_names


def test_required_dependencies_with_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    adapter = ClaudeCodeAdapter()
    deps = adapter.required_dependencies()
    dep_names = [d.name for d in deps]
    assert "ANTHROPIC_API_KEY" not in dep_names
    assert "claude" in dep_names
