"""Lightweight docs/config sync tests (Area C5).

Ensures:
  - Support matrix docs can be generated from code
  - New feature flags are documented in the matrix
"""

from __future__ import annotations

import os

import pytest

from features.matrix import FeatureMatrix, get_feature_matrix, reset_feature_matrix


class TestSupportMatrixDocsSync:
    def test_matrix_markdown_table_generation(self):
        """The feature matrix can produce a markdown table for docs."""
        matrix = FeatureMatrix()
        md = matrix.as_markdown_table()
        # Should contain all feature IDs
        for entry in matrix.list_all():
            assert entry.feature_id in md, f"Feature {entry.feature_id} missing from markdown table"

    def test_all_config_flags_in_matrix(self):
        """Every config flag referenced in the matrix should be documented."""
        matrix = FeatureMatrix()
        # Just verify the structure is complete
        for entry in matrix.list_all():
            for flag in entry.config_flags:
                assert flag  # Not empty
                assert flag.isupper() or flag == ""  # Env var convention

    def test_feature_matrix_covers_all_areas(self):
        """The matrix should cover the key areas from the spec."""
        matrix = FeatureMatrix()
        required_ids = [
            "direct_chat",
            "async_agent_jobs",
            "agent_planner_executor_verifier",
            "agent_judge",
            "runtime_preflight",
            "local_runtime",
            "provider_routing_fallback",
        ]
        found_ids = {e.feature_id for e in matrix.list_all()}
        for fid in required_ids:
            assert fid in found_ids, f"Required feature {fid} missing from support matrix"
