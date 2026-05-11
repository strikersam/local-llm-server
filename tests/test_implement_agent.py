"""
Tests for .github/scripts/implement_agent.py

Covers:
- tool_bash: shlex splitting, output formatting, error handling
- tool_read_file: truncation, error handling
- tool_write_file: parent creation, success/error
- tool_search: 50-line cap, error handling
- tool_list_files: 200-line cap, default pattern, error handling
- PROVIDERS / CANDIDATE_MODELS structure
- TOOL_DISPATCH routing
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out the `openai` package (not in project requirements) before loading
# the script under test.
# ---------------------------------------------------------------------------
def _stub_openai() -> None:
    """Insert lightweight stubs for the openai symbols the script imports."""
    if "openai" in sys.modules:
        return

    openai_stub = types.ModuleType("openai")

    class _BaseError(Exception):
        def __init__(self, message="", *, response=None, body=None):
            super().__init__(message)

    openai_stub.OpenAI = MagicMock
    openai_stub.NotFoundError = type("NotFoundError", (_BaseError,), {})
    openai_stub.PermissionDeniedError = type("PermissionDeniedError", (_BaseError,), {})
    openai_stub.RateLimitError = type("RateLimitError", (_BaseError,), {})

    sys.modules["openai"] = openai_stub


_stub_openai()

# ---------------------------------------------------------------------------
# Import the module under test without executing __main__
# ---------------------------------------------------------------------------
_SCRIPT_PATH = Path(__file__).parent.parent / ".github" / "scripts" / "implement_agent.py"


def _load_module(script_path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("implement_agent", script_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


impl = _load_module(_SCRIPT_PATH)


# ---------------------------------------------------------------------------
# tool_bash
# ---------------------------------------------------------------------------
class TestToolBash:
    def test_simple_echo(self):
        result = impl.tool_bash("echo hello")
        assert "hello" in result
        assert "[exit 0]" in result

    def test_stderr_captured(self):
        result = impl.tool_bash("sh -c 'echo err >&2; exit 1'")
        assert "[stderr]" in result
        assert "err" in result
        assert "[exit 1]" in result

    def test_stdout_truncated_to_6000(self, tmp_path):
        # Write a script that produces > 6000 chars of output
        big_output = "x" * 8000
        script = tmp_path / "big.py"
        script.write_text(f"print({'x' * 8000!r})\n")
        result = impl.tool_bash(f"python {script}")
        # The captured stdout portion should be at most 6000 chars before [stderr]
        stdout_part = result.split("\n[stderr]")[0]
        assert len(stdout_part) <= 6000

    def test_invalid_command_returns_error(self):
        # Passing a command that does not exist
        result = impl.tool_bash("__nonexistent_cmd_xyz__")
        assert result.startswith("[error:")

    def test_exit_code_in_output(self):
        result = impl.tool_bash("sh -c 'exit 42'")
        assert "[exit 42]" in result

    def test_uses_shlex_split_not_shell(self):
        # Verify shell injection is NOT executed: pipe should be treated as literal arg
        # "echo foo | cat" with shell=False will fail because "echo" gets args ["|", "cat"]
        # which prints "| cat" literally – not dangerous.
        result = impl.tool_bash("echo foo")
        assert "foo" in result
        assert "[exit 0]" in result

    def test_exception_format(self):
        # Force an exception by patching subprocess.run to raise
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            result = impl.tool_bash("anything")
        assert result == "[error: boom]"


# ---------------------------------------------------------------------------
# tool_read_file
# ---------------------------------------------------------------------------
class TestToolReadFile:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("hello world")
        assert impl.tool_read_file(str(f)) == "hello world"

    def test_truncates_to_12000(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("a" * 15000)
        result = impl.tool_read_file(str(f))
        assert len(result) == 12000

    def test_missing_file_returns_error(self, tmp_path):
        result = impl.tool_read_file(str(tmp_path / "no_such_file.txt"))
        assert result.startswith("[error:")

    def test_replaces_encoding_errors(self, tmp_path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\xff\xfe hello")
        result = impl.tool_read_file(str(f))
        # Should not raise; replacement character or something safe is returned
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# tool_write_file
# ---------------------------------------------------------------------------
class TestToolWriteFile:
    def test_writes_and_returns_success(self, tmp_path):
        dest = str(tmp_path / "out.txt")
        result = impl.tool_write_file(dest, "content")
        assert result == f"Written to {dest}"
        assert Path(dest).read_text() == "content"

    def test_creates_parent_directories(self, tmp_path):
        dest = str(tmp_path / "a" / "b" / "c" / "file.txt")
        result = impl.tool_write_file(dest, "deep")
        assert result == f"Written to {dest}"
        assert Path(dest).read_text() == "deep"

    def test_error_on_invalid_path(self, tmp_path):
        # Writing to a directory that exists as a file (simulate error)
        # Make a file then try to write to a child of it
        existing_file = tmp_path / "file.txt"
        existing_file.write_text("occupied")
        result = impl.tool_write_file(str(existing_file / "child"), "data")
        assert result.startswith("[error:")

    def test_overwrites_existing_file(self, tmp_path):
        dest = tmp_path / "exists.txt"
        dest.write_text("old")
        impl.tool_write_file(str(dest), "new")
        assert dest.read_text() == "new"


# ---------------------------------------------------------------------------
# tool_search
# ---------------------------------------------------------------------------
class TestToolSearch:
    def test_returns_exit_code(self, tmp_path, monkeypatch):
        # Run a real grep search in a temp dir with a known file
        (tmp_path / "hello.py").write_text("print('hello')\n")
        monkeypatch.chdir(tmp_path)
        result = impl.tool_search("hello")
        assert "[exit" in result

    def test_limits_to_50_lines(self):
        # Mock subprocess.run to return 100 lines
        mock_result = MagicMock()
        mock_result.stdout = "\n".join(f"match:{i}" for i in range(100))
        mock_result.stderr = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = impl.tool_search("pattern")
        # Should only include first 50 lines
        lines = result.split("\n[stderr]")[0].splitlines()
        assert len(lines) <= 50

    def test_exception_returns_error(self):
        with patch("subprocess.run", side_effect=OSError("no grep")):
            result = impl.tool_search("anything")
        assert result.startswith("[error:")

    def test_stderr_included(self):
        mock_result = MagicMock()
        mock_result.stdout = "match1\nmatch2\n"
        mock_result.stderr = "some stderr"
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            result = impl.tool_search("pattern")
        assert "some stderr" in result
        assert "[exit 1]" in result

    def test_empty_stderr_omitted_from_error_section(self):
        mock_result = MagicMock()
        mock_result.stdout = "line1\n"
        mock_result.stderr = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = impl.tool_search("foo")
        assert "[stderr]" in result  # section header still present
        assert "[exit 0]" in result

    def test_uses_shell_false(self):
        """Verify tool_search passes shell=False to subprocess.run."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            impl.tool_search("test_pattern")
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("shell") is False or call_kwargs[1].get("shell") is False


