"""Tests for agent/background.py — Background Agent."""
import time

from agent.background import BackgroundAgent, BackgroundTask


def _task(kind: str = "manual") -> BackgroundTask:
    from agent.background import _now
    return BackgroundTask(
        task_id="bg_test",
        kind=kind,
        payload={"instruction": "do something"},
        created_at=_now(),
    )


def test_submit_and_list():
    agent = BackgroundAgent()
    task = _task()
    agent.submit(task)
    tasks = agent.list_tasks()
    assert any(t.task_id == task.task_id for t in tasks)


def test_get_task():
    agent = BackgroundAgent()
    task = _task()
    agent.submit(task)
    fetched = agent.get_task(task.task_id)
    assert fetched is not None
    assert fetched.task_id == task.task_id


def test_get_missing_returns_none():
    agent = BackgroundAgent()
    assert agent.get_task("nope") is None


def test_start_and_stop():
    agent = BackgroundAgent()
    agent.start()
    assert agent.is_running is True
    agent.stop()
    assert agent.is_running is False


def test_task_processed_on_start():
    completed: list[BackgroundTask] = []
    agent = BackgroundAgent(on_task_complete=completed.append)
    agent.start()

    from agent.background import _now
    task = agent.create_and_submit("test", {"x": 1})

    # Wait for the worker to process
    deadline = time.time() + 3.0
    while time.time() < deadline and not completed:
        time.sleep(0.05)

    agent.stop()
    assert len(completed) == 1
    assert completed[0].status == "done"


def test_create_and_submit():
    agent = BackgroundAgent()
    task = agent.create_and_submit("webhook", {"url": "http://x.com"})
    assert task.task_id.startswith("bg_")
    assert task.kind == "webhook"


def test_list_by_status():
    agent = BackgroundAgent()
    task = _task("manual")
    agent.submit(task)
    pending = agent.list_tasks(status="pending")
    assert any(t.task_id == task.task_id for t in pending)
    done = agent.list_tasks(status="done")
    assert not any(t.task_id == task.task_id for t in done)


def test_as_dict():
    t = _task()
    d = t.as_dict()
    assert "task_id" in d
    assert "status" in d
    assert "kind" in d
