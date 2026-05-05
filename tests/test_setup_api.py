from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from setup.api import clear_wizard_state_cache, set_wizard_state_collection, setup_router


class _FakeWizardCollection:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    async def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        user_id = query.get("user_id")
        doc = self.docs.get(str(user_id))
        if doc is None:
            return None
        return dict(doc)

    async def replace_one(self, query: dict, replacement: dict, upsert: bool = False) -> None:
        user_id = str(query.get("user_id") or replacement.get("user_id"))
        self.docs[user_id] = dict(replacement)

    async def delete_one(self, query: dict) -> SimpleNamespace:
        user_id = str(query.get("user_id"))
        existed = user_id in self.docs
        self.docs.pop(user_id, None)
        return SimpleNamespace(deleted_count=1 if existed else 0)


def _setup_client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = {"email": "admin@example.com", "role": "admin"}
        return await call_next(request)

    app.include_router(setup_router)
    return TestClient(app)


def test_setup_state_persists_in_collection_across_cache_resets() -> None:
    collection = _FakeWizardCollection()
    set_wizard_state_collection(collection)
    clear_wizard_state_cache()
    client = _setup_client()

    try:
        save_response = client.put(
            "/api/setup/step/1",
            json={
                "use_nvidia_nim": True,
                "use_ollama": False,
                "ollama_base_url": "http://localhost:11434",
            },
        )
        assert save_response.status_code == 200, save_response.text

        complete_response = client.post("/api/setup/complete")
        assert complete_response.status_code == 200, complete_response.text

        clear_wizard_state_cache()

        state_response = client.get("/api/setup/state")
        assert state_response.status_code == 200, state_response.text
        payload = state_response.json()
        assert payload["completed"] is True
        assert payload["step1_providers"]["use_nvidia_nim"] is True
        assert payload["user_id"] == "admin@example.com"
    finally:
        clear_wizard_state_cache()
        set_wizard_state_collection(None)


def test_reset_wizard_removes_persisted_collection_state() -> None:
    collection = _FakeWizardCollection()
    set_wizard_state_collection(collection)
    clear_wizard_state_cache()
    client = _setup_client()

    try:
        save_response = client.put(
            "/api/setup/step/5",
            json={
                "never_use_paid_providers": True,
                "require_approval_before_paid": True,
                "enable_langfuse": True,
                "langfuse_host": "https://trace.example.com",
            },
        )
        assert save_response.status_code == 200, save_response.text
        assert "admin@example.com" in collection.docs

        reset_response = client.post("/api/setup/reset", json={"user_id": "admin@example.com"})
        assert reset_response.status_code == 200, reset_response.text

        clear_wizard_state_cache()
        state_response = client.get("/api/setup/state")
        assert state_response.status_code == 200, state_response.text
        payload = state_response.json()
        assert payload["completed"] is False
        assert payload["step5_policy"] == {}
    finally:
        clear_wizard_state_cache()
        set_wizard_state_collection(None)
