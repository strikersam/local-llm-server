#!/usr/bin/env python3
"""
Start an ngrok tunnel for local-llm-server with public access.
Requires pyngrok to be installed: pip install pyngrok
"""

import sys
import time
import subprocess
from pathlib import Path

try:
    from pyngrok import ngrok
except ImportError:
    print("❌ pyngrok not installed")
    print("\nInstall with:")
    print("  .venv/bin/pip install pyngrok")
    sys.exit(1)


def check_services():
    """Check if local services are running."""
    import httpx

    try:
        # Check proxy
        response = httpx.get("http://localhost:8000/health", timeout=2)
        proxy_ok = response.status_code == 200
    except:
        proxy_ok = False

    try:
        # Check Ollama
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        ollama_ok = response.status_code == 200
    except:
        ollama_ok = False

    return proxy_ok, ollama_ok


def main():
    print("\n" + "="*60)
    print("🚀 Local LLM Server - Ngrok Tunnel")
    print("="*60 + "\n")

    # Check services
    print("✅ Checking local services...")
    proxy_ok, ollama_ok = check_services()

    if not proxy_ok:
        print("   ❌ Proxy not running on localhost:8000")
        print("   Start it: .venv/bin/python -m uvicorn proxy:app --port 8000")
        sys.exit(1)

    if not ollama_ok:
        print("   ❌ Ollama not running on localhost:11434")
        print("   Start it: ollama serve")
        sys.exit(1)

    print("   ✓ Proxy: http://localhost:8000")
    print("   ✓ Ollama: http://localhost:11434")

    # Get ngrok auth token if needed
    print("\nDo you have an ngrok auth token?")
    print("Get one from: https://dashboard.ngrok.com/auth/your-authtoken")
    token = input("Enter your ngrok auth token (or press Enter to skip): ").strip()

    if token:
        ngrok.set_auth_token(token)
        print("✓ Auth token set")
    else:
        print("⚠️  Without auth token, tunnel URL will change on each run")

    # Set up tunnel
    print("\n📡 Starting ngrok tunnel...")
    print("   Forwarding: http://localhost:8000 → Public HTTPS URL")

    try:
        # Connect to ngrok
        public_url = ngrok.connect(8000)

        print(f"\n✅ Tunnel is live!")
        print(f"\n🌐 Public URL: {public_url}")
        print(f"\n📋 Test it:")
        print(f"   curl {public_url}/health")
        print(f"\n🔐 Use it with:")
        print(f"   ANTHROPIC_BASE_URL={public_url} claude code")
        print(f"\n📊 Monitor tunnel: http://localhost:4040")
        print(f"\n✋ Press Ctrl+C to stop tunnel")
        print()

        # Keep tunnel alive
        ngrok_process = ngrok.get_ngrok_process()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n👋 Stopping tunnel...")
            ngrok.kill()
            print("✓ Tunnel closed")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check ngrok dashboard: https://dashboard.ngrok.com/")
        print("2. Verify ngrok auth token is set")
        print("3. Check your local services are running")
        sys.exit(1)


if __name__ == "__main__":
    main()
