"""Sync the README screenshot gallery from the organized screenshot inventory."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

START_MARKER = "<!-- README_UI_GALLERY:START -->"
END_MARKER = "<!-- README_UI_GALLERY:END -->"


@dataclass(frozen=True)
class Screenshot:
    path: str
    alt: str
    width: str = "92%"


@dataclass(frozen=True)
class GallerySection:
    heading: str
    summary: str
    screenshots: tuple[Screenshot, ...]


GALLERY: tuple[GallerySection, ...] = (
    GallerySection(
        heading="### 🛬 Login",
        summary="People can sign in through a simple starting page instead of touching raw config files.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-login.png", "LLM Relay login"),),
    ),
    GallerySection(
        heading="### 🧙 Setup Wizard",
        summary="The wizard helps you choose providers, models, runtimes, a default agent, and a cost policy.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-setup-wizard.png", "Setup Wizard"),),
    ),
    GallerySection(
        heading="### 💬 Chat",
        summary="This is where people talk to AI directly, using the providers and rules you set up.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-chat.png", "Direct Chat"),),
    ),
    GallerySection(
        heading="### 🗂 Task Board",
        summary="This makes AI work visible. You can see what is waiting, running, blocked, in review, or done.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-tasks-kanban.png", "Kanban Task Board"),),
    ),
    GallerySection(
        heading="### 🤖 Agent Roster",
        summary="This is your cast of AI helpers. Each agent can have its own model, runtime, specialty, and rules.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-agents.png", "Agent Roster"),),
    ),
    GallerySection(
        heading="### ⚙️ Runtimes",
        summary="This shows the engines behind the scenes that actually run your AI work.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-runtimes.png", "Agent Runtimes"),),
    ),
    GallerySection(
        heading="### 🛣 Routing Policy",
        summary="This is where you decide how smart, cheap, fast, or private the system should be when picking a model.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-routing.png", "Routing Policy"),),
    ),
    GallerySection(
        heading="### 🔌 Providers and Models",
        summary="This is where you connect local and cloud AI sources and decide what models are available.",
        screenshots=(
            Screenshot("docs/screenshots/readme/v3-providers.png", "Providers", width="48%"),
            Screenshot("docs/screenshots/readme/v3-models.png", "Models", width="48%"),
        ),
    ),
    GallerySection(
        heading="### 📚 Knowledge",
        summary="This is your team's memory: wiki pages, source material, and reusable context.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-knowledge.png", "Knowledge and Wiki"),),
    ),
    GallerySection(
        heading="### 🔭 Logs and activity",
        summary="This helps you answer, ‘what just happened?’",
        screenshots=(Screenshot("docs/screenshots/readme/v3-logs.png", "Logs"),),
    ),
    GallerySection(
        heading="### 🗓 Schedules",
        summary="This is how you make AI jobs run later or run again automatically.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-schedules.png", "Schedules"),),
    ),
    GallerySection(
        heading="### 🧭 Settings and guardrails",
        summary="Central settings keep defaults, policies, and integrations in one place instead of scattered config files.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-settings.png", "Settings"),),
    ),
    GallerySection(
        heading="### 🛡 Admin portal",
        summary="This gives admins a simpler place to manage access, controls, and system behavior.",
        screenshots=(Screenshot("docs/screenshots/readme/v3-admin.png", "Admin Portal"),),
    ),
    GallerySection(
        heading="### 🖥 Built-in web UI",
        summary="The proxy also ships a lightweight built-in app at `/app`, so you can ship a useful UI without the separate hosted dashboard.",
        screenshots=(Screenshot("docs/screenshots/webui/webui-app.png", "Built-in Web UI"),),
    ),
    GallerySection(
        heading="### 🔐 Built-in admin login",
        summary="The built-in admin surface has a dedicated login gate before exposing sensitive controls.",
        screenshots=(Screenshot("docs/screenshots/webui/webui-admin-login.png", "Built-in admin login"),),
    ),
    GallerySection(
        heading="### 🧰 Built-in admin workspace",
        summary="Once authenticated, admins can manage providers, workspaces, and runtime metadata from the in-proxy UI.",
        screenshots=(Screenshot("docs/screenshots/webui/webui-admin.png", "Built-in admin workspace"),),
    ),
)


def build_gallery() -> str:
    blocks: list[str] = []
    for section in GALLERY:
        blocks.append(section.heading)
        blocks.append("")
        blocks.append(section.summary)
        blocks.append("")
        if len(section.screenshots) == 1:
            shot = section.screenshots[0]
            blocks.append(
                f'<p align="center"><img src="{shot.path}" width="{shot.width}" alt="{shot.alt}"/></p>'
            )
        else:
            image_lines = ["<p align=\"center\">"]
            for index, shot in enumerate(section.screenshots):
                image_lines.append(
                    f'  <img src="{shot.path}" width="{shot.width}" alt="{shot.alt}"/>'
                )
                if index != len(section.screenshots) - 1:
                    image_lines.append("  &nbsp;")
            image_lines.append("</p>")
            blocks.append("\n".join(image_lines))
        blocks.append("")
    return "\n".join(blocks).strip()


def replace_gallery_block(readme_text: str, gallery_text: str) -> str:
    start = readme_text.index(START_MARKER) + len(START_MARKER)
    end = readme_text.index(END_MARKER)
    return f"{readme_text[:start]}\n{gallery_text}\n{readme_text[end:]}"


def sync_readme_gallery(readme_path: Path) -> None:
    current = readme_path.read_text(encoding="utf-8")
    updated = replace_gallery_block(current, build_gallery())
    readme_path.write_text(updated, encoding="utf-8")


def write_manifest(manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "heading": section.heading,
            "summary": section.summary,
            "screenshots": [asdict(shot) for shot in section.screenshots],
        }
        for section in GALLERY
    ]
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    readme_path = Path("README.md")
    sync_readme_gallery(readme_path)
    write_manifest(Path("docs/screenshots/manifest.json"))
    print(f"Updated: {readme_path}")
    print("Updated: docs/screenshots/manifest.json")


if __name__ == "__main__":
    main()
