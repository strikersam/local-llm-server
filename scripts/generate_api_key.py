#!/usr/bin/env python3
"""Create a new API key for a user (email + department / seat) and append to KEYS_FILE.

Usage:
    python scripts/generate_api_key.py --email user@example.com --department engineering
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running from repo root: python scripts/generate_api_key.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from key_store import KeyStore, issue_new_api_key


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Bearer API key bound to an email and department (seat). "
        "The plaintext key is printed once; store it securely.",
    )
    parser.add_argument("--email", required=True, help="User email (shown in Langfuse as user_id)")
    parser.add_argument(
        "--department",
        required=True,
        help="Seat / department label (stored in metadata and key file)",
    )
    parser.add_argument(
        "--keys-file",
        default=os.environ.get("KEYS_FILE", "keys.json"),
        help="Path to the key database JSON (default: KEYS_FILE env or keys.json)",
    )
    args = parser.parse_args()

    path = Path(args.keys_file)
    if not str(path).strip():
        print("KEYS_FILE / --keys-file must be set", file=sys.stderr)
        return 1

    ks = KeyStore(path)
    plain, rec = issue_new_api_key(ks, args.email.strip(), args.department.strip())

    print("Key created. Distribute this secret once (it cannot be shown again):")
    print(plain)
    print()
    print(f"key_id:      {rec.key_id}")
    print(f"email:       {rec.email}")
    print(f"department:  {rec.department}")
    print(f"stored in:   {path.resolve()}")
    print()
    print("If the proxy is already running, the next request reloads keys.json automatically (mtime).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
