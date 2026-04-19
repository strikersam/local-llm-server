"""agents/__init__.py — CRISPY multi-agent coding system."""
from agents.profiles import (
    AgentProfile,
    load_all_profiles,
    make_architect_profile,
    make_coder_profile,
    make_reviewer_profile,
    make_scout_profile,
    make_verifier_profile,
)
from agents.swarm import AgentSwarm, PHASE_ROLE

__all__ = [
    "AgentProfile",
    "AgentSwarm",
    "PHASE_ROLE",
    "load_all_profiles",
    "make_architect_profile",
    "make_coder_profile",
    "make_reviewer_profile",
    "make_scout_profile",
    "make_verifier_profile",
]
