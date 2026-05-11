"""
Tests for .github/scripts/review_agent.py

Covers:
- CANDIDATE_MODELS structure
- API key skipping logic
- Verdict parsing (PASS / FAIL)
- RateLimitError retry with exponential backoff
- Results file written with correct schema
- sys.exit codes
- Fallback when all models fail
"""
from __future__ import annotations

import importlib.util
import json
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
    openai_stub.RateLimitError = type("RateLimitError", (_BaseError,), {})

    sys.modules["openai"] = openai_stub


_stub_openai()

# Get the RateLimitError class from the stub (imported by the module)
_RateLimitError = sys.modules["openai"].RateLimitError

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
_SCRIPT_PATH = Path(__file__).parent.parent / ".github" / "scripts" / "review_agent.py"


def _load_module(script_path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("review_agent", script_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


review = _load_module(_SCRIPT_PATH)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_completion(content: str) -> MagicMock:
    """Build a fake OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    res = MagicMock()
    res.choices = [choice]
    return res


def _patch_gh_diff(pr_diff: str = "diff content"):
    """Context manager that patches subprocess.check_output to return a PR diff."""
    return patch("subprocess.check_output", return_value=pr_diff)


# ---------------------------------------------------------------------------
# CANDIDATE_MODELS structure
# ---------------------------------------------------------------------------
class TestCandidateModels:
    def test_has_at_least_two_models(self):
        assert len(review.CANDIDATE_MODELS) >= 2

    def test_each_model_has_three_fields(self):
        for entry in review.CANDIDATE_MODELS:
            assert len(entry) == 3, f"Expected (model, base_url, api_key), got {entry!r}"

    def test_base_urls_are_https(self):
        for model_name, base_url, _ in review.CANDIDATE_MODELS:
            assert base_url.startswith("https://"), (
                f"{model_name} base_url is not HTTPS: {base_url}"
            )

    def test_model_names_nonempty(self):
        for model_name, _, _ in review.CANDIDATE_MODELS:
            assert model_name.strip(), "Model name should not be empty"


# ---------------------------------------------------------------------------
# main() – verdict parsing
# ---------------------------------------------------------------------------
class TestVerdictParsing:
    def _run_main(self, tmp_path, monkeypatch, llm_response: str, pr_num: str = "42"):
        monkeypatch.setattr(review, "PR_NUMBER", pr_num)
        result_file = tmp_path / "review_result.json"
        monkeypatch.setattr(review, "RESULT_FILE", str(result_file))

        # Patch CANDIDATE_MODELS to use a single fake model with a known key
        monkeypatch.setattr(review, "CANDIDATE_MODELS", [
            ("test-model", "https://fake.api/v1", "sk-test"),
        ])

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_completion(llm_response)

        with _patch_gh_diff("fake diff"):
            # The script uses `from openai import OpenAI` so patch the bound name
            with patch.object(review, "OpenAI", return_value=mock_client):
                with pytest.raises(SystemExit) as exc_info:
                    review.main()

        data = json.loads(result_file.read_text())
        return data, exc_info.value.code

    def test_pass_verdict_writes_pass(self, tmp_path, monkeypatch):
        data, code = self._run_main(tmp_path, monkeypatch, "OVERALL: PASS – looks good")
        assert data["verdict"] == "PASS"
        assert code == 0

    def test_fail_verdict_writes_fail(self, tmp_path, monkeypatch):
        data, code = self._run_main(tmp_path, monkeypatch, "There are issues. OVERALL: FAIL")
        assert data["verdict"] == "FAIL"
        assert code == 1

    def test_verdict_case_insensitive(self, tmp_path, monkeypatch):
        data, code = self._run_main(tmp_path, monkeypatch, "overall: pass with minor notes")
        assert data["verdict"] == "PASS"
        assert code == 0

    def test_summary_truncated_to_200(self, tmp_path, monkeypatch):
        long_text = "OVERALL: PASS " + "x" * 500
        data, _ = self._run_main(tmp_path, monkeypatch, long_text)
        assert len(data["summary"]) <= 200

    def test_result_file_schema(self, tmp_path, monkeypatch):
        data, _ = self._run_main(tmp_path, monkeypatch, "OVERALL: PASS")
        assert "verdict" in data
        assert "summary" in data
        assert data["verdict"] in ("PASS", "FAIL")

    def test_no_overall_keyword_results_in_fail(self, tmp_path, monkeypatch):
        data, code = self._run_main(tmp_path, monkeypatch, "Looks mostly fine but no verdict")
        assert data["verdict"] == "FAIL"
        assert code == 1


# ---------------------------------------------------------------------------
# main() – API key skipping
# ---------------------------------------------------------------------------
class TestApiKeySkipping:
    def test_skips_model_without_api_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(review, "PR_NUMBER", "1")
        result_file = tmp_path / "result.json"
        monkeypatch.setattr(review, "RESULT_FILE", str(result_file))

        # First model has no key, second has one
        monkeypatch.setattr(review, "CANDIDATE_MODELS", [
            ("model-a", "https://fake.api/v1", None),
            ("model-b", "https://fake.api/v1", "sk-real"),
        ])

        call_tracker = {"count": 0, "kwargs": []}

        def fake_openai_ctor(**kw):
            call_tracker["count"] += 1
            call_tracker["kwargs"].append(kw)
            client = MagicMock()
            client.chat.completions.create.return_value = _make_mock_completion("OVERALL: PASS")
            return client

        with _patch_gh_diff():
            with patch.object(review, "OpenAI", side_effect=fake_openai_ctor):
                with pytest.raises(SystemExit) as exc_info:
                    review.main()

        assert exc_info.value.code == 0
        # OpenAI should have been instantiated only once (model-b, not model-a)
        assert call_tracker["count"] == 1
        assert call_tracker["kwargs"][0]["api_key"] == "sk-real"

    def test_all_models_missing_keys_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(review, "PR_NUMBER", "1")
        result_file = tmp_path / "result.json"
        monkeypatch.setattr(review, "RESULT_FILE", str(result_file))

        monkeypatch.setattr(review, "CANDIDATE_MODELS", [
            ("model-a", "https://fake.api/v1", None),
            ("model-b", "https://fake.api/v1", None),
        ])

        with _patch_gh_diff():
            with pytest.raises(SystemExit) as exc_info:
                review.main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# main() – RateLimitError retry
# ---------------------------------------------------------------------------
class TestRateLimitRetry:
    def test_rate_limit_retries_with_backoff(self, tmp_path, monkeypatch):
        monkeypatch.setattr(review, "PR_NUMBER", "5")
        result_file = tmp_path / "result.json"
        monkeypatch.setattr(review, "RESULT_FILE", str(result_file))
        monkeypatch.setattr(review, "CANDIDATE_MODELS", [
            ("test-model", "https://fake.api/v1", "sk-test"),
        ])

        call_count = {"n": 0}

        def fake_create(**kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                raise review.RateLimitError(
                    message="rate limited",
                    response=MagicMock(status_code=429, headers={}),
                    body=None,
                )
            return _make_mock_completion("OVERALL: PASS")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create

        with _patch_gh_diff():
            with patch.object(review, "OpenAI", return_value=mock_client):
                with patch.object(review, "time") as mock_time:
                    with pytest.raises(SystemExit) as exc_info:
                        review.main()

        assert exc_info.value.code == 0
        assert mock_time.sleep.call_count == 2
        # Verify exponential backoff: sleep(5), sleep(10) for retries 0 and 1
        sleep_calls = [c.args[0] for c in mock_time.sleep.call_args_list]
        assert sleep_calls[0] == 5    # 5 * 2^0
        assert sleep_calls[1] == 10   # 5 * 2^1

    def test_exhausted_retries_falls_through_to_next_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr(review, "PR_NUMBER", "5")
        result_file = tmp_path / "result.json"
        monkeypatch.setattr(review, "RESULT_FILE", str(result_file))
        monkeypatch.setattr(review, "CANDIDATE_MODELS", [
            ("model-a", "https://fake.api/v1", "sk-rate-limited"),
            ("model-b", "https://fake.api/v1", "sk-good"),
        ])

        # All 3 calls to model-a raise RateLimitError; model-b succeeds
        client_a = MagicMock()
        client_a.chat.completions.create.side_effect = review.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        client_b = MagicMock()
        client_b.chat.completions.create.return_value = _make_mock_completion("OVERALL: PASS")

        clients = {"sk-rate-limited": client_a, "sk-good": client_b}

        def make_client(**kw):
            return clients[kw["api_key"]]

        with _patch_gh_diff():
            with patch.object(review, "OpenAI", side_effect=make_client):
                with patch.object(review, "time"):
                    with pytest.raises(SystemExit) as exc_info:
                        review.main()

        # Should eventually succeed via model-b
        assert exc_info.value.code == 0

    def test_non_rate_limit_exception_breaks_retry_loop(self, tmp_path, monkeypatch):
        """A non-RateLimitError should break the retry loop for that model."""
        monkeypatch.setattr(review, "PR_NUMBER", "7")
        result_file = tmp_path / "result.json"
        monkeypatch.setattr(review, "RESULT_FILE", str(result_file))
        monkeypatch.setattr(review, "CANDIDATE_MODELS", [
            ("model-a", "https://fake.api/v1", "sk-test"),
        ])

        call_count = {"n": 0}

        def fake_create(**kwargs):
            call_count["n"] += 1
            raise ConnectionError("network error")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create

        with _patch_gh_diff():
            with patch.object(review, "OpenAI", return_value=mock_client):
                with pytest.raises(SystemExit) as exc_info:
                    review.main()

        # Should only attempt once (break on non-RateLimitError)
        assert call_count["n"] == 1
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# main() – stops querying after first successful model
# ---------------------------------------------------------------------------
class TestStopsAfterFirstSuccess:
    def test_uses_first_available_model_and_stops(self, tmp_path, monkeypatch):
        monkeypatch.setattr(review, "PR_NUMBER", "99")
        result_file = tmp_path / "result.json"
        monkeypatch.setattr(review, "RESULT_FILE", str(result_file))
        monkeypatch.setattr(review, "CANDIDATE_MODELS", [
            ("model-a", "https://fake.api/v1", "sk-first"),
            ("model-b", "https://fake.api/v1", "sk-second"),
        ])

        client_call_counts = {"a": 0, "b": 0}

        def make_client(**kw):
            client = MagicMock()
            key = "a" if kw.get("api_key") == "sk-first" else "b"
            def create(**ckwargs):
                client_call_counts[key] += 1
                return _make_mock_completion("OVERALL: PASS")
            client.chat.completions.create.side_effect = create
            return client

        with _patch_gh_diff():
            with patch.object(review, "OpenAI", side_effect=make_client):
                with pytest.raises(SystemExit) as exc_info:
                    review.main()

        assert exc_info.value.code == 0
        assert client_call_counts["a"] == 1
        assert client_call_counts["b"] == 0  # should NOT have been called