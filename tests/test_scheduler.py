"""Tests for agent/scheduler.py — Scheduled Agent Jobs."""
import json
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


# ─── Persistence ──────────────────────────────────────────────────────────────

def test_persistence_saves_and_loads(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    sched = AgentScheduler(jobs_path=jobs_file)
    sched.create(name="persist-me", cron="0 9 * * *", instruction="Hello")
    sched.shutdown()

    assert jobs_file.exists()
    data = json.loads(jobs_file.read_text())
    assert len(data) == 1
    assert data[0]["name"] == "persist-me"

    # Load into a fresh scheduler — job should be restored
    sched2 = AgentScheduler(jobs_path=jobs_file)
    jobs = sched2.list()
    assert len(jobs) == 1
    assert jobs[0].name == "persist-me"
    assert jobs[0].instruction == "Hello"
    sched2.shutdown()


def test_persistence_removes_on_delete(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    sched = AgentScheduler(jobs_path=jobs_file)
    job = sched.create(name="temp", cron="* * * * *", instruction="X")
    sched.delete(job.job_id)
    sched.shutdown()

    data = json.loads(jobs_file.read_text())
    assert data == []


def test_persistence_updates_run_count(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    fired: list[ScheduledJob] = []
    sched = AgentScheduler(on_fire=fired.append, jobs_path=jobs_file)
    job = sched.create(name="counter", cron="* * * * *", instruction="Count")
    sched.trigger(job.job_id)
    sched.shutdown()

    data = json.loads(jobs_file.read_text())
    assert data[0]["run_count"] == 1


def test_no_persistence_when_path_omitted():
    # Should not raise even though no path is given
    sched = AgentScheduler()
    sched.create(name="mem-only", cron="* * * * *", instruction="M")
    sched.shutdown()  # no error


# ─── Seed ─────────────────────────────────────────────────────────────────────

def test_seed_creates_job_when_absent():
    sched = AgentScheduler()
    job = sched.seed(name="scout", cron="0 9 * * *", instruction="Scout")
    assert job.name == "scout"
    assert len(sched.list()) == 1
    sched.shutdown()


def test_seed_is_idempotent():
    sched = AgentScheduler()
    job1 = sched.seed(name="scout", cron="0 9 * * *", instruction="Scout v1")
    job2 = sched.seed(name="scout", cron="0 9 * * *", instruction="Scout v2")
    assert job1.job_id == job2.job_id
    assert len(sched.list()) == 1
    sched.shutdown()


def test_seed_preserves_existing_instruction():
    sched = AgentScheduler()
    sched.seed(name="scout", cron="0 9 * * *", instruction="Original")
    # Second seed with different instruction must not overwrite
    job = sched.seed(name="scout", cron="0 9 * * *", instruction="New")
    assert job.instruction == "Original"
    sched.shutdown()


def test_seed_persists_new_job(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    sched = AgentScheduler(jobs_path=jobs_file)
    sched.seed(name="seeded", cron="0 9 * * *", instruction="Seeded job")
    sched.shutdown()

    data = json.loads(jobs_file.read_text())
    assert len(data) == 1
    assert data[0]["name"] == "seeded"


def test_seed_skips_when_loaded_from_disk(tmp_path):
    jobs_file = tmp_path / "jobs.json"

    # First boot — seed creates the job
    sched1 = AgentScheduler(jobs_path=jobs_file)
    sched1.seed(name="scout", cron="0 9 * * *", instruction="Boot 1")
    sched1.shutdown()

    # Second boot — seed must not duplicate
    sched2 = AgentScheduler(jobs_path=jobs_file)
    sched2.seed(name="scout", cron="0 9 * * *", instruction="Boot 2")
    assert len(sched2.list()) == 1
    assert sched2.list()[0].instruction == "Boot 1"
    sched2.shutdown()
