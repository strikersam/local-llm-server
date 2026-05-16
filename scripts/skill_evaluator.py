#!/usr/bin/env python3
"""
Skill Evaluator for local-llm-server

Evaluates skills in .claude/skills/ by running their test scripts (if available)
and collecting metadata such as last updated time and potential conflicts.

Inspired by the rigorous skill evaluation process described in:
https://x.com/mnilax/status/2051701429987897712?s=12
"""

from __future__ import annotations

import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import time
import tempfile
import shutil
from typing import Dict, List, Any, Optional

# Constants
SKILLS_DIR = Path(".claude/skills")
REPO_ROOT = Path(".")
GIT_DIR = REPO_ROOT / ".git"
TEST_SCRIPT_NAMES = ["test.sh", "test.py", "test"]
CONFLICT_RISKY_FILES = {
    "admin_auth.py",
    "key_store.py",
    "agent/tools.py",
    "proxy.py",
}
# Default timeout for test scripts (can be overridden by --timeout)
DEFAULT_TIMEOUT_SECONDS = 30
DAYS_FOR_STALE = 90


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
) -> tuple[int, str, str]:
    """Run a command and return (exit_code, stdout, stderr)."""
    if timeout is None:
        timeout = DEFAULT_TIMEOUT_SECONDS
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return -2, "", str(e)


def get_git_last_updated(skill_path: Path) -> Optional[datetime]:
    """Get the last commit date for a skill directory."""
    if not GIT_DIR.exists():
        return None
    exit_code, stdout, stderr = run_command(
        ["git", "log", "-1", "--format=%ct", "--", str(skill_path)]
    )
    if exit_code != 0 or not stdout.strip():
        return None
    try:
        timestamp = int(stdout.strip())
        return datetime.fromtimestamp(timestamp)
    except ValueError:
        return None


def has_test_script(skill_path: Path) -> Optional[Path]:
    """Check if skill has a test script."""
    for name in TEST_SCRIPT_NAMES:
        test_path = skill_path / name
        if test_path.is_file():
            return test_path
    return None


def run_skill_test(skill_path: Path) -> Dict[str, Any]:
    """Run the skill's test script and return results."""
    test_script = has_test_script(skill_path)
    if not test_script:
        return {
            "has_test": False,
            "passed": False,
            "error": "No test script found",
            "duration": 0.0,
        }

    # Make test script executable if it's a shell script
    if test_script.suffix == ".sh":
        os.chmod(test_script, 0o755)

    start_time = time.time()
    exit_code, stdout, stderr = run_command(
        [str(test_script)], cwd=skill_path
    )
    duration = time.time() - start_time

    passed = exit_code == 0
    return {
        "has_test": True,
        "passed": passed,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "duration": duration,
    }


def check_for_conflicts(skill_path: Path) -> List[str]:
    """Check if skill modifies risky files (by examining its content)."""
    conflicts = []
    # Look for files that might modify risky files
    for root, dirs, files in os.walk(skill_path):
        for file in files:
            file_path = Path(root) / file
            # Skip test scripts and documentation
            if file in TEST_SCRIPT_NAMES or file.endswith((".md", ".txt", ".json")):
                continue
            try:
                content = file_path.read_text(errors="ignore")
                for risky in CONFLICT_RISKY_FILES:
                    if risky in content:
                        conflicts.append(
                            f"{file_path.relative_to(skill_path)} references {risky}"
                        )
            except Exception:
                # Skip unreadable files
                pass
    return conflicts


