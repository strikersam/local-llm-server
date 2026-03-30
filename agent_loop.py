# Backward-compatibility shim — import from agent package instead.
# This file will be removed in a future version.
from agent.loop import AgentRunner  # noqa: F401

__all__ = ["AgentRunner"]
