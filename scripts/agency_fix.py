#!/usr/bin/env python3
"""Agency Fix Agent — uses NVIDIA NIM (or Anthropic) to analyse failing tests and apply fixes.

Usage:
    python scripts/agency_fix.py <pytest-output-file>

Exit codes:
    0  All tests green after fix (or were already green)
    1  Could not fix tests
    2  No LLM API key available
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)
log = logging.getLogger("qwen-proxy")

REPO_ROOT = Path(__file__).resolve().parent.parent

NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NVIDIA_MODEL = os.environ.get("AGENCY_MODEL", "qwen/qwen2.5-coder-32b-instruct")
ANTHROPIC_MODEL = "claude-opus-4-7"

MAX_ITERATIONS = 3
MAX_CONTEXT_CHARS = 40_000


def call_llm(messages: list[dict[str, str]]) -> str:
    if NVIDIA_KEY:
        try:
            from openai import OpenAI  # type: ignore[import]
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=NVIDIA_KEY,
            )
            resp = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.1,
                max_tokens=8192,
            )
            content = resp.choices[0].message.content if resp.choices else None
            if content:
                return content
            log.warning("NVIDIA NIM returned empty content — falling back to Anthropic")
        except Exception as exc:
            log.warning("NVIDIA NIM call failed (%s) — falling back to Anthropic", exc)

    if ANTHROPIC_KEY:
        try:
            import anthropic  # type: ignore[import]
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            system = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msgs = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
            resp = client.messages.create(
                model=ANTHROPIC_MODEL,
                system=system,
                messages=user_msgs,  # type: ignore[arg-type]
                max_tokens=8192,
            )
            if not resp.content:
                log.warning("Anthropic returned empty content list")
                return ""
            return resp.content[0].text  # type: ignore[union-attr]
        except Exception as exc:
            log.warning("Anthropic call failed (%s)", exc)

    return ""


def run_pytest(extra_args: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header", "--timeout=120"]
    if extra_args:
        cmd.extend(extra_args)
    env = {**os.environ}
    env.setdefault("API_KEYS", "ci-test-key")
    env.setdefault("OLLAMA_BASE", "http://localhost:11434")
    env.setdefault("ROUTER_HEALTH_CHECK_ENABLED", "false")
    env.setdefault("MONGO_URL", "mongodb://localhost:27017")
    env.setdefault("DB_NAME", "llm_wiki_dashboard_ci")
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


def extract_failing_tests(output: str) -> list[str]:
    return re.findall(r"^FAILED\s+(\S+)", output, re.MULTILINE)


def read_file_safe(path: Path, max_chars: int = 8000) -> str:
    try:
        text = path.read_text(errors="replace")
        return text[:max_chars] if len(text) > max_chars else text
    except OSError:
        return ""


def collect_context(failing: list[str], pytest_output: str) -> str:
    parts: list[str] = [f"## Pytest output\n```\n{pytest_output[:8000]}\n```\n"]
    seen_files: set[str] = set()
    for test_id in failing:
        file_part = test_id.split("::")[0]
        if file_part not in seen_files:
            seen_files.add(file_part)
            fpath = REPO_ROOT / file_part
            content = read_file_safe(fpath)
            if content:
                parts.append(f"## {file_part}\n```python\n{content}\n```\n")
    combined = "\n".join(parts)
    return combined[:MAX_CONTEXT_CHARS]


def collect_source_files(failing: list[str]) -> str:
    src_files: dict[str, str] = {}
    for py_file in REPO_ROOT.glob("**/*.py"):
        if any(skip in py_file.parts for skip in (".venv", "node_modules", "__pycache__", ".git")):
            continue
        if py_file.parts[len(REPO_ROOT.parts):][0:1] == ("tests",):
            continue
        src_files[str(py_file.relative_to(REPO_ROOT))] = read_file_safe(py_file, max_chars=4000)
    priority = {"backend/server.py", "proxy.py", "provider_router.py"}
    result_parts: list[str] = []
    total = 0
    for rel, content in src_files.items():
        if rel in priority or total < 15_000:
            chunk = f"## {rel}\n```python\n{content}\n```\n"
            result_parts.append(chunk)
            total += len(chunk)
        if total > 20_000:
            break
    return "\n".join(result_parts)


def build_prompt(pytest_output: str, failing: list[str], iteration: int) -> list[dict[str, str]]:
    context = collect_context(failing, pytest_output)
    src = collect_source_files(failing)

    system = (
        "You are an expert Python engineer working on the local-llm-server project.\n"
        "Your job is to fix failing pytest tests by editing source files (NOT the tests themselves).\n"
        "Never skip, xfail, or comment out tests.\n"
        "Respond ONLY with a JSON object in this exact schema:\n"
        "{\n"
        '  "explanation": "<brief diagnosis>",\n'
        '  "edits": [\n'
        "    {\n"
        '      "file": "<relative path from repo root>",\n'
        '      "old": "<exact substring to replace — must be unique in the file>",\n'
        '      "new": "<replacement text>"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "If no source edit can fix the failure, return {\"explanation\": \"<reason>\", \"edits\": []}.\n"
        "The JSON must be parseable. Do NOT wrap it in markdown code fences."
    )

    user = (
        f"Iteration {iteration}/{MAX_ITERATIONS}. Fix these failing tests:\n"
        + "\n".join(f"  - {t}" for t in failing)
        + "\n\n"
        + context
        + "\n\n## Source context\n"
        + src
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_edits(response: str) -> dict[str, Any]:
    response = re.sub(r"```(?:json)?\n?", "", response).strip().rstrip("`")
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return {"explanation": "Could not parse LLM response", "edits": []}


_BLOCKED_TOP_DIRS = frozenset({"tests", ".github", "scripts"})
_BLOCKED_FILES = frozenset({
    "pytest.ini", "setup.cfg", "pyproject.toml", "conftest.py",
    "requirements.txt", "requirements-dev.txt", "CLAUDE.md",
})
_BLOCKED_EXTENSIONS = frozenset({".yml", ".yaml", ".toml", ".cfg", ".ini"})


def _is_blocked(rel_resolved: Path) -> str | None:
    """Return a human-readable reason if the path should not be edited, else None."""
    if rel_resolved.parts[0:1] and rel_resolved.parts[0] in _BLOCKED_TOP_DIRS:
        return f"top-level directory '{rel_resolved.parts[0]}' is blocked"
    if rel_resolved.name in _BLOCKED_FILES:
        return f"file '{rel_resolved.name}' is a control file"
    if rel_resolved.suffix in _BLOCKED_EXTENSIONS:
        return f"extension '{rel_resolved.suffix}' is blocked (config/CI files)"
    return None


def apply_edits(edits: list[dict[str, str]]) -> list[str]:
    applied: list[str] = []
    repo_root_resolved = REPO_ROOT.resolve()
    for edit in edits:
        rel = edit.get("file", "")
        old = edit.get("old", "")
        new = edit.get("new", "")
        if not (rel and old) or not isinstance(rel, str) or not isinstance(old, str) or not isinstance(new, str):
            continue
        fpath = (REPO_ROOT / rel).resolve()
        try:
            rel_resolved = fpath.relative_to(repo_root_resolved)
        except ValueError:
            log.warning("skip %s — path escapes repo root", rel)
            continue
        reason = _is_blocked(rel_resolved)
        if reason:
            log.warning("skip %s — %s", rel, reason)
            continue
        if not fpath.is_file():
            log.warning("skip %s — not a regular file", rel)
            continue
        content = fpath.read_text(errors="replace")
        if old not in content:
            log.warning("skip %s — old string not found", rel)
            continue
        if content.count(old) != 1:
            log.warning("skip %s — old string matches %d locations (must be unique)", rel, content.count(old))
            continue
        fpath.write_text(content.replace(old, new, 1))
        applied.append(rel)
        log.info("edit applied: %s", rel)
    return applied


def update_changelog(explanation: str, fixed_tests: list[str]) -> None:
    cl_path = REPO_ROOT / "docs" / "changelog.md"
    if not cl_path.exists():
        return
    content = cl_path.read_text()
    bullet = f"- Agency auto-fix: {explanation}"
    for t in fixed_tests[:5]:
        bullet += f"\n  - `{t}`"
    marker = "## [Unreleased]"
    if marker not in content:
        return
    # Find the Unreleased section boundary
    unreleased_start = content.index(marker)
    next_section = content.find("\n## ", unreleased_start + len(marker))
    unreleased_block = content[unreleased_start:next_section] if next_section != -1 else content[unreleased_start:]
    fixed_heading = "### Fixed"
    if fixed_heading in unreleased_block:
        # Append bullet to existing ### Fixed section
        insert_at = content.index(fixed_heading, unreleased_start) + len(fixed_heading)
        content = content[:insert_at] + f"\n{bullet}" + content[insert_at:]
    else:
        # Create new ### Fixed block after the marker
        content = content.replace(marker, f"{marker}\n\n{fixed_heading}\n{bullet}", 1)
    cl_path.write_text(content)


def main() -> int:
    if not NVIDIA_KEY and not ANTHROPIC_KEY:
        log.error("Neither NVIDIA_API_KEY nor ANTHROPIC_API_KEY is set.")
        return 2

    initial_output_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if initial_output_file and initial_output_file.exists():
        pytest_output = initial_output_file.read_text()
        has_failures = bool(extract_failing_tests(pytest_output))
        has_errors = bool(re.search(r"^(ERROR|FAILED)\s", pytest_output, re.MULTILINE))
        exit_code = 0 if not (has_failures or has_errors) else 1
    else:
        log.info("Running pytest baseline...")
        exit_code, pytest_output = run_pytest()

    if exit_code == 0:
        log.info("All tests already passing — nothing to fix.")
        return 0

    failing = extract_failing_tests(pytest_output)
    if not failing:
        log.error("Tests failed but no FAILED lines found — may be a collection error.")
        log.error(pytest_output[-2000:])
        return 1

    log.info("Failing tests (%d): %s", len(failing), ", ".join(failing[:5]))
    all_applied: list[str] = []

    for iteration in range(1, MAX_ITERATIONS + 1):
        log.info("=== Agency Fix Iteration %d/%d ===", iteration, MAX_ITERATIONS)
        messages = build_prompt(pytest_output, failing, iteration)
        log.info("Calling LLM...")
        response = call_llm(messages)

        if not response:
            log.warning("LLM returned empty response.")
            break

        parsed = parse_edits(response)
        if not isinstance(parsed, dict):
            log.warning("LLM response parsed to non-dict type %s; skipping.", type(parsed).__name__)
            break
        explanation = parsed.get("explanation", "")
        raw_edits = parsed.get("edits", [])
        # Normalise: a single dict response is wrapped into a list; anything
        # other than a list of dicts is discarded.
        if isinstance(raw_edits, dict):
            raw_edits = [raw_edits]
        edits = [e for e in raw_edits if isinstance(e, dict)] if isinstance(raw_edits, list) else []
        log.info("LLM explanation: %s", explanation)

        if not edits:
            log.warning("No edits suggested.")
            break

        applied = apply_edits(edits)
        all_applied.extend(applied)

        if not applied:
            log.warning("No edits could be applied.")
            break

        fixed_tests = list(failing)  # snapshot before re-run overwrites failing
        log.info("Re-running pytest...")
        exit_code, pytest_output = run_pytest()
        failing = extract_failing_tests(pytest_output)

        if exit_code == 0:
            log.info("All tests green after iteration %d.", iteration)
            update_changelog(explanation, fixed_tests)
            return 0

        log.warning("Still failing: %s", ", ".join(failing[:5]))

    log.error("Could not fix all tests after %d iterations.", MAX_ITERATIONS)
    return 1


if __name__ == "__main__":
    sys.exit(main())