def evaluate_skill(skill_name: str) -> Dict[str, Any]:
    """Evaluate a single skill."""
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.is_dir():
        return {"error": f"Skill directory not found: {skill_name}"}

    result = {
        "skill": skill_name,
        "path": str(skill_path),
        "evaluated_at": datetime.now().isoformat(),
    }

    # Check last updated
    last_updated = get_git_last_updated(skill_path)
    if last_updated:
        result["last_updated"] = last_updated.isoformat()
        days_old = (datetime.now() - last_updated).days
        result["days_old"] = days_old
        result["is_stale"] = days_old > DAYS_FOR_STALE
    else:
        result["last_updated"] = None
        result["days_old"] = None
        result["is_stale"] = None

    # Check for test script and run it
    test_result = run_skill_test(skill_path)
    result.update(test_result)

    # Check for potential conflicts
    conflicts = check_for_conflicts(skill_path)
    result["potential_conflicts"] = conflicts
    result["has_potential_conflicts"] = len(conflicts) > 0

    # Determine overall pass/fail based on available criteria
    passes = []
    fails = []

    if not test_result["has_test"]:
        fails.append("No test script available")
    elif not test_result["passed"]:
        fails.append("Test script failed")
    elif test_result["duration"] > DEFAULT_TIMEOUT_SECONDS:
        fails.append(f"Test script too slow (> {DEFAULT_TIMEOUT_SECONDS}s)")
    else:
        passes.append("Test script passed")

    if result.get("is_stale"):
        fails.append(f"Skill not updated in {result['days_old']} days (> {DAYS_FOR_STALE})")
    else:
        passes.append("Skill is recently updated")

    if result.get("has_potential_conflicts"):
        fails.append("Potential conflicts with risky files detected")
    else:
        passes.append("No obvious conflicts with risky files")

    result["passes"] = passes
    result["fails"] = fails
    result["passed_overall"] = len(fails) == 0

    return result


def main() -> None:
    """Main entry point."""
    global DEFAULT_TIMEOUT_SECONDS
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate skills in .claude/skills/"
    )
    parser.add_argument(
        "skill",
        nargs="?",
        help="Specific skill to evaluate (if omitted, evaluate all skills)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout for test scripts in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    args = parser.parse_args()

    # Update the global timeout
    DEFAULT_TIMEOUT_SECONDS = args.timeout

    if not SKILLS_DIR.is_dir():
        print(f"Error: Skills directory not found: {SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)

    skills_to_evaluate = []
    if args.skill:
        skill_path = SKILLS_DIR / args.skill
        if not skill_path.is_dir():
            print(f"Error: Skill not found: {args.skill}", file=sys.stderr)
            sys.exit(1)
        skills_to_evaluate = [args.skill]
    else:
        skills_to_evaluate = [
            d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    results = []
    for skill in sorted(skills_to_evaluate):
        print(f"Evaluating skill: {skill}", file=sys.stderr)
        result = evaluate_skill(skill)
        results.append(result)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        # Text format
        for result in results:
            print(f"\n{'='*60}")
            print(f"Skill: {result['skill']}")
            print(f"{'='*60}")
            if "error" in result:
                print(f"ERROR: {result['error']}")
                continue

            print(f"Path: {result['path']}")
            if result.get("last_updated"):
                print(
                    f"Last updated: {result['last_updated']} ({result['days_old']} days ago)"
                )
            else:
                print("Last updated: Unknown (git not available or no commits)")

            print(f"Has test: {result.get('has_test', False)}")
            if result.get("has_test"):
                print(f"Test passed: {result.get('passed', False)}")
                print(f"Test duration: {result.get('duration', 0):.2f}s")
                if not result.get("passed"):
                    print(f"Test stdout: {result.get('stdout', '')[:200]}")
                    print(f"Test stderr: {result.get('stderr', '')[:200]}")

            print(f"Potential conflicts: {result.get('has_potential_conflicts', False)}")
            if result.get("potential_conflicts"):
                for conflict in result["potential_conflicts"][:5]:
                    print(f"  - {conflict}")

            print(f"Passes: {len(result.get('passes', []))}")
            for p in result.get("passes", []):
                print(f"  ✓ {p}")
            print(f"Fails: {len(result.get('fails', []))}")
            for f in result.get("fails", []):
                print(f"  ✗ {f}")

            print(f"Overall: {'PASS' if result.get('passed_overall') else 'FAIL'}")


if __name__ == "__main__":
    main()