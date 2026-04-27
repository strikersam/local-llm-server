#!/usr/bin/env python3
"""Start ngrok tunnel for local-llm-server (non-interactive)."""

import sys
import time
import os

try:
    from pyngrok import ngrok
except ImportError:
    print("❌ pyngrok not installed. Install: pip install pyngrok")
    sys.exit(1)


def main():
    print("\n" + "="*60)
    print("🚀 Starting ngrok tunnel...")
    print("="*60 + "\n")

    # Set auth token if available
    auth_token = os.getenv("NGROK_AUTH_TOKEN", "").strip()
    if auth_token:
        ngrok.set_auth_token(auth_token)
        print(f"✓ Using auth token from NGROK_AUTH_TOKEN")

    try:
        # Start tunnel
        tunnel = ngrok.connect(8000, bind_tls=True)
        print(f"\n✅ Tunnel started!")
        print(f"\n🌐 Public URL: {tunnel}")
        print(f"\n📋 Test it:")
        print(f"   curl {tunnel}/health")
        print(f"\n🔐 Use with Claude Code:")
        print(f"   export ANTHROPIC_BASE_URL={tunnel}")
        print(f"   claude code")
        print(f"\n📊 Monitor: http://localhost:4040")
        print(f"\n✋ Tunnel is running... (Ctrl+C to stop)")

        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n👋 Stopping tunnel...")
            ngrok.kill()
            print("✓ Done")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Solution:")
        print("1. Install pyngrok: pip install pyngrok")
        print("2. Get auth token: https://dashboard.ngrok.com")
        print("3. Set it: export NGROK_AUTH_TOKEN=your_token")
        print("4. Run: python start_tunnel_simple.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
