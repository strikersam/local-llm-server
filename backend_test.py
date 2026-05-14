#!/usr/bin/env python3
"""
Backend API Testing for LLM Wiki Dashboard
This script runs the actual test suite via pytest to ensure consistency with CI.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Run pytest on the tests directory
    result = subprocess.run([sys.executable, "-m", "pytest"], cwd=Path(__file__).parent)
    sys.exit(result.returncode)
