#!/usr/bin/env python3
"""Backward-compatibility shim — use scripts/generate_api_key.py instead.

This file is kept so existing documentation links and muscle-memory work.
It delegates immediately to the canonical script.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.generate_api_key import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
