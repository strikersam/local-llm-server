"""tests/test_control_plane_api.py — Tests for Control Plane API endpoints.

Covers the new /api/schedules/* and /api/routing/* routes added as part of
the Control Plane implementation (Stage 2: runtime adapter system).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from agent.scheduler import AgentScheduler, set_scheduler, get_scheduler, ScheduledJob
from schedules.api import schedules_router
from routing.api import routing_router

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def scheduler():
    sched = AgentScheduler()
    set_scheduler(sched)
    return sched


@pytest.fixture
def schedules_client(scheduler):
    app = FastAPI()
    app.include_router(schedules_router)
    return TestClient(app)


@pytest.fixture
def mock_runtime_manager():
    mgr = MagicMock()
    mgr.get_policy.return_value = {
        "never_use_paid_providers": True,
        "require_approval_before_paid_escalation": True,
        "max_paid_escalations_per_day": 0,
        "preferred_runtime_id": "hermes",
        "fallback_runtime_ids": [],
        "task_type_runtime_overrides": {},
    }
    mgr.get_decision_log.return_value = []
    return mgr


@pytest.fixture
def routing_client(mock_runtime_manager):
    app = FastAPI()
    app.include_router(routing_router)
    with patch("routing.api.get_runtime_manager", return_value=mock_runtime_manager):
        yield TestClient(app)


# ── Scheduler singleton ───────────────────────────────────────────────────────

def test_get_scheduler_raises_before_set():
    import agent.scheduler as sched_mod
    orig = sched_mod._scheduler_instance
    sched_mod._scheduler_instance = None
    with pytest.raises(RuntimeError, match="Scheduler not initialised"):
        get_scheduler()
    sched_mod._scheduler_instance = orig


def test_set_and_get_scheduler():
    sched = AgentScheduler()
    set_scheduler(sched)
    assert get_scheduler() is sched


# ── Scheduler toggle ──────────────────────────────────────────────────────────

def test_toggle_disables_job(scheduler):
    job = scheduler.create(name="test-job", cron="0 9 * * *", instruction="ping")
    assert job.enabled is True
    toggled = scheduler.toggle(job.job_id, enabled=False)
    assert toggled.enabled is False


def test_toggle_re_enables_job(scheduler):
    job = scheduler.create(name="test-job2", cron="0 9 * * *", instruction="ping")
    scheduler.toggle(job.job_id, enabled=False)
    toggled = scheduler.toggle(job.job_id, enabled=True)
    assert toggled.enabled is True


def test_toggle_missing_job_raises(scheduler):
    with pytest.raises(KeyError):
        scheduler.toggle("nonexistent-id", enabled=False)


# ── /api/schedules endpoints ──────────────────────────────────────────────────

def test_list_schedules_empty(schedules_client):
    resp = schedules_client.get("/api/schedules/")
    assert resp.status_code == 200
    assert resp.json()["schedules"] == []


def test_create_schedule(schedules_client):
    payload = {
        "name": "Daily lint",
        "cron": "0 9 * * *",
        "instruction": "Run lint",
        "approval_gate": False,
    }
    resp = schedules_client.post("/api/schedules/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Daily lint"
    assert data["cron"] == "0 9 * * *"
    assert "job_id" in data


def test_list_schedules_after_create(schedules_client):
    schedules_client.post("/api/schedules/", json={
        "name": "Job A", "cron": "0 9 * * *", "instruction": "do A"
    })
    resp = schedules_client.get("/api/schedules/")
    assert resp.status_code == 200
    assert len(resp.json()["schedules"]) >= 1


def test_get_schedule(schedules_client):
    create_resp = schedules_client.post("/api/schedules/", json={
        "name": "Single", "cron": "0 9 * * *", "instruction": "do single"
    })
    job_id = create_resp.json()["job_id"]
    resp = schedules_client.get(f"/api/schedules/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["job_id"] == job_id


def test_get_schedule_not_found(schedules_client):
    resp = schedules_client.get("/api/schedules/nonexistent")
    assert resp.status_code == 404


def test_toggle_schedule_paused(schedules_client):
    create_resp = schedules_client.post("/api/schedules/", json={
        "name": "Toggleable", "cron": "0 9 * * *", "instruction": "toggle me"
    })
    job_id = create_resp.json()["job_id"]
    resp = schedules_client.patch(f"/api/schedules/{job_id}", json={"status": "paused"})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_toggle_schedule_active(schedules_client):
    create_resp = schedules_client.post("/api/schedules/", json={
        "name": "ReActivate", "cron": "0 9 * * *", "instruction": "reactivate"
    })
    job_id = create_resp.json()["job_id"]
    schedules_client.patch(f"/api/schedules/{job_id}", json={"status": "paused"})
    resp = schedules_client.patch(f"/api/schedules/{job_id}", json={"status": "active"})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_toggle_schedule_not_found(schedules_client):
    resp = schedules_client.patch("/api/schedules/bad-id", json={"status": "paused"})
    assert resp.status_code == 404


def test_run_schedule_now(schedules_client, scheduler):
    fired = []
    scheduler.set_on_fire(lambda job: fired.append(job.job_id))
    create_resp = schedules_client.post("/api/schedules/", json={
        "name": "Runnable", "cron": "0 9 * * *", "instruction": "run now"
    })
    job_id = create_resp.json()["job_id"]
    resp = schedules_client.post(f"/api/schedules/{job_id}/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "triggered"
    assert job_id in fired


def test_run_schedule_not_found(schedules_client):
    resp = schedules_client.post("/api/schedules/ghost/run")
    assert resp.status_code == 404


def test_delete_schedule(schedules_client):
    create_resp = schedules_client.post("/api/schedules/", json={
        "name": "Delete me", "cron": "0 9 * * *", "instruction": "bye"
    })
    job_id = create_resp.json()["job_id"]
    resp = schedules_client.delete(f"/api/schedules/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    # Confirm it's gone
    assert schedules_client.get(f"/api/schedules/{job_id}").status_code == 404


def test_schedule_runs_history(schedules_client):
    create_resp = schedules_client.post("/api/schedules/", json={
        "name": "History test", "cron": "0 9 * * *", "instruction": "count me"
    })
    job_id = create_resp.json()["job_id"]
    schedules_client.post(f"/api/schedules/{job_id}/run")
    resp = schedules_client.get(f"/api/schedules/{job_id}/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["schedule_id"] == job_id
    assert data["run_count"] >= 1


# ── /api/routing endpoints ────────────────────────────────────────────────────

def test_get_routing_policy(routing_client, mock_runtime_manager):
    with patch("routing.api.get_runtime_manager", return_value=mock_runtime_manager):
        resp = routing_client.get("/api/routing/policy")
    assert resp.status_code == 200
    data = resp.json()
    assert "policy" in data
    assert "never_use_paid_providers" in data["policy"]


def test_get_routing_stats(routing_client, mock_runtime_manager):
    with patch("routing.api.get_runtime_manager", return_value=mock_runtime_manager):
        resp = routing_client.get("/api/routing/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_decisions" in data
    assert "local_ratio" in data
    assert "decisions" in data
