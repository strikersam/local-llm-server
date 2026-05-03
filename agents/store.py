"""agents/store.py — Persistent store for user-defined agent configurations.

Stores custom agent profiles that users create through the UI.  These are
distinct from the built-in CRISPY agent roles (scout/architect/coder/etc.)
which are defined in agents/profiles.py.

Backend: MongoDB with in-memory fallback (matches tasks/store.py pattern).
Owner isolation: each agent belongs to a user; admins see all agents.
"""

from __future__ import annotations

import secrets
import time
from typing import Any

from pydantic import BaseModel, Field


# ── Data model ────────────────────────────────────────────────────────────────

class AgentDefinition(BaseModel):
    """A user-defined agent configuration stored in the database."""

    agent_id:     str = Field(default_factory=lambda: f"agent_{secrets.token_hex(8)}")
    owner_id:     str                                   # user email or internal ID
    name:         str
    role:         str = ""
    description:  str = ""
    model:        str = "qwen3-coder:30b"
    system_prompt: str = ""
    preferred_runtime: str | None = None
    runtime_id:   str | None = None                    # preferred runtime (e.g. "hermes")
    fallback_runtimes: list[str] = Field(default_factory=list)
    task_specializations: list[str] = Field(default_factory=list)
    task_types:   list[str] = Field(default_factory=list)  # code_generation, review, etc.
    requires_approval: bool = False
    is_public:    bool = False                          # visible to whole workspace
    cost_policy:  str = "local_only"                   # local_only | allow_paid | budget_X
    tags:         list[str] = Field(default_factory=list)
    created_at:   float = Field(default_factory=time.time)
    updated_at:   float = Field(default_factory=time.time)
    # Audit fields
    last_used_at: float | None = None
    use_count:    int = 0

    def touch(self) -> None:
        self.updated_at = time.time()

    def model_post_init(self, __context: Any) -> None:
        self.sync_compat_fields()

    def sync_compat_fields(self) -> None:
        """Keep legacy backend fields and Control Plane UI fields aligned."""
        if self.preferred_runtime and not self.runtime_id:
            self.runtime_id = self.preferred_runtime
        elif self.runtime_id and not self.preferred_runtime:
            self.preferred_runtime = self.runtime_id

        if self.task_specializations and not self.task_types:
            self.task_types = list(self.task_specializations)
        elif self.task_types and not self.task_specializations:
            self.task_specializations = list(self.task_types)

    def record_use(self) -> None:
        self.last_used_at = time.time()
        self.use_count += 1

    def as_dict(self) -> dict[str, Any]:
        self.sync_compat_fields()
        return self.model_dump()


class AgentCreateRequest(BaseModel):
    name:          str
    role:          str = ""
    description:   str = ""
    model:         str = "qwen3-coder:30b"
    system_prompt: str = ""
    preferred_runtime: str | None = None
    runtime_id:    str | None = None
    fallback_runtimes: list[str] = Field(default_factory=list)
    task_specializations: list[str] = Field(default_factory=list)
    task_types:    list[str] = Field(default_factory=list)
    requires_approval: bool = False
    is_public:     bool = False
    cost_policy:   str = "local_only"
    tags:          list[str] = Field(default_factory=list)


class AgentUpdateRequest(BaseModel):
    name:          str | None = None
    role:          str | None = None
    description:   str | None = None
    model:         str | None = None
    system_prompt: str | None = None
    preferred_runtime: str | None = None
    runtime_id:    str | None = None
    fallback_runtimes: list[str] | None = None
    task_specializations: list[str] | None = None
    task_types:    list[str] | None = None
    requires_approval: bool | None = None
    is_public:     bool | None = None
    cost_policy:   str | None = None
    tags:          list[str] | None = None


# ── Store ─────────────────────────────────────────────────────────────────────