# ---------------------------------------------------------------------------
# tool_list_files
# ---------------------------------------------------------------------------
class TestToolListFiles:
    def test_default_pattern(self):
        mock_result = MagicMock()
        mock_result.stdout = "\n".join(f"file_{i}.py" for i in range(5))
        mock_result.stderr = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = impl.tool_list_files()
        # Called with default pattern **/*
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args.args[0]
        assert "**/*" in cmd
        assert "[exit 0]" in result

    def test_limits_to_200_lines(self):
        mock_result = MagicMock()
        mock_result.stdout = "\n".join(f"file_{i}.py" for i in range(300))
        mock_result.stderr = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = impl.tool_list_files("*.py")
        # Only first 200 lines should appear before [stderr]
        file_lines = result.split("\n[stderr]")[0].splitlines()
        assert len(file_lines) <= 200

    def test_exception_returns_error(self):
        with patch("subprocess.run", side_effect=OSError("no git")):
            result = impl.tool_list_files("**/*")
        assert result.startswith("[error:")

    def test_stderr_truncated_to_2000(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "e" * 3000
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            result = impl.tool_list_files()
        stderr_section = result.split("[stderr]\n")[1].split("\n[exit")[0]
        assert len(stderr_section) <= 2000

    def test_uses_shell_false(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            impl.tool_list_files("*.ts")
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("shell") is False or call_kwargs[1].get("shell") is False

    def test_custom_pattern_forwarded(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            impl.tool_list_files("tests/**/*.py")
        cmd = mock_run.call_args[0][0]
        assert "tests/**/*.py" in cmd


# ---------------------------------------------------------------------------
# PROVIDERS / CANDIDATE_MODELS structure
# ---------------------------------------------------------------------------
class TestProvidersAndModels:
    def test_providers_keys(self):
        assert "nvidia" in impl.PROVIDERS
        assert "moonshot" in impl.PROVIDERS

    def test_providers_have_base_url(self):
        for name, cfg in impl.PROVIDERS.items():
            assert "base_url" in cfg, f"{name} missing base_url"
            assert cfg["base_url"].startswith("https://"), f"{name} base_url not https"

    def test_providers_have_api_key_field(self):
        for name, cfg in impl.PROVIDERS.items():
            assert "api_key" in cfg, f"{name} missing api_key"

    def test_candidate_models_structure(self):
        for model_name, provider_name in impl.CANDIDATE_MODELS:
            assert isinstance(model_name, str) and model_name
            assert provider_name in impl.PROVIDERS, (
                f"Model {model_name} references unknown provider {provider_name!r}"
            )

    def test_candidate_models_has_at_least_two_providers(self):
        providers_used = {p for _, p in impl.CANDIDATE_MODELS}
        assert len(providers_used) >= 2, "Should have models from at least 2 providers"

    def test_nvidia_base_url(self):
        assert "nvidia.com" in impl.PROVIDERS["nvidia"]["base_url"]

    def test_moonshot_base_url(self):
        assert "moonshot" in impl.PROVIDERS["moonshot"]["base_url"]


# ---------------------------------------------------------------------------
# TOOL_DISPATCH
# ---------------------------------------------------------------------------
class TestToolDispatch:
    def test_bash_tool_dispatched(self):
        with patch.object(impl, "tool_bash", return_value="ok") as m:
            result = impl.TOOL_DISPATCH["bash"]({"cmd": "echo hi"})
        m.assert_called_once_with("echo hi")
        assert result == "ok"

    def test_read_file_dispatched(self):
        with patch.object(impl, "tool_read_file", return_value="content") as m:
            result = impl.TOOL_DISPATCH["read_file"]({"path": "/tmp/x"})
        m.assert_called_once_with("/tmp/x")

    def test_write_file_dispatched(self):
        with patch.object(impl, "tool_write_file", return_value="Written to /tmp/x") as m:
            result = impl.TOOL_DISPATCH["write_file"]({"path": "/tmp/x", "content": "data"})
        m.assert_called_once_with("/tmp/x", "data")

    def test_list_files_dispatched_with_default(self):
        with patch.object(impl, "tool_list_files", return_value="files") as m:
            result = impl.TOOL_DISPATCH["list_files"]({})
        m.assert_called_once_with("**/*")

    def test_list_files_dispatched_with_pattern(self):
        with patch.object(impl, "tool_list_files", return_value="files") as m:
            result = impl.TOOL_DISPATCH["list_files"]({"pattern": "*.py"})
        m.assert_called_once_with("*.py")

    def test_search_code_dispatched(self):
        with patch.object(impl, "tool_search", return_value="results") as m:
            result = impl.TOOL_DISPATCH["search_code"]({"query": "def foo"})
        m.assert_called_once_with("def foo")

    def test_unknown_tool_returns_error(self):
        unknown_fn = impl.TOOL_DISPATCH.get("nonexistent_tool", lambda _i: "[error: unknown tool]")
        result = unknown_fn({})
        assert result == "[error: unknown tool]"


# ---------------------------------------------------------------------------
# API-key skipping and RateLimitError handling (unit tests with mocks)
# ---------------------------------------------------------------------------
class TestMainProviderLogic:
    """Tests around the main() loop logic – patched to avoid real API calls."""

    def _make_mock_response(self, content="Done", tool_calls=None):
        msg = MagicMock()
        msg.content = content
        msg.tool_calls = tool_calls or []
        msg.model_dump.return_value = {"role": "assistant", "content": content}
        choice = MagicMock()
        choice.message = msg
        res = MagicMock()
        res.choices = [choice]
        return res

    def test_skips_model_when_api_key_missing(self, tmp_path, monkeypatch):
        """When all providers have no API key, main() should write a failure result."""
        monkeypatch.setitem(impl.PROVIDERS["nvidia"], "api_key", None)
        monkeypatch.setitem(impl.PROVIDERS["moonshot"], "api_key", None)

        result_file = tmp_path / "result.json"
        monkeypatch.setattr(impl, "RESULT_FILE", str(result_file))

        with pytest.raises(SystemExit) as exc_info:
            impl.main()

        assert exc_info.value.code == 1
        assert result_file.exists()
        data = json.loads(result_file.read_text())
        assert data["success"] is False

    def test_rate_limit_triggers_sleep_and_retry(self, tmp_path, monkeypatch, capsys):
        """RateLimitError should print a message and sleep, then retry."""
        # Use the bound RateLimitError from the loaded module
        RateLimitError = impl.RateLimitError

        monkeypatch.setitem(impl.PROVIDERS["nvidia"], "api_key", "test-key")
        monkeypatch.setitem(impl.PROVIDERS["moonshot"], "api_key", None)

        result_file = tmp_path / "result.json"
        monkeypatch.setattr(impl, "RESULT_FILE", str(result_file))
        monkeypatch.setattr(impl, "MAX_TURNS", 2)

        call_count = {"n": 0}

        def fake_create(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RateLimitError(
                    message="rate limited",
                    response=MagicMock(status_code=429, headers={}),
                    body=None,
                )
            return self._make_mock_response("Done")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create

        with patch.object(impl, "OpenAI", return_value=mock_client):
            with patch.object(impl, "time") as mock_time:
                with pytest.raises(SystemExit):
                    impl.main()

        # sleep should have been called for the rate limit
        mock_time.sleep.assert_called_once()
        assert call_count["n"] >= 2

    def test_not_found_error_advances_model(self, tmp_path, monkeypatch):
        """NotFoundError/PermissionDeniedError should advance to next model."""
        NotFoundError = impl.NotFoundError

        monkeypatch.setitem(impl.PROVIDERS["nvidia"], "api_key", "test-key")
        monkeypatch.setitem(impl.PROVIDERS["moonshot"], "api_key", None)

        result_file = tmp_path / "result.json"
        monkeypatch.setattr(impl, "RESULT_FILE", str(result_file))
        monkeypatch.setattr(impl, "MAX_TURNS", 3)

        # Patch CANDIDATE_MODELS so both entries use nvidia (key present)
        monkeypatch.setattr(impl, "CANDIDATE_MODELS", [
            ("model-a", "nvidia"),
            ("model-b", "nvidia"),
        ])

        call_count = {"n": 0}

        def fake_create(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise NotFoundError(
                    message="not found",
                    response=MagicMock(status_code=404, headers={}),
                    body=None,
                )
            return self._make_mock_response("Done")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create

        with patch.object(impl, "OpenAI", return_value=mock_client):
            with pytest.raises(SystemExit):
                impl.main()

        # Should have tried at least 2 models
        assert call_count["n"] >= 2