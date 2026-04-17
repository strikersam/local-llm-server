from __future__ import annotations

import pytest

from webui.url_guard import validate_git_ref, validate_outbound_url


def test_metadata_ip_always_blocked():
    with pytest.raises(ValueError, match="metadata"):
        validate_outbound_url("http://169.254.169.254/latest/meta-data/")


def test_metadata_hostname_always_blocked():
    with pytest.raises(ValueError, match="metadata"):
        validate_outbound_url("http://metadata.google.internal/")


def test_scheme_file_rejected():
    with pytest.raises(ValueError, match="scheme"):
        validate_outbound_url("file:///etc/passwd")


def test_scheme_gopher_rejected():
    with pytest.raises(ValueError, match="scheme"):
        validate_outbound_url("gopher://example.com/")


def test_https_public_host_allowed():
    assert validate_outbound_url("https://api.openai.com/v1") == "https://api.openai.com/v1"


def test_localhost_allowed_by_default():
    # Local-first deployment: pointing at Ollama on localhost is the common case.
    assert validate_outbound_url("http://localhost:11434") == "http://localhost:11434"
    assert validate_outbound_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"


def test_localhost_blocked_in_strict_mode(monkeypatch):
    monkeypatch.setenv("STRICT_OUTBOUND", "1")
    with pytest.raises(ValueError, match="strict"):
        validate_outbound_url("http://127.0.0.1:8000")
    with pytest.raises(ValueError, match="strict"):
        validate_outbound_url("http://localhost:11434")


def test_private_rfc1918_blocked_in_strict_mode(monkeypatch):
    monkeypatch.setenv("STRICT_OUTBOUND", "1")
    with pytest.raises(ValueError, match="strict"):
        validate_outbound_url("http://10.0.0.1/")
    with pytest.raises(ValueError, match="strict"):
        validate_outbound_url("http://192.168.1.1/")


def test_git_scheme_allows_ssh():
    # git workspaces often use SSH URLs for private repos.
    assert (
        validate_outbound_url("ssh://git@github.com/org/repo.git", scheme="git")
        == "ssh://git@github.com/org/repo.git"
    )


def test_http_scheme_rejects_ssh():
    with pytest.raises(ValueError, match="scheme"):
        validate_outbound_url("ssh://example.com/foo", scheme="http")


def test_git_ref_valid():
    assert validate_git_ref("main") == "main"
    assert validate_git_ref("feature/new-thing") == "feature/new-thing"
    assert validate_git_ref("v1.2.3") == "v1.2.3"


def test_git_ref_rejects_flag_injection():
    with pytest.raises(ValueError):
        validate_git_ref("--upload-pack=evil")


def test_git_ref_rejects_traversal():
    with pytest.raises(ValueError):
        validate_git_ref("../other")
    with pytest.raises(ValueError):
        validate_git_ref("refs/.hidden")


def test_git_ref_rejects_shell_metacharacters():
    with pytest.raises(ValueError):
        validate_git_ref("main; rm -rf /")
    with pytest.raises(ValueError):
        validate_git_ref("main`id`")


def test_git_ref_rejects_empty():
    with pytest.raises(ValueError):
        validate_git_ref("")
    with pytest.raises(ValueError):
        validate_git_ref("   ")


def test_url_required():
    with pytest.raises(ValueError):
        validate_outbound_url("")
