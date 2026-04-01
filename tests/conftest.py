from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    """Ensure repo root is importable when running `pytest` as a console script.

    On some Python builds, running `pytest` (vs `python -m pytest`) does not include the
    current working directory on `sys.path`, which breaks `import proxy` style imports.
    """

    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

