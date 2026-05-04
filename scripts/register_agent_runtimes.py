#!/usr/bin/env python3
"""Register agent runtimes into the local agent store.

Usage:
  python scripts/register_agent_runtimes.py [--reset]

This script:
1. Creates AgentDefinition entries for: hermes, opencode, goose, task_harness, aider
2. Stores them in MongoDB (or in-memory fallback)
3. Reports registered agents with their IDs

Options:
  --reset    Clear existing runtime agents before registering new ones
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.store import AgentStore, AgentDefinition

log = logging.getLogger("register-runtimes")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)

SYSTEM_OWNER = "system"

# Runtime role mapping
RUNTIME_ROLES = {
    "hermes": {
        "name": "Hermes (Executor)",
        "description": "Fast, lightweight code execution runtime",
        "task_types": ["code_generation", "refactoring"],
        "model": "hermes:latest",
    },
    "opencode": {
        "name": "OpenCode (Generator)",
        "description": "Code generation and scaffolding runtime",
        "task_types": ["code_generation", "scaffolding"],
        "model": "opencode:latest",
    },
    "goose": {
        "name": "Goose (Multi-Purpose)",
        "description": "Multi-purpose AI development agent",
        "task_types": ["code_generation", "testing", "review"],
        "model": "goose:latest",
    },
    "task_harness": {
        "name": "Task Harness",
        "description": "Compatible external harness for long-running, multi-file agent workflows",
        "task_types": ["code_generation", "repo_editing", "scheduled", "agent_delegation"],
        "model": "task-harness:latest",
    },
    "aider": {
        "name": "Aider (Pair Programmer)",
        "description": "Pair programming and collaborative development",
        "task_types": ["code_generation", "refactoring", "debugging"],
        "model": "aider:latest",
    },
}


async def register_runtimes(store: AgentStore, reset: bool = False) -> None:
    """Register runtime agents in the store."""
    for runtime_id, config in RUNTIME_ROLES.items():

        # Delete existing if reset requested
        if reset:
            await store.delete(runtime_id, owner_id=SYSTEM_OWNER)
            log.info(f"Reset: deleted existing {runtime_id}")

        # Create new agent definition
        agent = AgentDefinition(
            agent_id=runtime_id,
            owner_id=SYSTEM_OWNER,
            name=config["name"],
            description=config["description"],
            model=config["model"],
            runtime_id=runtime_id,
            task_types=config["task_types"],
            is_public=True,  # Runtimes are workspace-visible
            cost_policy="local_only",
            tags=["runtime", "system"],
        )

        # Store the agent
        await store.create(agent)
        log.info(f"✓ Registered: {agent.agent_id:15} → {agent.name}")


async def main():
    import argparse
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Clear existing runtime agents first")
    parser.add_argument("--mongo-url", default="mongodb://localhost:27017", help="MongoDB connection URL")
    parser.add_argument("--db-name", default="local_llm_server", help="Database name")
    args = parser.parse_args()

    # Try to connect to MongoDB
    store = AgentStore(db=None)
    try:
        client = AsyncIOMotorClient(args.mongo_url, serverSelectionTimeoutMS=2000)
        # Test connection
        await client.server_info()
        db = client[args.db_name]
        store = AgentStore(db=db)
        log.info(f"✓ Connected to MongoDB at {args.mongo_url}/{args.db_name}")
    except Exception as e:
        log.warning(f"MongoDB unavailable ({e}), using in-memory store")
        log.info("  To persist agents, ensure MongoDB is running and accessible")
        store = AgentStore(db=None)

    # Register runtimes
    log.info(f"Registering agent runtimes: {', '.join(RUNTIME_ROLES.keys())}...")
    await register_runtimes(store, reset=args.reset)

    # List registered agents
    agents = await store.list_all()
    log.info(f"\n{'─' * 70}")
    log.info(f"Summary: {len(agents)} agent(s) in system store")
    for agent in agents:
        log.info(f"  {agent.agent_id:20} | {agent.name} | runtime: {agent.runtime_id}")


if __name__ == "__main__":
    asyncio.run(main())
