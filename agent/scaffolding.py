"""agent/scaffolding.py — Project Scaffolding

Creates new project skeletons from named templates so that when you ask the
agent to "start a new project", you get a working skeleton rather than an
empty folder.

Built-in templates: ``python-library``, ``fastapi-service``, ``cli-tool``.
Custom templates can be loaded from a directory of JSON files.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("qwen-scaffolding")

# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

_BUILTIN: dict[str, dict[str, Any]] = {
    "python-library": {
        "name": "python-library",
        "description": "Python library with src layout, pytest, and type annotations",
        "tags": ["python", "library"],
        "files": {
            "src/__init__.py": '"""Package root."""\n',
            "tests/__init__.py": "",
            "tests/test_sample.py": "def test_placeholder():\n    assert True\n",
            "pyproject.toml": '[project]\nname = "my-lib"\nversion = "0.1.0"\n',
            "README.md": "# My Library\n\nInstall: `pip install .`\n",
        },
    },
    "fastapi-service": {
        "name": "fastapi-service",
        "description": "FastAPI service with a health endpoint and tests",
        "tags": ["python", "fastapi", "service"],
        "files": {
            "main.py": (
                "from fastapi import FastAPI\n"
                "app = FastAPI()\n\n"
                '@app.get("/health")\n'
                "def health():\n"
                '    return {"status": "ok"}\n'
            ),
            "tests/__init__.py": "",
            "tests/test_health.py": (
                "from fastapi.testclient import TestClient\n"
                "from main import app\n\n"
                "def test_health():\n"
                '    r = TestClient(app).get("/health")\n'
                "    assert r.status_code == 200\n"
            ),
            "requirements.txt": "fastapi\nhttpx\npytest\n",
        },
    },
    "cli-tool": {
        "name": "cli-tool",
        "description": "Click-based CLI tool with basic command structure",
        "tags": ["python", "cli"],
        "files": {
            "cli.py": (
                "import click\n\n"
                "@click.group()\n"
                "def main(): pass\n\n"
                "@main.command()\n"
                "def run():\n"
                '    """Run the tool."""\n'
                '    click.echo("Hello!")\n\n'
                'if __name__ == "__main__":\n'
                "    main()\n"
            ),
            "requirements.txt": "click\n",
            "README.md": "# CLI Tool\n\nUsage: `python cli.py run`\n",
        },
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Template:
    name: str
    description: str
    files: dict[str, str]   # relative_path → file_content
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "file_count": len(self.files),
        }


@dataclass
class ScaffoldResult:
    template_name: str
    target_dir: str
    files_created: list[str]
    success: bool
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "template_name": self.template_name,
            "target_dir": self.target_dir,
            "files_created": self.files_created,
            "success": self.success,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Scaffolder
# ---------------------------------------------------------------------------


class ProjectScaffolder:
    """Apply named project templates to a target directory.

    Usage::

        s = ProjectScaffolder()
        result = s.apply("fastapi-service", "/tmp/my-project")
        print(result.files_created)
    """

    def __init__(self, templates_dir: str | Path | None = None) -> None:
        self._templates: dict[str, Template] = {
            name: Template(
                name=t["name"],
                description=t["description"],
                files=t["files"],
                tags=t.get("tags", []),
            )
            for name, t in _BUILTIN.items()
        }
        if templates_dir:
            self._load_dir(Path(templates_dir))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list(self) -> list[Template]:
        return list(self._templates.values())

    def get(self, name: str) -> Template | None:
        return self._templates.get(name)

    def apply(
        self,
        template_name: str,
        target_dir: str | Path,
        *,
        overwrite: bool = False,
    ) -> ScaffoldResult:
        """Write template files into *target_dir*.

        Skips existing files unless *overwrite=True*.
        """
        template = self._templates.get(template_name)
        if not template:
            return ScaffoldResult(
                template_name=template_name,
                target_dir=str(target_dir),
                files_created=[],
                success=False,
                error=f"Template {template_name!r} not found",
            )

        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        created: list[str] = []

        try:
            for rel_path, content in template.files.items():
                dest = target / rel_path
                if dest.exists() and not overwrite:
                    log.debug("Skipping existing file: %s", dest)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                created.append(str(dest))

            log.info(
                "Scaffolded %r → %s (%d files created)",
                template_name,
                target,
                len(created),
            )
            return ScaffoldResult(
                template_name=template_name,
                target_dir=str(target),
                files_created=created,
                success=True,
            )
        except Exception as exc:
            return ScaffoldResult(
                template_name=template_name,
                target_dir=str(target),
                files_created=created,
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_dir(self, directory: Path) -> None:
        for p in directory.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                t = Template(
                    name=data["name"],
                    description=data.get("description", ""),
                    files=data.get("files", {}),
                    tags=data.get("tags", []),
                )
                self._templates[t.name] = t
                log.info("Loaded template %r from %s", t.name, p)
            except Exception as exc:
                log.warning("Could not load template %s: %s", p, exc)
