"""
Task definition schema for the evaluation harness.

Inspired by OpenHarness' structured task specs – each task declares
what the agent must do, which tools are allowed, and how success is
measured.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class SuccessCriterionType(str, Enum):
    EXACT_MATCH = "exact_match"       # answer == expected
    CONTAINS = "contains"             # expected in answer
    REGEX = "regex"                   # re.search(pattern, answer)
    CALLABLE = "callable"             # custom fn(answer) -> bool
    HUMAN = "human"                   # requires manual review
    LLM_JUDGE = "llm_judge"           # scored by a judge LLM


@dataclass
class SuccessCriterion:
    criterion_type: SuccessCriterionType
    expected: Optional[Any] = None        # for exact_match / contains / regex
    judge_fn: Optional[Callable] = None   # for callable
    judge_prompt: Optional[str] = None    # for llm_judge
    score_threshold: float = 1.0          # minimum score to count as success

    def evaluate(self, answer: str) -> tuple[bool, float]:
        """
        Returns (success: bool, score: float ∈ [0, 1]).
        Raises NotImplementedError for HUMAN / LLM_JUDGE – those need
        external evaluation.
        """
        import re

        ct = self.criterion_type

        if ct == SuccessCriterionType.EXACT_MATCH:
            match = str(answer).strip() == str(self.expected).strip()
            return match, 1.0 if match else 0.0

        if ct == SuccessCriterionType.CONTAINS:
            match = str(self.expected).lower() in str(answer).lower()
            return match, 1.0 if match else 0.0

        if ct == SuccessCriterionType.REGEX:
            match = bool(re.search(str(self.expected), str(answer)))
            return match, 1.0 if match else 0.0

        if ct == SuccessCriterionType.CALLABLE:
            if self.judge_fn is None:
                raise ValueError("judge_fn must be set for CALLABLE criterion")
            result = self.judge_fn(answer)
            if isinstance(result, tuple):
                success, score = result
            else:
                success = bool(result)
                score = 1.0 if success else 0.0
            return success, score

        if ct in (SuccessCriterionType.HUMAN, SuccessCriterionType.LLM_JUDGE):
            raise NotImplementedError(
                f"Criterion type {ct} requires external evaluation"
            )

        raise ValueError(f"Unknown criterion type: {ct}")


@dataclass
class Task:
    """
    A fully-specified evaluation task.

    Fields mirror the OpenHarness task schema so recordings/results
    can be compared across harnesses.
    """

    task_id: str
    description: str
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    category: str = "general"
    allowed_tools: list[str] = field(default_factory=list)   # empty = all tools
    max_steps: int = 50
    timeout_s: float = 300.0
    success_criterion: Optional[SuccessCriterion] = None
    initial_context: dict = field(default_factory=dict)      # seed data for agent
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    #  Evaluation                                                          #
    # ------------------------------------------------------------------ #

    def evaluate_answer(self, answer: str) -> tuple[bool, float]:
        """
        Score the agent's final answer.
        Returns (success, score).
        """
        if self.success_criterion is None:
            # No automated criterion – needs human review
            return False, 0.0
        return self.success_criterion.evaluate(answer)

    # ------------------------------------------------------------------ #
    #  Serialisation (criterion callables are not preserved)               #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        sc = self.success_criterion
        criterion_dict = None
        if sc is not None:
            criterion_dict = {
                "criterion_type": sc.criterion_type.value,
                "expected": sc.expected,
                "judge_prompt": sc.judge_prompt,
                "score_threshold": sc.score_threshold,
            }
        return {
            "task_id": self.task_id,
            "description": self.description,
            "difficulty": self.difficulty.value,
            "category": self.category,
            "allowed_tools": self.allowed_tools,
            "max_steps": self.max_steps,
            "timeout_s": self.timeout_s,
            "success_criterion": criterion_dict,
            "initial_context": self.initial_context,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def save(self, directory: str | Path = "tasks") -> Path:
        out_dir = Path(directory)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.task_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Task":
        data = json.loads(Path(path).read_text())
        sc_data = data.pop("success_criterion", None)
        sc = None
        if sc_data:
            sc = SuccessCriterion(
                criterion_type=SuccessCriterionType(sc_data["criterion_type"]),
                expected=sc_data.get("expected"),
                judge_prompt=sc_data.get("judge_prompt"),
                score_threshold=sc_data.get("score_threshold", 1.0),
            )
        return cls(
            success_criterion=sc,
            difficulty=TaskDifficulty(data.pop("difficulty", "medium")),
            **data,
        )


# ------------------------------------------------------------------ #
#  Built-in benchmark task catalogue                                  #
# ------------------------------------------------------------------ #

BUILTIN_TASKS: list[Task] = [
    Task(
        task_id="web_search_capital",
        description="Find the current capital city of France and return only the city name.",
        difficulty=TaskDifficulty.EASY,
        category="web",
        allowed_tools=["browser", "search"],
        max_steps=5,
        success_criterion=SuccessCriterion(
            criterion_type=SuccessCriterionType.EXACT_MATCH,
            expected="Paris",
        ),
        tags=["web", "factual"],
    ),
    Task(
        task_id="code_reverse_string",
        description=(
            "Write a Python function called `reverse_string` that takes a string "
            "and returns it reversed. Return only the function definition."
        ),
        difficulty=TaskDifficulty.EASY,
        category="coding",
        allowed_tools=["bash"],
        max_steps=10,
        success_criterion=SuccessCriterion(
            criterion_type=SuccessCriterionType.CONTAINS,
            expected="def reverse_string",
        ),
        tags=["coding", "python"],
    ),
    Task(
        task_id="multi_step_math",
        description=(
            "Calculate: (142 * 37) + (891 / 3) - 128. Return only the numeric answer."
        ),
        difficulty=TaskDifficulty.MEDIUM,
        category="math",
        allowed_tools=["bash"],
        max_steps=8,
        success_criterion=SuccessCriterion(
            criterion_type=SuccessCriterionType.EXACT_MATCH,
            expected="5421.0",
        ),
        tags=["math", "arithmetic"],
    ),
    Task(
        task_id="file_read_summarise",
        description=(
            "Read the file README.md in the current directory and return a one-sentence "
            "summary of what the project does."
        ),
        difficulty=TaskDifficulty.MEDIUM,
        category="file_system",
        allowed_tools=["bash"],
        max_steps=5,
        success_criterion=SuccessCriterion(
            criterion_type=SuccessCriterionType.CONTAINS,
            expected="agent",
        ),
        tags=["file", "summarisation"],
    ),
]
