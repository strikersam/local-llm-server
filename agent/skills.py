"""agent/skills.py — Skill Library

Indexes and searches agent skills from local SKILL.md files and MCP-hosted
skill packs.  Skills are discoverable by keyword search across their name,
description, and full content.

Local skills are auto-discovered from ``.claude/skills/**/SKILL.md``.
MCP-hosted skills can be registered via :meth:`register_mcp`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("qwen-skills")


@dataclass
class Skill:
    skill_id: str           # "local:<name>" or "mcp:<name>"
    name: str
    description: str
    source: str             # "local" | "mcp"
    path: str | None = None
    tags: list[str] = field(default_factory=list)
    content: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "path": self.path,
            "tags": self.tags,
        }


class SkillLibrary:
    """Discover, search, and retrieve agent skills.

    Usage::

        lib = SkillLibrary()           # auto-indexes .claude/skills/
        results = lib.search("test")
        skill = lib.get("local:test-first-executor")
    """

    _DEFAULT_DIR = ".claude/skills"

    def __init__(self, skills_dir: str | Path | None = None) -> None:
        self._skills: dict[str, Skill] = {}
        search_dir = Path(skills_dir) if skills_dir else Path(self._DEFAULT_DIR)
        if search_dir.exists():
            self._index_local(search_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list(self, source: str | None = None) -> list[Skill]:
        skills = list(self._skills.values())
        if source:
            skills = [s for s in skills if s.source == source]
        return skills

    def search(self, query: str) -> list[Skill]:
        """Full-text search across name, description, and content."""
        q = query.lower()
        results = []
        for skill in self._skills.values():
            haystack = (
                skill.name.lower()
                + " "
                + skill.description.lower()
                + " "
                + " ".join(skill.tags).lower()
                + " "
                + (skill.content or "").lower()
            )
            if q in haystack:
                results.append(skill)
        return results

    def get(self, skill_id: str) -> Skill | None:
        return self._skills.get(skill_id)

    def register_mcp(
        self,
        *,
        name: str,
        description: str,
        content: str = "",
        tags: list[str] | None = None,
    ) -> Skill:
        """Register an MCP-hosted skill pack entry."""
        skill_id = f"mcp:{name}"
        skill = Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            source="mcp",
            tags=tags or [],
            content=content,
        )
        self._skills[skill_id] = skill
        log.info("MCP skill registered: %s", skill_id)
        return skill

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _index_local(self, directory: Path) -> None:
        indexed = 0
        for skill_md in directory.rglob("SKILL.md"):
            try:
                content = skill_md.read_text(encoding="utf-8")
                name = skill_md.parent.name
                skill_id = f"local:{name}"
                skill = Skill(
                    skill_id=skill_id,
                    name=name,
                    description=self._extract_description(content),
                    source="local",
                    path=str(skill_md),
                    content=content,
                )
                self._skills[skill_id] = skill
                indexed += 1
            except Exception as exc:
                log.debug("Could not index %s: %s", skill_md, exc)
        log.info("Indexed %d local skills from %s", indexed, directory)

    @staticmethod
    def _extract_description(markdown: str) -> str:
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
                return stripped[:200]
        return ""
