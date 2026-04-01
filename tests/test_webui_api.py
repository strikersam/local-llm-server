from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import proxy
from admin_auth import AdminIdentity
from webui.config_store import JsonConfigStore, JsonStorePaths
from webui.providers import ProviderManager
from webui.workspaces import WorkspaceManager


def _fake_user_auth():
    return proxy.AuthContext(
        key="test-key",
        email="tester@example.com",
        department="engineering",
        key_id="kid_test",
        source="legacy",
    )


def test_ui_bootstrap_is_public():
    client = TestClient(proxy.app)
    resp = client.get("/ui/api/bootstrap")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ui_providers_and_workspaces_use_app_state(tmp_path: Path, monkeypatch):
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_user_auth

    store = JsonConfigStore(
        JsonStorePaths(
            providers=tmp_path / "providers.json",
            workspaces=tmp_path / "workspaces.json",
        )
    )
    providers = ProviderManager(store)
    workspaces = WorkspaceManager(store, default_local_root=tmp_path)
    providers.ensure_defaults(local_base_url="http://localhost:11434")
    workspaces.ensure_defaults()

    proxy.app.state.webui_providers = providers
    proxy.app.state.webui_workspaces = workspaces

    client = TestClient(proxy.app)
    resp = client.get("/ui/api/providers")
    assert resp.status_code == 200
    assert any(p["provider_id"] == "prov_local" for p in resp.json()["providers"])

    wresp = client.get("/ui/api/workspaces")
    assert wresp.status_code == 200
    assert any(w["workspace_id"] == "ws_current" for w in wresp.json()["workspaces"])

    proxy.app.dependency_overrides.clear()


def test_admin_can_create_provider_via_webui_admin_api(tmp_path: Path):
    store = JsonConfigStore(
        JsonStorePaths(
            providers=tmp_path / "providers.json",
            workspaces=tmp_path / "workspaces.json",
        )
    )
    providers = ProviderManager(store)
    workspaces = WorkspaceManager(store, default_local_root=tmp_path)
    providers.ensure_defaults(local_base_url="http://localhost:11434")
    workspaces.ensure_defaults()

    proxy.app.state.webui_providers = providers
    proxy.app.state.webui_workspaces = workspaces

    session = proxy.ADMIN_AUTH.sessions.create(AdminIdentity(username="swami", auth_source="windows"))
    client = TestClient(proxy.app)
    resp = client.post(
        "/admin/api/providers",
        headers={"Authorization": f"Bearer {session.token}"},
        json={
            "name": "Example remote",
            "base_url": "https://example.com",
            "api_key": "sk-test",
            "default_model": "gpt-test",
            "default_temperature": 0.3,
            "kind": "openai_compat",
        },
    )
    assert resp.status_code == 200
    provider = resp.json()["provider"]
    assert provider["name"] == "Example remote"
    assert provider["has_api_key"] is True

