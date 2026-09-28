"""
优化器 / 目标函数注册表 / Optimizer and objective registries.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import Objective, Optimizer
from .errors import ObjectiveNotFoundError, OptimizerNotFoundError
from .objectives import PropagationUtilityV01
from .optimizers import GridSearchOptimizer


class OptimizerRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Optimizer]] = {}

    def register(self, optimizer_id: str, factory: Callable[[], Optimizer]) -> None:
        if optimizer_id in self._factories:
            raise ValueError(f"Optimizer '{optimizer_id}' already registered")
        self._factories[optimizer_id] = factory

    def create(self, optimizer_id: str) -> Optimizer:
        try:
            return self._factories[optimizer_id]()
        except KeyError:
            raise OptimizerNotFoundError(
                f"Unknown optimizer '{optimizer_id}'. Available: {', '.join(sorted(self._factories)) or '-'}"
            ) from None

    def list(self) -> list[Optimizer]:
        return [self._factories[i]() for i in sorted(self._factories)]


class ObjectiveRegistry:
    def __init__(self) -> None:
        self._objectives: dict[str, Objective] = {}

    def register(self, objective: Objective) -> None:
        if objective.id in self._objectives:
            raise ValueError(f"Objective '{objective.id}' already registered")
        self._objectives[objective.id] = objective

    def get(self, objective_id: str) -> Objective:
        try:
            return self._objectives[objective_id]
        except KeyError:
            raise ObjectiveNotFoundError(
                f"Unknown objective '{objective_id}'. Available: {', '.join(sorted(self._objectives)) or '-'}"
            ) from None

    def list(self) -> list[Objective]:
        return [self._objectives[i] for i in sorted(self._objectives)]


def default_optimizer_registry() -> OptimizerRegistry:
    registry = OptimizerRegistry()
    registry.register("grid_search", GridSearchOptimizer)
    return registry


def default_objective_registry() -> ObjectiveRegistry:
    registry = ObjectiveRegistry()
    registry.register(PropagationUtilityV01())
    return registry
