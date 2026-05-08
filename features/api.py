"""features/api.py — Admin API for the feature support matrix.

Exposes:
  GET  /admin/features           — list full support matrix
  GET  /admin/features/{id}      — get single feature entry
  POST /admin/features/check     — check if a feature is available
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from features.matrix import FeatureMaturity, FeatureUnavailableError, get_feature_matrix

log = logging.getLogger("qwen-proxy")

features_router = APIRouter(prefix="/admin/features", tags=["features"])


@features_router.get("")
async def list_features() -> dict[str, Any]:
    """Return the full support matrix with summary."""
    matrix = get_feature_matrix()
    return matrix.as_dict()


@features_router.get("/{feature_id}")
async def get_feature(feature_id: str) -> dict[str, Any]:
    """Return a single feature entry."""
    matrix = get_feature_matrix()
    entry = matrix.get(feature_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found in support matrix.")
    result = entry.as_dict()
    warning = matrix.maturity_warning(feature_id)
    if warning:
        result["warning"] = warning
    return result


@features_router.post("/check")
async def check_feature(body: dict[str, str]) -> dict[str, Any]:
    """Check if a feature is available and return its status + any warnings."""
    feature_id = body.get("feature_id", "")
    matrix = get_feature_matrix()
    try:
        entry = matrix.check_available(feature_id)
        result = entry.as_dict()
        warning = matrix.maturity_warning(feature_id)
        if warning:
            result["warning"] = warning
        result["available"] = True
        return result
    except FeatureUnavailableError as exc:
        return exc.as_dict() | {"available": False}
