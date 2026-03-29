import asyncio
from pathlib import Path

from agent_loop import AgentRunner


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
