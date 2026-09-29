from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class ProblemEvaluationAdapter(Protocol):
    problem_type: str

    def execute(self, *, repo_root: Path, record: dict[str, Any], package: dict[str, Any], algorithm: type) -> dict[str, Any]: ...


class ProblemEvaluationRegistry:
    def __init__(self) -> None:
        self._items: dict[str, ProblemEvaluationAdapter] = {}

    def register(self, adapter: ProblemEvaluationAdapter) -> None:
        self._items[adapter.problem_type] = adapter

    def get(self, problem_type: str) -> ProblemEvaluationAdapter:
        try:
            return self._items[problem_type]
        except KeyError as exc:
            raise ValueError(f"UNSUPPORTED_PROBLEM_TYPE: no evaluation adapter registered for {problem_type}") from exc


def default_registry() -> ProblemEvaluationRegistry:
    from .user_association import UserAssociationEvaluationAdapter

    registry = ProblemEvaluationRegistry()
    registry.register(UserAssociationEvaluationAdapter())
    return registry
