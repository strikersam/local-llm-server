# Backward-compatibility shim — import from agent package instead.
from agent.state import AgentSessionStore  # noqa: F401

__all__ = ["AgentSessionStore"]
