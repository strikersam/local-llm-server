"""
Council-review agent using NVIDIA NIM or Moonshot.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from openai import OpenAI, RateLimitError

PR_NUMBER = sys.argv[1] if len(sys.argv) > 1 else ""
RESULT_FILE = "/tmp/review_result.json"

CANDIDATE_MODELS = [
    ("nvidia/nemotron-3-super-120b-a12b", "https://integrate.api.nvidia.com/v1", os.environ.get("NVIDIA_API_KEY")),
    ("kimi-k2.6", "https://api.moonshot.cn/v1", os.environ.get("MOONSHOT_API_KEY")),
]

def main():
    """
    Run a PR review using available candidate LLM backends and write the verdict to RESULT_FILE.
    
    Fetches the PR diff for PR_NUMBER and prompts the models to review security and correctness using the expected `OVERALL: PASS|FAIL` format. Queries configured candidate models until one returns a response, writes JSON to RESULT_FILE containing `{"verdict": <"PASS"|"FAIL">, "summary": <first 200 chars of response>}`, and exits with status 0 when the verdict is PASS or 1 otherwise. If no model produces a response, exits with status 1.
    """
    diff = subprocess.check_output(["gh", "pr", "diff", PR_NUMBER, "--patch"], text=True)[:10000]
    prompt = f"Review PR #{PR_NUMBER}:\n\n{diff}\n\nRoles: Security, Correctness. Give overall PASS/FAIL. Format: OVERALL: PASS|FAIL"

    text = ""
    for model, base_url, api_key in CANDIDATE_MODELS:
        if not api_key:
            continue

        client = OpenAI(base_url=base_url, api_key=api_key)
        retries = 0
        while retries < 3:
            try:
                res = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
                text = res.choices[0].message.content
                break
            except RateLimitError:
                time.sleep(5 * (2 ** retries))
                retries += 1
                continue
            except Exception as e:
                print(f"Error with model {model}: {e}", file=sys.stderr)
                break

        if text:
            break

    if not text:
        print("All models failed or no API keys available.", file=sys.stderr)
        sys.exit(1)


    verdict = "PASS" if "OVERALL: PASS" in text.upper() else "FAIL"
    with open(RESULT_FILE, "w") as f:
        json.dump({"verdict": verdict, "summary": text[:200]}, f)

    sys.exit(0 if verdict == "PASS" else 1)

if __name__ == "__main__":
    main()
