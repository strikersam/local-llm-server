# Backward-compatibility shim — import from agent package instead.
from agent.prompts import (  # noqa: F401
    build_execution_prompt,
    build_planning_prompt,
    build_tool_prompt,
    build_verification_prompt,
)

__all__ = [
    "build_execution_prompt", "build_planning_prompt",
    "build_tool_prompt", "build_verification_prompt",
]
