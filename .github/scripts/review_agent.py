"""
Council-review agent using NVIDIA NIM.

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

from openai import APIError, OpenAI

PR_NUMBER = sys.argv[1] if len(sys.argv) > 1 else ""
RESULT_FILE = "/tmp/review_result.json"  # nosec: B108 - Predictable temp file path used for backward compatibility


def get_pr_diff(pr_num: str) -> str:
    try:
        result = subprocess.run(
            ["gh", "pr", "diff", pr_num, "--patch"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return f"[diff unavailable: gh exited {result.returncode}: {result.stderr.strip()[:200]}]"
        diff = result.stdout
    except subprocess.TimeoutExpired:
        return "[diff unavailable: gh timed out]"
    if len(diff) > 12000:
        diff = diff[:12000] + "\n...[diff truncated]"
    return diff


def get_pr_files(pr_num: str) -> str:
    try:
        result = subprocess.run(
            ["gh", "pr", "view", pr_num, "--json", "files", "-q", ".files[].path"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return f"[files unavailable: gh exited {result.returncode}: {result.stderr.strip()[:200]}]"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[files unavailable: gh timed out]"


def load_council_skill() -> str:
    p = Path(".agents/skills/council-review/SKILL.md")
    if p.exists():
        return p.read_text()[:2000]
    return ""


def main() -> None:
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        print("ERROR: NVIDIA_API_KEY not set — review failed", file=sys.stderr)
        result = {"verdict": "FAIL", "summary": "Review failed (no API key)", "details": ""}
        with open(RESULT_FILE, "w") as f:
            json.dump(result, f)
        sys.exit(1)

    diff = get_pr_diff(PR_NUMBER)
    files = get_pr_files(PR_NUMBER)

    # Fail closed: if we couldn't fetch the diff we cannot do a real review.
    if diff.startswith("[diff unavailable"):
        print(f"ERROR: {diff}", file=sys.stderr)
        result = {"verdict": "FAIL", "summary": f"Review failed: {diff}", "details": ""}
        with open(RESULT_FILE, "w") as f:
            json.dump(result, f)
        sys.exit(1)

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

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3-coder-480b-a35b-instruct",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
    except APIError as exc:
        print(f"ERROR: API call failed: {exc}", file=sys.stderr)
        result = {"verdict": "FAIL", "summary": f"Review failed: {exc}", "details": ""}
        with open(RESULT_FILE, "w") as f:
            json.dump(result, f)
        sys.exit(1)
    print(text)

    # Parse verdict — fail closed if output is unparseable
    verdict = "FAIL"
    parsed_successfully = False
    for line in text.splitlines():
        if line.startswith("OVERALL:"):
            v = line.split(":", 1)[1].strip().split()[0].upper()
            if v in {"PASS", "WARN", "FAIL"}:
                verdict = v
                parsed_successfully = True
            break

    summary_lines = [l for l in text.splitlines() if l.startswith("SUMMARY:")]
    summary = summary_lines[0].replace("SUMMARY:", "").strip() if summary_lines else text[:300]

    result = {
        "verdict": verdict,
        "summary": summary,
        "details": text,
        "parsed_successfully": parsed_successfully,
    }
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f)

    print(f"\n[review] Verdict: {verdict} (parsed={parsed_successfully})")
    sys.exit(0 if verdict in {"PASS", "WARN"} else 1)


if __name__ == "__main__":
    main()
