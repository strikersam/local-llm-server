"""Integration tests for all new feature API routes in proxy.py."""
import pytest
from fastapi.testclient import TestClient

import proxy


def _fake_auth():
    return proxy.AuthContext(
        key="test-key",
        email="tester@test.com",
        department="eng",
        key_id=None,
        source="legacy",
    )


@pytest.fixture(autouse=True)
def _auth_override():
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth
    yield
    proxy.app.dependency_overrides.pop(proxy.verify_api_key, None)


@pytest.fixture()
def client():
    return TestClient(proxy.app)


# ─── Memory ───────────────────────────────────────────────────────────────────

def test_memory_list_empty(client):
    r = client.get("/agent/memory")
    assert r.status_code == 200
    assert "snapshots" in r.json()


def test_memory_restore_missing(client):
    r = client.get("/agent/memory/as_nonexistent999")
    assert r.status_code == 404


def test_memory_delete_missing(client):
    r = client.delete("/agent/memory/as_gone")
    assert r.status_code == 200
    assert r.json()["deleted"] is False


# ─── Context ──────────────────────────────────────────────────────────────────

def test_context_inspect(client):
    r = client.post(
        "/agent/context/inspect",
        json={"messages": [{"role": "user", "content": "hello world"}]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "stats" in data
    assert data["stats"]["message_count"] == 1


def test_context_compress_reactive(client):
    messages = [{"role": "user", "content": "x" * 100}] * 10
    r = client.post(
        "/agent/context/compress",
        json={"messages": messages, "strategy": "reactive"},
    )
    assert r.status_code == 200
    assert "messages" in r.json()


def test_context_compress_invalid_strategy(client):
    r = client.post(
        "/agent/context/compress",
        json={"messages": [{"role": "user", "content": "hi"}], "strategy": "bogus"},
    )
    assert r.status_code == 422


# ─── Permissions ──────────────────────────────────────────────────────────────

def test_permissions_on_new_session(client):
    r = client.post("/agent/sessions", json={})
    assert r.status_code == 200
    sid = r.json()["session_id"]

    r = client.get(f"/agent/sessions/{sid}/permissions")
    assert r.status_code == 200
    assert "level" in r.json()


def test_permissions_unknown_session(client):
    r = client.get("/agent/sessions/as_nope999/permissions")
    assert r.status_code == 404


# ─── Token Budget ─────────────────────────────────────────────────────────────

def test_budget_set_and_get(client):
    r = client.put("/agent/budget/s_test1", json={"cap": 5000})
    assert r.status_code == 200
    assert r.json()["cap"] == 5000

    r = client.get("/agent/budget/s_test1")
    assert r.status_code == 200
    assert r.json()["cap"] == 5000


def test_budget_get_missing(client):
    r = client.get("/agent/budget/s_nobody_xyz")
    assert r.status_code == 404


def test_budget_list(client):
    client.put("/agent/budget/s_listA", json={"cap": 100})
    r = client.get("/agent/budget")
    assert r.status_code == 200
    assert "budgets" in r.json()


# ─── Scheduler ────────────────────────────────────────────────────────────────

def test_scheduler_create_and_list(client):
    r = client.post(
        "/agent/scheduler/jobs",
        json={"name": "test-job", "cron": "0 9 * * 1", "instruction": "Run lint"},
    )
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    r = client.get("/agent/scheduler/jobs")
    assert r.status_code == 200
    ids = [j["job_id"] for j in r.json()["jobs"]]
    assert job_id in ids


def test_scheduler_trigger(client):
    r = client.post(
        "/agent/scheduler/jobs",
        json={"name": "fire", "cron": "0 0 1 1 *", "instruction": "do it"},
    )
    job_id = r.json()["job_id"]
    r = client.post(f"/agent/scheduler/jobs/{job_id}/trigger")
    assert r.status_code == 200
    assert r.json()["run_count"] == 1


def test_scheduler_delete(client):
    r = client.post(
        "/agent/scheduler/jobs",
        json={"name": "del-job", "cron": "* * * * *", "instruction": "x"},
    )
    job_id = r.json()["job_id"]
    r = client.delete(f"/agent/scheduler/jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_scheduler_trigger_not_found(client):
    r = client.post("/agent/scheduler/jobs/job_nope999/trigger")
    assert r.status_code == 404


# ─── Playbooks ────────────────────────────────────────────────────────────────

def test_playbook_register_and_list(client):
    r = client.post(
        "/agent/playbooks",
        json={
            "name": "daily",
            "description": "Daily ops",
            "steps": [{"instruction": "Step 1"}, {"instruction": "Step 2"}],
        },
    )
    assert r.status_code == 200
    pb_id = r.json()["playbook_id"]

    r = client.get("/agent/playbooks")
    ids = [p["playbook_id"] for p in r.json()["playbooks"]]
    assert pb_id in ids


def test_playbook_run(client):
    r = client.post(
        "/agent/playbooks",
        json={"name": "runme", "description": "", "steps": [{"instruction": "go"}]},
    )
    pb_id = r.json()["playbook_id"]
    r = client.post(f"/agent/playbooks/{pb_id}/run")
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_playbook_delete(client):
    r = client.post(
        "/agent/playbooks",
        json={"name": "gone", "description": "", "steps": [{"instruction": "x"}]},
    )
    pb_id = r.json()["playbook_id"]
    r = client.delete(f"/agent/playbooks/{pb_id}")
    assert r.json()["deleted"] is True


def test_playbook_run_not_found(client):
    r = client.post("/agent/playbooks/pb_nope999/run")
    assert r.status_code == 404


# ─── Watchdog ─────────────────────────────────────────────────────────────────

def test_watchdog_add_and_list(client):
    r = client.post(
        "/agent/watchdog/resources",
        json={"name": "API", "kind": "url", "target": "http://localhost:9999", "action": "notify"},
    )
    assert r.status_code == 200
    rid = r.json()["resource_id"]

    r = client.get("/agent/watchdog/resources")
    ids = [r2["resource_id"] for r2 in r.json()["resources"]]
    assert rid in ids


def test_watchdog_remove(client):
    r = client.post(
        "/agent/watchdog/resources",
        json={"name": "del", "kind": "url", "target": "http://x"},
    )
    rid = r.json()["resource_id"]
    r = client.delete(f"/agent/watchdog/resources/{rid}")
    assert r.json()["removed"] is True


# ─── Scaffolding ──────────────────────────────────────────────────────────────

def test_scaffolding_list(client):
    r = client.get("/agent/scaffolding/templates")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["templates"]]
    assert "python-library" in names


def test_scaffolding_apply(tmp_path, client):
    r = client.post(
        "/agent/scaffolding/apply",
        json={"template": "cli-tool", "target_dir": str(tmp_path / "cli")},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_scaffolding_unknown_template(tmp_path, client):
    r = client.post(
        "/agent/scaffolding/apply",
        json={"template": "nope", "target_dir": str(tmp_path / "x")},
    )
    assert r.json()["success"] is False


# ─── Skills ───────────────────────────────────────────────────────────────────

def test_skills_list(client):
    r = client.get("/agent/skills")
    assert r.status_code == 200
    assert "skills" in r.json()


def test_skills_search(client):
    client.post(
        "/agent/skills/mcp",
        json={"name": "search-me", "description": "Unique_xyz_skill_abc"},
    )
    r = client.get("/agent/skills/search?q=Unique_xyz_skill_abc")
    assert r.status_code == 200
    assert len(r.json()["skills"]) >= 1


def test_skills_register_mcp(client):
    r = client.post(
        "/agent/skills/mcp",
        json={"name": "deploy-skill2", "description": "Deploy helper", "tags": ["ops"]},
    )
    assert r.status_code == 200
    assert r.json()["skill_id"] == "mcp:deploy-skill2"


# ─── Commits ──────────────────────────────────────────────────────────────────

def test_commit_log(client):
    r = client.get("/agent/commits")
    assert r.status_code == 200
    assert "commits" in r.json()


# ─── Terminal ─────────────────────────────────────────────────────────────────

def test_terminal_snapshot(client):
    r = client.get("/agent/terminal/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert "lines" in data
    assert "cols" in data


def test_terminal_run(client):
    r = client.post(
        "/agent/terminal/run",
        json={"command": ["echo", "hello"]},
    )
    assert r.status_code == 200
    assert "hello" in r.json()["stdout"]


# ─── Browser ──────────────────────────────────────────────────────────────────

def test_browser_start(client):
    r = client.post("/agent/browser/start")
    assert r.status_code == 200


def test_browser_stop(client):
    r = client.post("/agent/browser/stop")
    assert r.status_code == 200


def test_browser_action_navigate_no_playwright(client):
    r = client.post(
        "/agent/browser/action",
        json={"action": "navigate", "url": "https://example.com"},
    )
    # Returns 200 with available=False if playwright not installed
    assert r.status_code in (200, 400)


# ─── Voice ────────────────────────────────────────────────────────────────────

def test_voice_status(client):
    r = client.get("/agent/voice/status")
    assert r.status_code == 200
    assert "mic_available" in r.json()


def test_voice_transcribe_empty(client):
    import base64
    r = client.post(
        "/agent/voice/transcribe",
        json={"audio_b64": base64.b64encode(b"").decode()},
    )
    assert r.status_code == 200
    assert r.json()["source"] == "stub"


def test_voice_transcribe_invalid_b64(client):
    r = client.post(
        "/agent/voice/transcribe",
        json={"audio_b64": "not-valid-base64!!!"},
    )
    assert r.status_code == 400


# ─── Background Agent ─────────────────────────────────────────────────────────

def test_background_submit_and_list(client):
    r = client.post(
        "/agent/background/tasks",
        json={"kind": "manual", "payload": {"instruction": "do work"}},
    )
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    r = client.get("/agent/background/tasks")
    assert r.status_code == 200
    ids = [t["task_id"] for t in r.json()["tasks"]]
    assert task_id in ids


def test_background_get_task(client):
    r = client.post(
        "/agent/background/tasks",
        json={"kind": "webhook", "payload": {}},
    )
    task_id = r.json()["task_id"]
    r = client.get(f"/agent/background/tasks/{task_id}")
    assert r.status_code == 200
    assert r.json()["task_id"] == task_id


def test_background_task_not_found(client):
    r = client.get("/agent/background/tasks/bg_nope999")
    assert r.status_code == 404
