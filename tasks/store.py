"""tasks/store.py — MongoDB-backed task store.

Falls back to in-memory storage when MongoDB is unavailable so the
system degrades gracefully during development.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from tasks.models import Task, TaskStatus, TaskPriority

log = logging.getLogger("qwen-proxy")


class TaskStore:
    """Persistent task store backed by MongoDB.

    Uses the same motor client pattern as the rest of the application.
    Falls back to an in-memory dict when no motor client is injected.
    """

    def __init__(self, db: Any = None) -> None:
        """
        Args:
            db: motor AsyncIOMotorDatabase instance, or None for in-memory mode.
        """
        self._db = db
        self._mem: dict[str, dict] = {}  # fallback in-memory store
        self._mode = "mongo" if db is not None else "memory"
        if self._mode == "memory":
            log.warning("TaskStore: running in in-memory mode (no MongoDB). Data will be lost on restart.")

    @property
    def _collection(self):
        return self._db["tasks"] if self._db is not None else None

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(self, task: Task) -> Task:
        doc = task.model_dump()
        if self._mode == "mongo":
            await self._collection.insert_one({**doc, "_id": task.task_id})
        else:
            self._mem[task.task_id] = doc
        return task

    async def get(self, task_id: str, owner_id: str | None = None) -> Task | None:
        """Fetch a task by ID.  If owner_id is set, enforces ownership."""
        if self._mode == "mongo":
            query: dict[str, Any] = {"task_id": task_id}
            if owner_id:
                query["owner_id"] = owner_id
            doc = await self._collection.find_one(query, {"_id": 0})
        else:
            doc = self._mem.get(task_id)
            if doc and owner_id and doc.get("owner_id") != owner_id:
                return None
        return Task.model_validate(doc) if doc else None

    async def update(self, task: Task) -> Task:
        task.touch()
        doc = task.model_dump()
        if self._mode == "mongo":
            await self._collection.replace_one(
                {"task_id": task.task_id},
                {**doc, "_id": task.task_id},
                upsert=True,
            )
        else:
            self._mem[task.task_id] = doc
        return task

    async def delete(self, task_id: str, owner_id: str | None = None) -> bool:
        if self._mode == "mongo":
            q: dict[str, Any] = {"task_id": task_id}
            if owner_id:
                q["owner_id"] = owner_id
            result = await self._collection.delete_one(q)
            return result.deleted_count > 0
        else:
            if task_id in self._mem:
                if owner_id and self._mem[task_id].get("owner_id") != owner_id:
                    return False
                del self._mem[task_id]
                return True
            return False

    # ── Queries ───────────────────────────────────────────────────────────────

    async def list_for_user(
        self,
        owner_id: str,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        agent_id: str | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks for a specific user with optional filters."""
        query: dict[str, Any] = {"owner_id": owner_id}
        if status:
            query["status"] = status.value
        if priority:
            query["priority"] = priority.value
        if agent_id:
            query["agent_id"] = agent_id
        if tag:
            query["tags"] = tag

        if self._mode == "mongo":
            cursor = self._collection.find(query, {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit)
            docs = await cursor.to_list(length=limit)
        else:
            docs = [
                v for v in self._mem.values()
                if v.get("owner_id") == owner_id
                and (not status or v.get("status") == status.value)
                and (not priority or v.get("priority") == priority.value)
                and (not agent_id or v.get("agent_id") == agent_id)
                and (not tag or tag in (v.get("tags") or []))
            ]
            docs.sort(key=lambda d: d.get("created_at", 0), reverse=True)
            docs = docs[offset: offset + limit]

        return [Task.model_validate(d) for d in docs]

    async def list_all(
        self,
        *,
        status: TaskStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """Admin-only: list all tasks across all users."""
        query: dict[str, Any] = {}
        if status:
            query["status"] = status.value

        if self._mode == "mongo":
            cursor = self._collection.find(query, {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit)
            docs = await cursor.to_list(length=limit)
        else:
            docs = list(self._mem.values())
            if status:
                docs = [d for d in docs if d.get("status") == status.value]
            docs.sort(key=lambda d: d.get("created_at", 0), reverse=True)
            docs = docs[offset: offset + limit]

        return [Task.model_validate(d) for d in docs]

    async def list_pending(self, *, limit: int = 50) -> list[Task]:
        """Return tasks queued for agent execution."""
        if self._mode == "mongo":
            cursor = self._collection.find(
                {"pending_agent_run": True, "status": {"$in": [TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value]}},
                {"_id": 0},
            ).sort("updated_at", 1).limit(limit)
            docs = await cursor.to_list(length=limit)
        else:
            docs = [
                value for value in self._mem.values()
                if value.get("pending_agent_run") is True
                and value.get("status") in {TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value}
            ]
            docs.sort(key=lambda d: d.get("updated_at", d.get("created_at", 0)))
            docs = docs[:limit]
        return [Task.model_validate(d) for d in docs]

    async def count_by_agent(
        self,
        *,
        owner_id: str | None = None,
        statuses: set[TaskStatus] | None = None,
    ) -> dict[str, int]:
        """Return task counts keyed by ``agent_id`` for the requested statuses."""
        status_values = {status.value for status in statuses} if statuses else None

        if self._mode == "mongo":
            match: dict[str, Any] = {"agent_id": {"$ne": None}}
            if owner_id is not None:
                match["owner_id"] = owner_id
            if status_values is not None:
                match["status"] = {"$in": sorted(status_values)}
            pipeline = [
                {"$match": match},
                {"$group": {"_id": "$agent_id", "count": {"$sum": 1}}},
            ]
            rows = await self._collection.aggregate(pipeline).to_list(length=1000)
            return {
                str(row.get("_id")): int(row.get("count") or 0)
                for row in rows
                if row.get("_id")
            }

        counts: dict[str, int] = {}
        for task in self._mem.values():
            agent_id = task.get("agent_id")
            if not agent_id:
                continue
            if owner_id is not None and task.get("owner_id") != owner_id:
                continue
            if status_values is not None and task.get("status") not in status_values:
                continue
            counts[str(agent_id)] = counts.get(str(agent_id), 0) + 1
        return counts

    async def count_for_user(self, owner_id: str) -> dict[str, int]:
        """Return counts per status for a user's tasks."""
        if self._mode == "mongo":
            pipeline = [
                {"$match": {"owner_id": owner_id}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
            result = await self._collection.aggregate(pipeline).to_list(length=20)
            return {r["_id"]: r["count"] for r in result}
        else:
            counts: dict[str, int] = {}
            for v in self._mem.values():
                if v.get("owner_id") == owner_id:
                    s = v.get("status", "todo")
                    counts[s] = counts.get(s, 0) + 1
            return counts

    async def get_due_soon(self, within_hours: int = 24) -> list[Task]:
        """Return tasks due within the next N hours (any user)."""
        deadline = time.time() + within_hours * 3600
        if self._mode == "mongo":
            cursor = self._collection.find(
                {"due_date": {"$lte": deadline, "$ne": None}, "status": {"$nin": ["done"]}},
                {"_id": 0},
            ).sort("due_date", 1).limit(20)
            docs = await cursor.to_list(length=20)
        else:
            docs = [
                v for v in self._mem.values()
                if v.get("due_date") and v["due_date"] <= deadline and v.get("status") != "done"
            ]
            docs.sort(key=lambda d: d.get("due_date", 0))
            docs = docs[:20]
        return [Task.model_validate(d) for d in docs]


_global_store: TaskStore | None = None


def get_task_store() -> TaskStore:
    """Get or create the global task store instance."""
    global _global_store
    if _global_store is None:
        _global_store = TaskStore()
    return _global_store


def set_task_store(store: TaskStore) -> None:
    """Set the global task store instance (e.g., during app startup with MongoDB)."""
    global _global_store
    _global_store = store
