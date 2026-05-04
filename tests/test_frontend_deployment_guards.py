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


# ── Setup Wizard checkbox visibility regression guards ──────────────────────
# These tests prevent the recurring regression where global `appearance:none`
# on <input> hides native checkboxes in the Setup Wizard.

def test_index_css_restores_checkbox_appearance() -> None:
    """index.css must override appearance:none for checkboxes/radios."""
    css = _read("frontend/src/index.css")
    # The override block must exist
    assert 'input[type="checkbox"]' in css, (
        "index.css is missing the input[type='checkbox'] override; "
        "native checkboxes will be invisible due to global appearance:none."
    )


def test_index_css_checkbox_override_is_not_none() -> None:
    """The checkbox appearance override must NOT set appearance:none (that would keep them hidden)."""
    css = _read("frontend/src/index.css")
    lines = css.splitlines()
    in_checkbox_block = False
    for line in lines:
        if 'input[type="checkbox"]' in line:
            in_checkbox_block = True
        stripped = line.strip()
        if in_checkbox_block and "appearance" in stripped and not stripped.startswith("/*") and not stripped.startswith("*"):
            assert "none" not in stripped, (
                f"Checkbox block sets appearance:none — checkboxes will be invisible. "
                f"Offending line: {stripped!r}"
            )
        if in_checkbox_block and stripped == "}":
            break


def test_index_css_checkbox_uses_auto_appearance() -> None:
    """The checkbox appearance override must use 'auto' to request native rendering.

    'revert' is fragile under layered cascade rules; 'auto' is the explicit,
    standards-compliant value that tells the browser to render a native checkbox.
    """
    css = _read("frontend/src/index.css")
    lines = css.splitlines()
    in_checkbox_block = False
    found_auto = False
    for line in lines:
        if 'input[type="checkbox"]' in line:
            in_checkbox_block = True
        if in_checkbox_block and "appearance" in line and "auto" in line:
            found_auto = True
        if in_checkbox_block and line.strip() == "}":
            break
    assert found_auto, (
        "Checkbox appearance override does not use 'appearance: auto'. "
        "Use 'appearance: auto' (not 'revert') so checkboxes render natively "
        "across all browsers and cascade configurations."
    )


def test_setup_wizard_renders_checkbox_inputs_for_all_providers() -> None:
    """SetupWizardPage must render <input type='checkbox'> for each provider toggle."""
    wizard = _read("frontend/src/pages/SetupWizardPage.js")
    # Provider checkboxes (Step 1) — one per provider
    providers = ["useNvidiaNim", "useOllama", "useOpenAI", "useAnthropic", "useGoogle", "useAzure", "useCopilot"]
    for state_var in providers:
        assert f"checked={{{state_var}}}" in wizard, (
            f"Setup Wizard Step 1 is missing a checkbox bound to {state_var}; "
            f"the {state_var} provider toggle will not be shown to the user."
        )


def test_setup_wizard_step3_renders_runtime_checkboxes() -> None:
    """Step 3 runtime config must render checkboxes for each runtime."""
    wizard = _read("frontend/src/pages/SetupWizardPage.js")
    for runtime_var in ["enableHermes", "enableOpenCode", "enableTaskHarness", "enableAider"]:
        assert runtime_var in wizard, (
            f"Setup Wizard Step 3 is missing runtime variable {runtime_var}; "
            f"that runtime's checkbox will not render."
        )
    # The runtime list map must use input type checkbox
    assert 'input type="checkbox"' in wizard or "type=\"checkbox\"" in wizard, (
        "Step 3 runtime list does not render <input type='checkbox'>; "
        "users will not see runtime selection checkboxes."
    )
