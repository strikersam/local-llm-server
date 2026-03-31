"""Dynamic model router package.

Public API::

    from router import get_router, RoutingDecision

    decision = get_router().route(
        requested_model="claude-opus-4-6",
        messages=messages,
        override_model=request.headers.get("x-model-override"),
    )
    model = decision.resolved_model
    meta  = decision.to_meta()   # include in Langfuse observation
"""

from router.model_router import RoutingDecision, ModelRouter, get_router, reset_router

__all__ = ["RoutingDecision", "ModelRouter", "get_router", "reset_router"]
