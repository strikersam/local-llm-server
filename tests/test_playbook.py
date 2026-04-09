"""Tests for agent/playbook.py — Automation Playbooks."""
import pytest

from agent.playbook import PlaybookLibrary


def test_register_and_list():
    lib = PlaybookLibrary()
    lib.register(
        name="daily-lint",
        description="Lint wiki daily",
        steps=[{"instruction": "Run wiki lint"}, {"instruction": "Summarise issues"}],
    )
    pbs = lib.list()
    assert any(p.name == "daily-lint" for p in pbs)


def test_get_playbook():
    lib = PlaybookLibrary()
    pb = lib.register(name="test", description="", steps=[{"instruction": "do it"}])
    fetched = lib.get(pb.playbook_id)
    assert fetched is not None
    assert fetched.name == "test"


def test_get_nonexistent_returns_none():
    lib = PlaybookLibrary()
    assert lib.get("pb_nope") is None


def test_delete():
    lib = PlaybookLibrary()
    pb = lib.register(name="del", description="", steps=[{"instruction": "x"}])
    assert lib.delete(pb.playbook_id) is True
    assert lib.get(pb.playbook_id) is None


def test_delete_nonexistent_returns_false():
    lib = PlaybookLibrary()
    assert lib.delete("pb_nope") is False


def test_steps_have_ids():
    lib = PlaybookLibrary()
    pb = lib.register(
        name="steps",
        description="",
        steps=[
            {"instruction": "step one"},
            {"instruction": "step two"},
        ],
    )
    assert pb.steps[0].step_id == 1
    assert pb.steps[1].step_id == 2


def test_start_and_finish_run():
    lib = PlaybookLibrary()
    pb = lib.register(name="run", description="", steps=[{"instruction": "go"}])
    run = lib.start_run(pb.playbook_id)
    assert run.status == "running"

    finished = lib.finish_run(run.run_id, step_results=[{"ok": True}])
    assert finished.status == "done"
    assert finished.finished_at is not None


def test_start_run_unknown_raises():
    lib = PlaybookLibrary()
    with pytest.raises(KeyError):
        lib.start_run("pb_nope")


def test_list_by_tag():
    lib = PlaybookLibrary()
    lib.register(name="a", description="", steps=[{"instruction": "x"}], tags=["ci"])
    lib.register(name="b", description="", steps=[{"instruction": "y"}], tags=["deploy"])
    ci_pbs = lib.list(tag="ci")
    assert len(ci_pbs) == 1
    assert ci_pbs[0].name == "a"


def test_as_dict():
    lib = PlaybookLibrary()
    pb = lib.register(name="d", description="desc", steps=[{"instruction": "i"}])
    d = pb.as_dict()
    assert "playbook_id" in d
    assert "steps" in d
    assert len(d["steps"]) == 1


def test_get_run():
    lib = PlaybookLibrary()
    pb = lib.register(name="gr", description="", steps=[{"instruction": "go"}])
    run = lib.start_run(pb.playbook_id)
    fetched = lib.get_run(run.run_id)
    assert fetched is not None
    assert fetched.run_id == run.run_id