class AgentStore:
    """CRUD store for AgentDefinition objects.

    Uses MongoDB when a `db` client is provided; falls back to an
    in-memory dict for testing or when MongoDB is unavailable.
    """

    COLLECTION = "agent_definitions"

    def __init__(self, db: Any = None) -> None:
        self._db = db
        self._mem: dict[str, AgentDefinition] = {}

    # ── private helpers ───────────────────────────────────────────────────────

    @property
    def _col(self):
        return self._db[self.COLLECTION] if self._db is not None else None

    def _from_doc(self, doc: dict) -> AgentDefinition:
        doc.pop("_id", None)
        return AgentDefinition(**doc)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(self, agent: AgentDefinition) -> AgentDefinition:
        if self._col is not None:
            await self._col.insert_one(agent.as_dict())
        else:
            self._mem[agent.agent_id] = agent
        return agent

    async def get(
        self,
        agent_id: str,
        owner_id: str | None = None,
    ) -> AgentDefinition | None:
        """Return an agent by ID.

        If *owner_id* is provided, enforces that the agent belongs to
        that user (or is public/workspace).  Pass ``owner_id=None``
        to bypass owner check (admin use).
        """
        if self._col is not None:
            query: dict[str, Any] = {"agent_id": agent_id}
            doc = await self._col.find_one(query)
            if doc is None:
                return None
            agent = self._from_doc(doc)
        else:
            agent = self._mem.get(agent_id)
            if agent is None:
                return None

        if owner_id is not None and agent.owner_id != owner_id and not agent.is_public:
            return None
        return agent

    async def update(self, agent: AgentDefinition) -> None:
        agent.touch()
        if self._col is not None:
            await self._col.replace_one(
                {"agent_id": agent.agent_id}, agent.as_dict(), upsert=True
            )
        else:
            self._mem[agent.agent_id] = agent

    async def delete(self, agent_id: str, owner_id: str | None = None) -> bool:
        """Delete an agent.  Returns True on success, False if not found/unauthorised."""
        agent = await self.get(agent_id)
        if agent is None:
            return False
        if owner_id is not None and agent.owner_id != owner_id:
            return False
        if self._col is not None:
            await self._col.delete_one({"agent_id": agent_id})
        else:
            self._mem.pop(agent_id, None)
        return True

    async def list_for_user(
        self,
        owner_id: str,
        include_public: bool = True,
    ) -> list[AgentDefinition]:
        """Return all agents owned by *owner_id*, optionally including public agents."""
        if self._col is not None:
            query: dict[str, Any] = {"owner_id": owner_id}
            if include_public:
                query = {"$or": [{"owner_id": owner_id}, {"is_public": True}]}
            cursor = self._col.find(query)
            docs = await cursor.to_list(length=1000)
            return [self._from_doc(d) for d in docs]
        else:
            result = [
                a for a in self._mem.values()
                if a.owner_id == owner_id or (include_public and a.is_public)
            ]
            return sorted(result, key=lambda a: a.created_at, reverse=True)

    async def list_all(self) -> list[AgentDefinition]:
        """Return all agents in the system (admin use only)."""
        if self._col is not None:
            cursor = self._col.find({})
            docs = await cursor.to_list(length=10000)
            return [self._from_doc(d) for d in docs]
        else:
            return sorted(self._mem.values(), key=lambda a: a.created_at, reverse=True)

    async def count_for_user(self, owner_id: str) -> int:
        if self._col is not None:
            return await self._col.count_documents({"owner_id": owner_id})
        return sum(1 for a in self._mem.values() if a.owner_id == owner_id)


# ── Singleton ─────────────────────────────────────────────────────────────────

_store: AgentStore | None = None


def get_agent_store(db: Any = None) -> AgentStore:
    global _store
    if _store is None:
        _store = AgentStore(db=db)
    return _store


def set_agent_store(store: AgentStore) -> None:
    """Set the global agent store instance (e.g., with MongoDB on startup)."""
    global _store
    _store = store
