"""Tests for agent/permissions.py — Adaptive Permissions."""
from agent.permissions import AdaptivePermissions


def _msgs(*contents: str) -> list[dict]:
    return [{"role": "user", "content": c} for c in contents]


def test_read_only_default():
    ap = AdaptivePermissions()
    result = ap.assess([])
    assert result.level == "read_only"
    assert result.confidence < 0.5


def test_read_only_from_read_signals():
    ap = AdaptivePermissions()
    result = ap.assess(_msgs("please search for the function", "find the bug"))
    assert result.level == "read_only"
    assert result.read_signals


def test_read_write_from_write_signals():
    ap = AdaptivePermissions()
    result = ap.assess(_msgs("create a new file", "edit the function"))
    assert result.level == "read_write"
    assert "create" in result.write_signals or "edit" in result.write_signals


def test_full_access_from_risky_signals():
    ap = AdaptivePermissions()
    result = ap.assess(_msgs("sudo rm the directory", "destroy all logs"))
    assert result.level == "full_access"
    assert result.risky_signals


def test_has_write_permission_false():
    ap = AdaptivePermissions()
    assert ap.has_write_permission(_msgs("show me the file")) is False


def test_has_write_permission_true():
    ap = AdaptivePermissions()
    assert ap.has_write_permission(_msgs("please update this function")) is True


def test_assessment_as_dict():
    ap = AdaptivePermissions()
    d = ap.assess(_msgs("read the file")).as_dict()
    assert "level" in d
    assert "confidence" in d
    assert "summary" in d


def test_confidence_increases_with_more_signals():
    ap = AdaptivePermissions()
    few = ap.assess(_msgs("write something"))
    many = ap.assess(_msgs("write create update modify delete patch replace"))
    assert many.confidence >= few.confidence
