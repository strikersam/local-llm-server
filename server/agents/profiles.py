from typing import Dict, List, Optional

class AgentRole(Enum):
    ARCHITECT = "architect"
    SCOUT = "scout"
    CODER = "coder"
    REVIEWER = "reviewer"
    VERIFIER = "verifier"

class AgentProfile:
    def __init__(self, role: AgentRole, permissions: Dict[str, bool]):
        self.role = role
        self.permissions = permissions

DEFAULT_PERMISSIONS = {
    "read_files": True,
    "write_files": False,
    "execute_commands": False,
    "access_network": False
}

AGENT_PROFILES = {
    AgentRole.ARCHITECT: AgentProfile(
        role=AgentRole.ARCHITECT,
        permissions={
            "read_files": True,
            "write_files": False,
            "execute_commands": False,
            "access_network": True  # For research purposes
        }
    ),
    AgentRole.SCOUT: AgentProfile(
        role=AgentRole.SCOUT,
        permissions={
            "read_files": True,
            "write_files": False,
            "execute_commands": False,
            "access_network": True
        }
    ),
    AgentRole.CODER: AgentProfile(
        role=AgentRole.CODER,
        permissions={
            "read_files": True,
            "write_files": True,
            "execute_commands": True,  # For testing purposes
            "access_network": False
        }
    ),
    AgentRole.REVIEWER: AgentProfile(
        role=AgentRole.REVIEWER,
        permissions={
            "read_files": True,
            "write_files": False,
            "execute_commands": False,
            "access_network": False
        }
    ),
    AgentRole.VERIFIER: AgentProfile(
        role=AgentRole.VERIFIER,
        permissions={
            "read_files": True,
            "write_files": False,
            "execute_commands": True,  # For running verification commands
            "access_network": False
        }
    )
}