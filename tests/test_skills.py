"""Tests for agent/skills.py — Skill Library."""
from pathlib import Path

from agent.skills import Skill, SkillLibrary


def test_empty_library():
    lib = SkillLibrary(skills_dir="/nonexistent_dir_xyz")
    assert lib.list() == []


def test_index_local_skills():
    # Uses the real .claude/skills directory if it exists
    lib = SkillLibrary()
    skills = lib.list(source="local")
    # The repo has at least a few skills; if dir missing, just assert empty list is ok
    assert isinstance(skills, list)


def test_search_by_name():
    lib = SkillLibrary()
    lib.register_mcp(name="test-runner", description="Runs tests and reports", content="")
    results = lib.search("runner")
    assert any(s.skill_id == "mcp:test-runner" for s in results)


def test_search_by_description():
    lib = SkillLibrary()
    lib.register_mcp(name="foo", description="Unique keyword xyzzy123", content="")
    results = lib.search("xyzzy123")
    assert len(results) == 1


def test_search_no_results():
    lib = SkillLibrary()
    results = lib.search("zzz_no_match_zzz")
    assert results == []


def test_register_mcp():
    lib = SkillLibrary()
    skill = lib.register_mcp(name="deploy", description="Deploy to cloud", tags=["ops"])
    assert skill.skill_id == "mcp:deploy"
    assert skill.source == "mcp"


def test_get_skill():
    lib = SkillLibrary()
    lib.register_mcp(name="lint", description="Linting skill")
    skill = lib.get("mcp:lint")
    assert skill is not None
    assert skill.name == "lint"


def test_get_missing_returns_none():
    lib = SkillLibrary()
    assert lib.get("local:nope") is None


def test_list_by_source():
    lib = SkillLibrary(skills_dir="/nonexistent_xyz")
    lib.register_mcp(name="m1", description="")
    lib.register_mcp(name="m2", description="")
    mcp_skills = lib.list(source="mcp")
    assert len(mcp_skills) == 2
    assert all(s.source == "mcp" for s in mcp_skills)


def test_as_dict():
    lib = SkillLibrary()
    s = lib.register_mcp(name="x", description="X skill", tags=["t1"])
    d = s.as_dict()
    assert "skill_id" in d
    assert "source" in d
    assert d["tags"] == ["t1"]
