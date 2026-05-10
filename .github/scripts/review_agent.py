"""
Council-review agent using NVIDIA NIM.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from openai import OpenAI

PR_NUMBER = sys.argv[1] if len(sys.argv) > 1 else ""
RESULT_FILE = "/tmp/review_result.json"

def main():
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=os.environ["NVIDIA_API_KEY"])
    diff = subprocess.check_output(["gh", "pr", "diff", PR_NUMBER, "--patch"], text=True)[:10000]
    prompt = f"Review PR #{PR_NUMBER}:\n\n{diff}\n\nRoles: Security, Correctness. Give overall PASS/FAIL. Format: OVERALL: PASS|FAIL"
    res = client.chat.completions.create(model="nvidia/nemotron-3-super-120b-a12b", messages=[{"role": "user", "content": prompt}])
    text = res.choices[0].message.content
    verdict = "PASS" if "OVERALL: PASS" in text.upper() else "FAIL"
    with open(RESULT_FILE, "w") as f: json.dump({"verdict": verdict, "summary": text[:200]}, f)
    sys.exit(0 if verdict == "PASS" else 1)

if __name__ == "__main__": main()
