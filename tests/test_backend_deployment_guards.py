from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_backend_dockerfile_copies_schedules_package() -> None:
    dockerfile = (ROOT / "Dockerfile.backend").read_text()
    assert "COPY schedules/ schedules/" in dockerfile, (
        "Dockerfile.backend must copy the schedules package into the backend image; "
        "otherwise backend.server cannot import schedules_router on hosted deploys."
    )
