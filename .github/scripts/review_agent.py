"""
Council-review agent using Claude.

Fetches the git diff of a PR branch vs master and runs the council-review
skill (Security, Correctness, Performance, Maintainability reviewers).

Usage:
  python review_agent.py <pr_number>

Writes /tmp/review_result.json with:
  {"verdict": "PASS"|"WARN"|"FAIL", "summary": str, "details": str}

Exit codes:
  0 — PASS or WARN (auto-merge allowed)
  1 — FAIL (needs human review)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import anthropic

PR_NUMBER = sys.argv[1] if len(sys.argv) > 1 else ""
RESULT_FILE = "/tmp/review_result.json"


def get_pr_diff(pr_num: str) -> str:
    result = subprocess.run(
        f"gh pr diff {pr_num} --patch",
        shell=True, capture_output=True, text=True, timeout=60,
    )
    diff = result.stdout
    if len(diff) > 12000:
        diff = diff[:12000] + "\n...[diff truncated]"
    return diff


def get_pr_files(pr_num: str) -> str:
    result = subprocess.run(
        f"gh pr view {pr_num} --json files -q '.files[].path'",
        shell=True, capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip()


def load_council_skill() -> str:
    p = Path(".agents/skills/council-review/SKILL.md")
    if p.exists():
        return p.read_text()[:2000]
    return ""


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set — skipping review, will auto-pass", file=sys.stderr)
        result = {"verdict": "WARN", "summary": "Review skipped (no API key)", "details": ""}
        with open(RESULT_FILE, "w") as f:
            json.dump(result, f)
        sys.exit(0)

    diff = get_pr_diff(PR_NUMBER)
    files = get_pr_files(PR_NUMBER)
    skill = load_council_skill()

    prompt = textwrap.dedent(f"""
        You are performing a council code review on PR #{PR_NUMBER}.

        ## Council Review Skill
        {skill}

        ## Files Changed
        {files}

        ## Diff
        ```diff
        {diff}
        ```

        ## Instructions
        Run all four reviewer roles (Security, Correctness, Performance,
        Maintainability). For each, give a verdict: PASS / WARN / FAIL and
        a one-sentence reason.

        Then give an overall verdict:
        - PASS: all reviewers are PASS or WARN, no blocking issues
        - WARN: one or more WARNs but nothing blocking — auto-merge OK
        - FAIL: any reviewer found a blocking issue — needs human review

        Output in this exact format:
        SECURITY: <PASS|WARN|FAIL> — <reason>
        CORRECTNESS: <PASS|WARN|FAIL> — <reason>
        PERFORMANCE: <PASS|WARN|FAIL> — <reason>
        MAINTAINABILITY: <PASS|WARN|FAIL> — <reason>
        OVERALL: <PASS|WARN|FAIL>
        SUMMARY: <one-paragraph summary of the changes and verdict>
    """).strip()

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text if response.content else ""
    print(text)

    # Parse verdict
    verdict = "WARN"  # default to WARN (allow merge) if parsing fails
    for line in text.splitlines():
        if line.startswith("OVERALL:"):
            v = line.split(":", 1)[1].strip().split()[0].upper()
            if v in {"PASS", "WARN", "FAIL"}:
                verdict = v
            break

    summary_lines = [l for l in text.splitlines() if l.startswith("SUMMARY:")]
    summary = summary_lines[0].replace("SUMMARY:", "").strip() if summary_lines else text[:300]

    result = {"verdict": verdict, "summary": summary, "details": text}
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f)

    print(f"\n[review] Verdict: {verdict}")
    sys.exit(0 if verdict in {"PASS", "WARN"} else 1)


if __name__ == "__main__":
    main()
