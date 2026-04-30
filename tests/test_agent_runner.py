import asyncio
from pathlib import Path

from agent.loop import AgentRunner


def test_agent_runner_applies_a_change_with_mocked_model(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "notes.txt"
    target.write_text("old text\n", encoding="utf-8")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)
    responses = iter(
        [
            '{"goal":"Update notes","steps":[{"id":1,"description":"Replace notes content","files":["notes.txt"],"type":"edit"}]}',
            '{"tool":"read_file","args":{"path":"notes.txt"}}',
            '{"tool":"finish","args":{"reason":"Enough context gathered"}}',
            'FILE: notes.txt\nACTION: replace\n```text\nnew text\n```',
            '{"status":"pass","issues":[]}',
        ]
    )

    async def fake_chat_text(model: str, messages: list[dict[str, str]]) -> str:
        return next(responses)

    runner._chat_text = fake_chat_text  # type: ignore[method-assign]

    result = asyncio.run(
        runner.run(
            instruction="Update notes",
            history=[],
            requested_model=None,
            auto_commit=False,
            max_steps=3,
        )
    )

    assert result["steps"][0]["status"] == "applied"
    assert result["steps"][0]["changed_files"] == ["notes.txt"]
    assert target.read_text(encoding="utf-8") == "new text\n"


def test_agent_runner_reports_format_failure_with_mocked_model(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "notes.txt"
    target.write_text("old text\n", encoding="utf-8")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)
    responses = iter(
        [
            '{"goal":"Update notes","steps":[{"id":1,"description":"Replace notes content","files":["notes.txt"],"type":"edit"}]}',
            '{"tool":"finish","args":{"reason":"skip"}}',
            "not valid executor output",
            "still not valid",
            "not valid executor output",
            "still not valid",
            "not valid executor output",
            "still not valid",
        ]
    )

    async def fake_chat_text(model: str, messages: list[dict[str, str]]) -> str:
        return next(responses)

    runner._chat_text = fake_chat_text  # type: ignore[method-assign]

    result = asyncio.run(
        runner.run(
            instruction="Update notes",
            history=[],
            requested_model=None,
            auto_commit=False,
            max_steps=3,
        )
    )

    assert result["steps"][0]["status"] == "failed"
    assert "violated format" in result["steps"][0]["issues"][0].lower()


def test_agent_runner_cleans_language_prefix_from_generated_file(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "notes.txt"
    target.write_text("old text\n", encoding="utf-8")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)
    responses = iter(
        [
            '{"goal":"Update notes","steps":[{"id":1,"description":"Replace notes content","files":["notes.txt"],"type":"edit"}]}',
            '{"tool":"finish","args":{"reason":"Enough context gathered"}}',
            'FILE: notes.txt\nACTION: replace\n```text\ntext\nnew text\n```',
            '{"status":"pass","issues":[]}',
        ]
    )

    async def fake_chat_text(model: str, messages: list[dict[str, str]]) -> str:
        return next(responses)

    runner._chat_text = fake_chat_text  # type: ignore[method-assign]

    result = asyncio.run(
        runner.run(
            instruction="Update notes",
            history=[],
            requested_model="qwen3-coder:30b",
            auto_commit=False,
            max_steps=3,
        )
    )

    assert result["steps"][0]["status"] == "applied"
    assert target.read_text(encoding="utf-8") == "new text\n"


