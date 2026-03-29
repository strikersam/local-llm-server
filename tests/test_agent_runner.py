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
    assert target.read_text(encoding="utf-8") == "new text"


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
