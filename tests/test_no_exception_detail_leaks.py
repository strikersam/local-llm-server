"""tests/test_no_exception_detail_leaks.py — Guard against str(exc)/str(e) leaking

into HTTPException `detail=` responses. Regression test for the security fix
that replaced 31 such sites across backend/server.py, backend/v4_api.py,
proxy.py, runtimes/api.py, backend/admin_update_task_router.py, tasks/api.py,
webui/router.py, workflow/api.py, and agents/agile_api.py — a raw
`detail=str(exc))` in an HTTPException response leaks internal exception
text (stack-trace-adjacent detail, internal identifiers, file paths) to the
client.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_GUARDED_FILES = [
    "backend/server.py",
    "backend/v4_api.py",
    "proxy.py",
    "runtimes/api.py",
    "backend/admin_update_task_router.py",
    "tasks/api.py",
    "webui/router.py",
    "workflow/api.py",
    "agents/agile_api.py",
    "agent/coordinate.py",
]

# Matches `detail=str(exc))` or `detail=str(e))` — the leaking pattern.
_LEAK_PATTERN = re.compile(r"detail\s*=\s*str\(\s*(?:exc|e)\s*\)\s*\)")


@pytest.mark.parametrize("relpath", _GUARDED_FILES)
def test_no_raw_exception_detail_in_http_response(relpath: str) -> None:
    text = (ROOT / relpath).read_text()
    matches = _LEAK_PATTERN.findall(text)
    assert not matches, (
        f"{relpath} leaks raw exception text via HTTPException(detail=str(exc)): "
        f"{len(matches)} occurrence(s). Use a generic message and log the real "
        f"exception server-side instead."
    )
