#!/usr/bin/env python3
"""
Real-time proxy log viewer - shows all requests hitting DeepSeek 32B
Reads from proxy.log and displays activity with highlighting
"""

import os
import sys
import time
from pathlib import Path

LOG_FILE = Path("./logs/proxy.log")
DEEPSEEK_KEYWORDS = ["deepseek", "r1:32b", "/v1/chat/completions", "/v1/messages"]

def watch_log():
    """Watch and display proxy logs in real-time"""

    if not LOG_FILE.exists():
        print(f"❌ Log file not found: {LOG_FILE}")
        print(f"   Make sure proxy is running with logging enabled")
        sys.exit(1)

    print("\n" + "=" * 100)
    print("🔍 Proxy Real-Time Log Viewer")
    print("=" * 100)
    print(f"📍 Watching: {LOG_FILE.absolute()}\n")
    print("🎯 Filter: DeepSeek 32B requests\n")

    # Start from end of file
    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        f.seek(0, 2)  # Go to end
        line_count = 0
        last_size = f.tell()

    print("⏳ Monitoring for activity... (Ctrl+C to stop)\n")
    print("-" * 100)

    request_count = 0

    while True:
        try:
            time.sleep(0.1)  # Check frequently

            # Check if file grew
            current_size = os.path.getsize(LOG_FILE)

            if current_size > last_size:
                with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_size)
                    new_lines = f.readlines()
                    last_size = current_size

                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue

                        # Check if this is a request line with DeepSeek
                        if any(kw in line.lower() for kw in DEEPSEEK_KEYWORDS):
                            request_count += 1
                            print(f"\n{'🔥' * 45}")
                            print(f"Request #{request_count}")
                            print(f"{'🔥' * 45}")
                            print(f"  {line}")
                            print()
                        # Also show error or completion lines
                        elif "error" in line.lower() or "complete" in line.lower():
                            if any(kw in line.lower() for kw in ["deepseek", "r1"]):
                                print(f"  ✓ {line}")
                                print()

        except KeyboardInterrupt:
            print(f"\n\n{'=' * 100}")
            print(f"✋ Monitor stopped")
            print(f"Total DeepSeek requests logged: {request_count}")
            print(f"{'=' * 100}\n")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️  Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    watch_log()
