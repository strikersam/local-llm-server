"""tests/test_artifact_store.py — Unit tests for workflow/artifact_store.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from workflow.artifact_store import ArtifactStore


@pytest.fixture()
def store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore(
        artifacts_root=tmp_path / "artifacts",
        db_path=tmp_path / "workflow.db",
    )


class TestArtifactStorePersist:
    def test_persist_creates_file_on_disk(self, store: ArtifactStore, tmp_path: Path):
        art = store.persist(
            run_id="wf_test01",
            phase="context",
            name="context.md",
            content="# Context\n\nSome context here.",
        )
        assert Path(art.path).exists()
        assert Path(art.path).read_text(encoding="utf-8") == "# Context\n\nSome context here."

    def test_persist_returns_artifact_with_metadata(self, store: ArtifactStore, tmp_path: Path):
        art = store.persist(
            run_id="wf_test01",
            phase="plan",
            name="plan.md",
            content="## Plan\n\n## Slice 1: Add tests",
        )
        assert art.artifact_id.startswith("art_")
        assert art.run_id == "wf_test01"
        assert art.phase == "plan"
        assert art.name == "plan.md"
        assert art.size_bytes > 0
        assert len(art.content_hash) == 64  # SHA-256 hex

    def test_persist_is_idempotent(self, store: ArtifactStore, tmp_path: Path):
        """Writing the same (run_id, name) twice should update, not duplicate."""
        art1 = store.persist(
            run_id="wf_test02",
            phase="context",
            name="context.md",
            content="# v1",
        )
        art2 = store.persist(
            run_id="wf_test02",
            phase="context",
            name="context.md",
            content="# v2 updated",
        )
        assert art1.artifact_id == art2.artifact_id  # same row updated
        assert art2.size_bytes > art1.size_bytes
        listed = store.list_for_run("wf_test02")
        assert len(listed) == 1  # no duplicate

    def test_persist_different_runs_isolated(self, store: ArtifactStore, tmp_path: Path):
        store.persist(run_id="wf_A", phase="context", name="context.md", content="A")
        store.persist(run_id="wf_B", phase="context", name="context.md", content="B")
        a_arts = store.list_for_run("wf_A")
        b_arts = store.list_for_run("wf_B")
        assert len(a_arts) == 1
        assert len(b_arts) == 1
        assert a_arts[0].artifact_id != b_arts[0].artifact_id


class TestArtifactStoreRetrieval:
    def test_get_content_by_id(self, store: ArtifactStore, tmp_path: Path):
        art = store.persist(
            run_id="wf_r01", phase="research", name="research.md", content="## Research"
        )
        content = store.get_content(art.artifact_id)
        assert content == "## Research"

    def test_get_content_missing_id_returns_none(self, store: ArtifactStore, tmp_path: Path):
        assert store.get_content("art_nonexistent") is None

    def test_get_by_name(self, store: ArtifactStore, tmp_path: Path):
        store.persist(run_id="wf_r02", phase="plan", name="plan.md", content="# Plan")
        art = store.get_by_name("wf_r02", "plan.md")
        assert art is not None
        assert art.name == "plan.md"

    def test_get_by_name_wrong_run_returns_none(self, store: ArtifactStore, tmp_path: Path):
        store.persist(run_id="wf_r03", phase="plan", name="plan.md", content="# Plan")
        assert store.get_by_name("wf_OTHER", "plan.md") is None

    def test_content_by_name_convenience(self, store: ArtifactStore, tmp_path: Path):
        store.persist(run_id="wf_r04", phase="plan", name="plan.md", content="## Plan content")
        content = store.content_by_name("wf_r04", "plan.md")
        assert content == "## Plan content"

    def test_content_by_name_missing_returns_none(self, store: ArtifactStore, tmp_path: Path):
        assert store.content_by_name("wf_r04", "missing.md") is None


class TestArtifactStoreListing:
    def test_list_for_run_ordered_by_creation(self, store: ArtifactStore, tmp_path: Path):
        run_id = "wf_list01"
        for name in ["context.md", "research.md", "plan.md"]:
            store.persist(run_id=run_id, phase="test", name=name, content=f"# {name}")
        listed = store.list_for_run(run_id)
        assert len(listed) == 3
        assert [a.name for a in listed] == ["context.md", "research.md", "plan.md"]

    def test_list_empty_for_unknown_run(self, store: ArtifactStore, tmp_path: Path):
        assert store.list_for_run("wf_unknown") == []

    def test_as_index_returns_metadata_only(self, store: ArtifactStore, tmp_path: Path):
        run_id = "wf_idx01"
        store.persist(run_id=run_id, phase="context", name="context.md", content="# ctx")
        index = store.as_index(run_id)
        assert len(index) == 1
        item = index[0]
        assert "artifact_id" in item
        assert "size_bytes" in item
        assert "content" not in item  # index has no content


class TestArtifactStoreDeletion:
    def test_delete_run_artifacts(self, store: ArtifactStore, tmp_path: Path):
        run_id = "wf_del01"
        art = store.persist(run_id=run_id, phase="context", name="context.md", content="# ctx")
        art_path = Path(art.path)
        assert art_path.exists()
        deleted = store.delete_run_artifacts(run_id)
        assert deleted == 1
        assert not art_path.exists()
        assert store.list_for_run(run_id) == []

    def test_delete_non_existent_run_returns_zero(self, store: ArtifactStore, tmp_path: Path):
        assert store.delete_run_artifacts("wf_no_such") == 0


class TestArtifactStoreJSONArtifact:
    def test_persist_and_retrieve_json_artifact(self, store: ArtifactStore, tmp_path: Path):
        """Verify artifacts that are stored as JSON (e.g., CheckRun results)."""
        data = {"check_id": "chk_001", "passed": True, "exit_code": 0}
        store.persist(
            run_id="wf_json01",
            phase="verify",
            name="verify-slice-01.json",
            content=json.dumps(data, indent=2),
        )
        raw = store.content_by_name("wf_json01", "verify-slice-01.json")
        assert raw is not None
        parsed = json.loads(raw)
        assert parsed["passed"] is True