def test_agent_runner_fails_incomplete_shared_logger_change(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "service.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)
    responses = iter(
        [
            '{"goal":"Add logging","steps":[{"id":1,"description":"Add logging across this module and create a shared logger utility.","files":["service.py"],"type":"edit"}]}',
            '{"tool":"finish","args":{"reason":"Enough context gathered"}}',
            "FILE: service.py\nACTION: replace\n```python\nimport logging\n\nlogger = logging.getLogger(__name__)\nprint('hello')\n```",
            '{"status":"pass","issues":[]}',
        ]
    )

    async def fake_chat_text(model: str, messages: list[dict[str, str]]) -> str:
        return next(responses)

    runner._chat_text = fake_chat_text  # type: ignore[method-assign]

    result = asyncio.run(
        runner.run(
            instruction="Add logging across this module and create a shared logger utility.",
            history=[],
            requested_model="qwen3-coder:30b",
            auto_commit=False,
            max_steps=3,
        )
    )

    assert result["steps"][0]["status"] == "failed"
    assert any("shared logger utility" in issue.lower() for issue in result["steps"][0]["issues"])


def test_agent_runner_fails_unsafe_jwt_change(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    app_file = root / "app.py"
    deps = root / "requirements.txt"
    app_file.write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    deps.write_text("fastapi\n", encoding="utf-8")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)
    responses = iter(
        [
            '{"goal":"Add JWT auth","steps":[{"id":1,"description":"Add authentication to this API using JWT and update all relevant routes.","files":["app.py"],"type":"edit"}]}',
            '{"tool":"finish","args":{"reason":"Enough context gathered"}}',
            'FILE: app.py\nACTION: replace\n```python\nfrom fastapi import FastAPI\nSECRET_KEY = "hardcoded"\napp = FastAPI()\n```',
            '{"status":"pass","issues":[]}',
            'FILE: app.py\nACTION: replace\n```python\nfrom fastapi import FastAPI\nSECRET_KEY = "hardcoded"\napp = FastAPI()\n```',
            '{"status":"pass","issues":[]}',
            'FILE: app.py\nACTION: replace\n```python\nfrom fastapi import FastAPI\nSECRET_KEY = "hardcoded"\napp = FastAPI()\n```',
            '{"status":"pass","issues":[]}',
        ]
    )

    async def fake_chat_text(model: str, messages: list[dict[str, str]]) -> str:
        return next(responses)

    runner._chat_text = fake_chat_text  # type: ignore[method-assign]

    result = asyncio.run(
        runner.run(
            instruction="Add authentication to this API using JWT and update all relevant routes.",
            history=[],
            requested_model="qwen3-coder:30b",
            auto_commit=False,
            max_steps=3,
        )
    )

    assert result["steps"][0]["status"] == "failed"
    assert any("secret_key" in issue.lower() for issue in result["steps"][0]["issues"])


# ── _normalize_plan_response unit tests ──────────────────────────────────────

def _make_runner() -> AgentRunner:
    return AgentRunner(ollama_base="http://localhost:11434")


def test_normalize_slices_renamed_to_steps():
    runner = _make_runner()
    raw = {
        "goal": "do the thing",
        "slices": [{"id": 1, "description": "step one", "type": "analyze", "files": []}],
    }
    result = runner._normalize_plan_response(raw, "do the thing")
    assert "steps" in result
    assert "slices" not in result
    assert result["steps"][0]["description"] == "step one"


def test_normalize_missing_goal_derived_from_instruction():
    runner = _make_runner()
    raw = {"steps": [{"id": 1, "description": "do it", "type": "edit", "files": ["f.py"]}]}
    result = runner._normalize_plan_response(raw, "Update the config file")
    assert result["goal"] == "Update the config file"


def test_normalize_goal_truncated_to_200_chars():
    runner = _make_runner()
    long_instruction = "x" * 300
    raw = {"steps": []}
    result = runner._normalize_plan_response(raw, long_instruction)
    assert len(result["goal"]) == 200


def test_normalize_missing_step_type_defaults_to_analyze():
    runner = _make_runner()
    raw = {
        "goal": "refactor",
        "steps": [{"id": 1, "description": "look around", "files": []}],
    }
    result = runner._normalize_plan_response(raw, "refactor")
    assert result["steps"][0]["type"] == "analyze"


def test_normalize_invalid_step_type_replaced_with_analyze():
    runner = _make_runner()
    raw = {
        "goal": "check something",
        "steps": [{"id": 1, "description": "review code", "files": [], "type": "review"}],
    }
    result = runner._normalize_plan_response(raw, "check something")
    assert result["steps"][0]["type"] == "analyze"


def test_normalize_valid_step_type_unchanged():
    runner = _make_runner()
    for valid_type in ("edit", "create", "github"):
        raw = {
            "goal": "task",
            "steps": [{"id": 1, "description": "do", "files": [], "type": valid_type}],
        }
        result = runner._normalize_plan_response(raw, "task")
        assert result["steps"][0]["type"] == valid_type


def test_normalize_slices_and_missing_goal_together():
    """Reproduce the exact error from the screenshot: slices present, goal absent."""
    runner = _make_runner()
    raw = {
        "slices": [
            {"id": 1, "description": "gather retrospective findings", "files": []},
        ]
    }
    result = runner._normalize_plan_response(raw, "Summarise retrospective findings")
    assert "steps" in result
    assert "slices" not in result
    assert result["goal"] == "Summarise retrospective findings"
    assert result["steps"][0]["type"] == "analyze"


def test_runner_succeeds_when_model_returns_slices_schema(tmp_path: Path):
    """End-to-end: model returns CRISPY-style slices, plan should still execute."""
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "notes.txt"
    target.write_text("old\n", encoding="utf-8")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)
    responses = iter(
        [
            # Planner returns slices schema (no goal, no steps)
            '{"slices":[{"id":1,"description":"Update notes file","files":["notes.txt"]}]}',
            # Executor tool selection
            '{"tool":"finish","args":{"reason":"ready"}}',
            # Executor writes file
            "FILE: notes.txt\nACTION: replace\n```text\nnew content\n```",
            # Verifier approves
            '{"status":"pass","issues":[]}',
        ]
    )

    async def fake_chat_text(model: str, messages: list) -> str:
        return next(responses)

    runner._chat_text = fake_chat_text  # type: ignore[method-assign]

    result = asyncio.run(
        runner.run(
            instruction="Update notes file",
            history=[],
            requested_model=None,
            auto_commit=False,
            max_steps=3,
        )
    )

    assert result["steps"][0]["status"] == "applied"
    assert target.read_text(encoding="utf-8") == "new content\n"
