from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_public_bootstrap_route_exists_for_prelogin_setup() -> None:
    app = _read("frontend/src/App.js")
    assert '<Route path="/bootstrap" element={<SetupWizardPage />} />' in app


def test_login_page_links_to_bootstrap_when_backend_is_missing() -> None:
    login_page = _read("frontend/src/pages/LoginPage.js")
    assert "Need to connect a backend first?" in login_page
    assert 'Link to="/bootstrap"' in login_page


def test_api_redirects_respect_public_and_backend_paths() -> None:
    api = _read("frontend/src/api.js")
    assert "getApiUrl('/api/auth/refresh')" in api
    assert "window.location.href = getPublicPath('/login')" in api


def test_settings_oauth_origin_uses_current_backend_configuration() -> None:
    settings = _read("frontend/src/pages/SettingsPage.js")
    assert "function getBackendOrigin()" in settings
    assert "const backendOrigin = getBackendOrigin();" in settings
