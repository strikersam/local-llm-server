# Backward-compatibility shim — import from agent package instead.
from agent.tools import WorkspaceTools  # noqa: F401

__all__ = ["WorkspaceTools"]
