"""features — Feature maturity/support matrix.

Import the registry and enforcement helpers from features.matrix.
"""

from features.matrix import (
    FeatureEntry,
    FeatureMaturity,
    FeatureMatrix,
    FeatureUnavailableError,
    get_matrix,
    require_feature,
)

__all__ = [
    "FeatureEntry",
    "FeatureMaturity",
    "FeatureMatrix",
    "FeatureUnavailableError",
    "get_matrix",
    "require_feature",
]
