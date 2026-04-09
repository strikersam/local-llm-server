"""Tests for agent/scheduler.py — Scheduled Agent Jobs."""
import pytest

from agent.scheduler import AgentScheduler, ScheduledJob


def test_create_job():
    sched = AgentScheduler()
    job = sched.create(name="lint", cron="0 9 * * 1", instruction="Run lint")
    assert job.name == "lint"
    assert job.cron == "0 9 * * 1"
    assert job.run_count == 0
    assert job.enabled is True
    sched.shutdown()


def test_list_jobs():
    sched = AgentScheduler()
    sched.create(name="a", cron="* * * * *", instruction="A")
    sched.create(name="b", cron="* * * * *", instruction="B")
    jobs = sched.list()
    names = [j.name for j in jobs]
    assert "a" in names
    assert "b" in names
    sched.shutdown()


def test_get_job():
    sched = AgentScheduler()
    job = sched.create(name="c", cron="* * * * *", instruction="C")
    fetched = sched.get(job.job_id)
    assert fetched is not None
    assert fetched.job_id == job.job_id
    sched.shutdown()


def test_delete_job():
    sched = AgentScheduler()
    job = sched.create(name="del", cron="* * * * *", instruction="Del")
    deleted = sched.delete(job.job_id)
    assert deleted is True
    assert sched.get(job.job_id) is None
    sched.shutdown()


def test_delete_nonexistent():
    sched = AgentScheduler()
    assert sched.delete("nope") is False
    sched.shutdown()


def test_trigger_fires_callback():
    fired: list[ScheduledJob] = []
    sched = AgentScheduler(on_fire=fired.append)
    job = sched.create(name="fire", cron="0 0 1 1 *", instruction="Fire me")
    sched.trigger(job.job_id)
    assert len(fired) == 1
    assert fired[0].job_id == job.job_id
    assert fired[0].run_count == 1
    sched.shutdown()


def test_trigger_unknown_raises():
    sched = AgentScheduler()
    with pytest.raises(KeyError):
        sched.trigger("unknown_job")
    sched.shutdown()


def test_trigger_increments_run_count():
    sched = AgentScheduler()
    job = sched.create(name="cnt", cron="* * * * *", instruction="Count")
    sched.trigger(job.job_id)
    sched.trigger(job.job_id)
    assert sched.get(job.job_id).run_count == 2
    sched.shutdown()


def test_as_dict():
    sched = AgentScheduler()
    job = sched.create(name="d", cron="* * * * *", instruction="D")
    d = job.as_dict()
    assert "job_id" in d
    assert "cron" in d
    assert "enabled" in d
    sched.shutdown()
