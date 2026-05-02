#!/usr/bin/env python3
"""
Simple task runner for local-llm-server.
Submit a task description and get results back.
"""

import json
import sys
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEYS", "test-key-9Ob7nJSX4vxkr4AbYlXNB0Z-FVO6MitnOZGLZwRhGps").split(",")[0].strip()
BASE_URL = f"http://{os.getenv('PROXY_HOST', '127.0.0.1')}:{os.getenv('PROXY_PORT', '8000')}"
WORKSPACE = os.getenv("AGENT_WORKSPACE_ROOT", str(Path.cwd()))

def submit_task(description: str, task_type: str = "planner"):
    """Submit a task to the agent planner."""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "task": description,
        "workspace": WORKSPACE,
        "task_type": task_type,
    }

    print(f"📋 Submitting task...")
    print(f"   Description: {description}")
    print(f"   Workspace: {WORKSPACE}")
    print(f"   Model: gemma4:latest")
    print()

    try:
        # Try the streaming endpoint first
        with httpx.stream(
            "POST",
            f"{BASE_URL}/agent/plan",
            json=payload,
            headers=headers,
            timeout=300.0
        ) as response:
            if response.status_code == 404:
                print("⚠️  Agent endpoint not available. Trying alternative...")
                response.raise_for_status()

            print("🤔 Agent Planning:\n")
            for line in response.iter_text():
                if line:
                    print(line, end="", flush=True)
            print("\n")

    except httpx.HTTPError as e:
        if "404" in str(e):
            print("⚠️  Could not reach agent endpoint. Trying task endpoint...")
            submit_simple_task(description, headers)
        else:
            print(f"❌ Error: {e}")
            sys.exit(1)

def submit_simple_task(description: str, headers: dict):
    """Submit a simple task via the tasks API."""

    payload = {
        "description": description,
        "workspace": WORKSPACE,
    }

    with httpx.Client() as client:
        try:
            response = client.post(
                f"{BASE_URL}/api/tasks/create",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            print("✅ Task submitted!")
            print(json.dumps(result, indent=2))

            if "id" in result:
                print(f"\n📌 Task ID: {result['id']}")
                print("   Check status with: curl -H 'Authorization: Bearer ...' http://localhost:8000/api/tasks/{task_id}")

        except httpx.HTTPError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

def check_health():
    """Check if the proxy is running."""
    try:
        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                health = response.json()
                print("✅ Proxy is healthy")
                print(f"   Models: {', '.join(health.get('models', []))}")
                return True
    except Exception as e:
        print(f"❌ Proxy not responding: {e}")
        return False

if __name__ == "__main__":
    if not check_health():
        print("\n💡 Start the proxy with: .venv/bin/python -m uvicorn proxy:app --port 8000")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python task_runner.py 'Your task description'")
        print("\nExamples:")
        print("  python task_runner.py 'List all Python files'")
        print("  python task_runner.py 'Read and summarize proxy.py'")
        print("  python task_runner.py 'Find all TODO comments'")
        sys.exit(1)

    task_description = " ".join(sys.argv[1:])
    submit_task(task_description)
