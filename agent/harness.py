"""
Evaluation harness – runs an agent against a Task, records the
Trajectory, scores it and returns structured results.

Inspired by OpenHarness' clean separation between:
  • task definition  (agent/task.py)
  • trajectory recording  (agent/trajectory.py)
  • evaluation / scoring  (this file)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from agent.task import Task
from agent.trajectory import Trajectory

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Result & leaderboard types                                         #
# ------------------------------------------------------------------ #

@dataclass
class EvalResult:
    """Outcome of running one task through the harness."""

    run_id: str
    task_id: str
    agent_name: str
    success: bool
    score: float                      # 0.0 – 1.0
    step_count: int
    duration_s: float
    final_answer: Optional[str]
    trajectory_path: Optional[str]   # where the .json was saved
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "success": self.success,
            "score": self.score,
            "step_count": self.step_count,
            "duration_s": self.duration_s,
            "final_answer": self.final_answer,
            "trajectory_path": self.trajectory_path,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkReport:
    """Aggregated results for a full benchmark suite run."""

    agent_name: str
    task_results: list[EvalResult] = field(default_factory=list)

    @property
    def total_tasks(self) -> int:
        return len(self.task_results)

    @property
    def successful_tasks(self) -> int:
        return sum(1 for r in self.task_results if r.success)

    @property
    def success_rate(self) -> float:
        if not self.task_results:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def avg_score(self) -> float:
        if not self.task_results:
            return 0.0
        return sum(r.score for r in self.task_results) / self.total_tasks

    @property
    def avg_steps(self) -> float:
        if not self.task_results:
            return 0.0
        return sum(r.step_count for r in self.task_results) / self.total_tasks

    def summary(self) -> dict:
        by_category: dict[str, list[EvalResult]] = {}
        for r in self.task_results:
            cat = r.metadata.get("category", "unknown")
            by_category.setdefault(cat, []).append(r)

        return {
            "agent_name": self.agent_name,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "success_rate": round(self.success_rate, 4),
            "avg_score": round(self.avg_score, 4),
            "avg_steps": round(self.avg_steps, 2),
            "by_category": {
                cat: {
                    "count": len(results),
                    "success_rate": round(
                        sum(1 for r in results if r.success) / len(results), 4
                    ),
                }
                for cat, results in by_category.items()
            },
        }

    def print_report(self) -> None:
        s = self.summary()
        print("\n" + "=" * 60)
        print(f"  BENCHMARK REPORT  –  agent: {s['agent_name']}")
        print("=" * 60)
        print(f"  Tasks run    : {s['total_tasks']}")
        print(f"  Successful   : {s['successful_tasks']}")
        print(f"  Success rate : {s['success_rate']:.1%}")
        print(f"  Avg score    : {s['avg_score']:.3f}")
        print(f"  Avg steps    : {s['avg_steps']:.1f}")
        if s["by_category"]:
            print("\n  By category:")
            for cat, stats in s["by_category"].items():
                print(
                    f"    {cat:<20} {stats['count']} tasks  "
                    f"SR={stats['success_rate']:.1%}"
                )
        print("=" * 60 + "\n")


# ------------------------------------------------------------------ #
#  Harness                                                            #
# ------------------------------------------------------------------ #

# Type alias: an agent is any async callable that receives
# (task_description, allowed_tools, trajectory) and returns a string answer.
AgentFn = Callable[[str, list[str], Trajectory], Any]


class EvalHarness:
    """
    Runs agent functions against Tasks, records Trajectories and
    produces EvalResults / BenchmarkReports.

    Usage
    -----
    harness = EvalHarness(agent_fn=my_agent, agent_name="my_agent_v1")
    result  = await harness.run_task(task)
    report  = await harness.run_benchmark(tasks)
    """

    def __init__(
        self,
        agent_fn: AgentFn,
        agent_name: str = "agent",
        trajectory_dir: str = "trajectories",
        save_trajectories: bool = True,
    ) -> None:
        self.agent_fn = agent_fn
        self.agent_name = agent_name
        self.trajectory_dir = trajectory_dir
        self.save_trajectories = save_trajectories

    async def run_task(self, task: Task) -> EvalResult:
        """Execute the agent on a single task and return an EvalResult."""
        traj = Trajectory(
            task_id=task.task_id,
            task_description=task.description,
            agent_name=self.agent_name,
        )

        start = time.time()
        final_answer: Optional[str] = None
        error_msg: Optional[str] = None
        success = False
        score = 0.0

        try:
            logger.info("Harness: starting task %s", task.task_id)

            # Wrap with timeout
            answer = await asyncio.wait_for(
                self._run_agent(task, traj),
                timeout=task.timeout_s,
            )
            final_answer = str(answer) if answer is not None else ""
            success, score = task.evaluate_answer(final_answer)

        except asyncio.TimeoutError:
            error_msg = f"Task timed out after {task.timeout_s}s"
            logger.warning("Harness: %s – %s", task.task_id, error_msg)

        except NotImplementedError as exc:
            # LLM_JUDGE / HUMAN criterion – can't score automatically
            error_msg = f"Non-automated criterion: {exc}"
            success = False
            score = 0.0

        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)
            logger.exception("Harness: task %s raised an error", task.task_id)

        finally:
            duration = time.time() - start
            traj.finish(
                final_answer=final_answer,
                success=success,
                score=score,
            )

        # Persist trajectory
        traj_path: Optional[str] = None
        if self.save_trajectories:
            try:
                traj_path = str(traj.save(self.trajectory_dir))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not save trajectory: %s", exc)

        return EvalResult(
            run_id=traj.run_id,
            task_id=task.task_id,
            agent_name=self.agent_name,
            success=success,
            score=score,
            step_count=len(traj.steps),
            duration_s=round(duration, 3),
            final_answer=final_answer,
            trajectory_path=traj_path,
            error=error_msg,
            metadata={"category": task.category, "difficulty": task.difficulty.value},
        )

    async def _run_agent(self, task: Task, traj: Trajectory) -> str:
        """Delegate to the agent callable (sync or async)."""
        result = self.agent_fn(task.description, task.allowed_tools, traj)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def run_benchmark(
        self,
        tasks: list[Task],
        *,
        concurrency: int = 1,
    ) -> BenchmarkReport:
        """
        Run multiple tasks and aggregate into a BenchmarkReport.

        Set concurrency > 1 to run tasks in parallel (use with care –
        some agent implementations are not re-entrant).
        """
        report = BenchmarkReport(agent_name=self.agent_name)
        semaphore = asyncio.Semaphore(concurrency)

        async def _bounded(task: Task) -> EvalResult:
            async with semaphore:
                return await self.run_task(task)

        results = await asyncio.gather(*[_bounded(t) for t in tasks])
        report.task_results = list(results)
        return report
