"""
Agent trajectory recorder – captures every step an agent takes so runs
can be replayed, diffed and scored offline (inspired by OpenHarness).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class TrajectoryStep:
    """A single action/observation pair in an agent trajectory."""

    step_id: int
    timestamp: float
    action_type: str          # e.g. "tool_call", "llm_response", "browser", "bash"
    action_input: Any
    observation: Any
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trajectory:
    """
    Complete record of one agent run against one task.

    Compatible with the OpenHarness trajectory schema so recordings
    can be fed into external evaluation pipelines.
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None
    task_description: Optional[str] = None
    agent_name: str = "default"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    success: Optional[bool] = None
    score: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    # Internal step counter
    _step_counter: int = field(default=0, repr=False, compare=False)

    # ------------------------------------------------------------------ #
    #  Recording                                                           #
    # ------------------------------------------------------------------ #

    def record(
        self,
        action_type: str,
        action_input: Any,
        observation: Any,
        *,
        metadata: dict | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
    ) -> TrajectoryStep:
        """Append a step and return it."""
        self._step_counter += 1
        step = TrajectoryStep(
            step_id=self._step_counter,
            timestamp=time.time(),
            action_type=action_type,
            action_input=action_input,
            observation=observation,
            metadata=metadata or {},
            error=error,
            duration_ms=duration_ms,
        )
        self.steps.append(step)
        return step

    def finish(
        self,
        final_answer: str | None = None,
        *,
        success: bool | None = None,
        score: float | None = None,
    ) -> None:
        """Mark the trajectory as complete."""
        self.end_time = time.time()
        self.final_answer = final_answer
        self.success = success
        self.score = score

    # ------------------------------------------------------------------ #
    #  Serialisation                                                       #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "agent_name": self.agent_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": (self.end_time - self.start_time) if self.end_time else None,
            "steps": [s.to_dict() for s in self.steps],
            "step_count": len(self.steps),
            "final_answer": self.final_answer,
            "success": self.success,
            "score": self.score,
            "metadata": self.metadata,
        }

    def save(self, directory: str | Path = "trajectories") -> Path:
        """Persist trajectory as JSON and return the file path."""
        out_dir = Path(directory)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.run_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Trajectory":
        """Reload a previously saved trajectory (read-only replay)."""
        data = json.loads(Path(path).read_text())
        traj = cls(
            run_id=data["run_id"],
            task_id=data.get("task_id"),
            task_description=data.get("task_description"),
            agent_name=data.get("agent_name", "default"),
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            final_answer=data.get("final_answer"),
            success=data.get("success"),
            score=data.get("score"),
            metadata=data.get("metadata", {}),
        )
        for s in data.get("steps", []):
            traj.steps.append(
                TrajectoryStep(
                    step_id=s["step_id"],
                    timestamp=s["timestamp"],
                    action_type=s["action_type"],
                    action_input=s["action_input"],
                    observation=s["observation"],
                    metadata=s.get("metadata", {}),
                    error=s.get("error"),
                    duration_ms=s.get("duration_ms", 0.0),
                )
            )
        traj._step_counter = len(traj.steps)
        return traj

    # ------------------------------------------------------------------ #
    #  Quick stats                                                         #
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        """Return a summary dict suitable for logging / leaderboards."""
        tool_calls = [s for s in self.steps if s.action_type == "tool_call"]
        errors = [s for s in self.steps if s.error]
        durations = [s.duration_ms for s in self.steps if s.duration_ms > 0]
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "step_count": len(self.steps),
            "tool_call_count": len(tool_calls),
            "error_count": len(errors),
            "avg_step_ms": (sum(durations) / len(durations)) if durations else 0.0,
            "total_duration_s": (
                (self.end_time - self.start_time) if self.end_time else None
            ),
            "success": self.success,
            "score": self.score,
        }
