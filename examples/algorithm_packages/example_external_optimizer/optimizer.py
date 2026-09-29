from __future__ import annotations

import random
from typing import Any

from algorithms import (
    ALGORITHM_SDK_VERSION,
    Algorithm,
    AlgorithmCapabilities,
    AlgorithmCategory,
    AlgorithmMetadata,
    AlgorithmProblem,
    AlgorithmStatus,
    HyperparameterDefinition,
    HyperparameterType,
    StopReason,
)
from optimization.parameters import ParameterBounds
from algorithms import AlgorithmRecommendation


class ExampleExternalOptimizer(Algorithm):
    """Small deterministic optimizer used to prove the trusted SDK lifecycle.

    The package only proposes association vectors. The platform remains responsible
    for candidate validation, KPI evaluation, constraints, trace and evidence.
    """

    _metadata = AlgorithmMetadata(
        algorithm_id="example_external_optimizer",
        name_zh="外部示例优化器",
        name_en="Example External Optimizer",
        version="0.1.0",
        category=AlgorithmCategory.EXTERNAL,
        description_zh="Day 10 外部算法接入示例。",
        description_en="A deterministic external package onboarding example.",
        purpose_zh="演示包校验、冒烟测试和平台负责评价。",
        purpose_en="Demonstrate package validation, smoke testing and platform-owned evaluation.",
        provider="Day 10 example package",
        learning_algorithm=False,
        capabilities=AlgorithmCapabilities(
            supports_discrete=False,
            supports_continuous=False,
            supports_integer=False,
            supports_categorical=True,
            supports_vector=False,
            supports_constraints=False,
            supports_multi_objective=False,
            supports_batch_suggestions=False,
            supports_iterative_feedback=True,
            supports_auto_configuration=False,
            max_parameters=1,
        ),
        hyperparameter_schema=[
            HyperparameterDefinition(
                id="seed", name_zh="随机种子", name_en="Seed", type=HyperparameterType.INTEGER,
                default=20260929, bounds=ParameterBounds(lower=0, upper=2147483647),
            ),
            HyperparameterDefinition(
                id="candidate_offset", name_zh="候选偏移", name_en="Candidate offset", type=HyperparameterType.INTEGER,
                default=1, bounds=ParameterBounds(lower=1, upper=50),
            ),
        ],
        supported_problem_types=["user_association"],
        source="external package",
        status=AlgorithmStatus.AVAILABLE,
        sdk_version=ALGORITHM_SDK_VERSION,
    )

    @classmethod
    def metadata(cls) -> AlgorithmMetadata:
        return cls._metadata

    def __init__(self) -> None:
        self._choices: list[list[str]] = []
        self._parameter_id = "association_vector"
        self._used: set[tuple[str, ...]] = set()
        self._results: list[Any] = []
        self._best: Any | None = None
        self._stop_reason: StopReason | None = None

    def initialize(self, problem: AlgorithmProblem, hyperparameters: dict[str, Any], incumbents: list[Any]) -> None:
        self._parameter_id = problem.parameter_space.parameters[0].id
        definition = problem.parameter_space.parameters[0]
        self._choices = [list(choice) for choice in (definition.choices or [definition.default])]
        offset = int(hyperparameters.get("candidate_offset", 1))
        rng = random.Random(int(hyperparameters.get("seed", 20260929)))
        if len(self._choices) > 1:
            tail = self._choices[1:]
            rng.shuffle(tail)
            self._choices = [self._choices[0]] + tail
            self._choices = self._choices[:1] + self._choices[1 + min(offset - 1, max(0, len(self._choices) - 2)):]
        self._used = set()
        self._results = list(incumbents)
        self._best = max(incumbents, key=lambda item: item.score() if item.score() is not None else float("-inf"), default=None)
        self._stop_reason = None

    def suggest(self, max_suggestions: int) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        for choice in self._choices:
            key = tuple(choice)
            if key in self._used:
                continue
            self._used.add(key)
            suggestions.append({self._parameter_id: list(choice)})
            if len(suggestions) >= max_suggestions:
                break
        if not suggestions:
            self._stop_reason = StopReason.NO_IMPROVEMENT
        return suggestions

    def observe(self, results: list[Any]) -> None:
        self._results.extend(results)
        for result in results:
            if result.objective is None:
                continue
            if self._best is None or result.objective > self._best.objective:
                self._best = result
        if len(self._results) >= 3 or len(self._used) >= len(self._choices):
            self._stop_reason = StopReason.MAX_ITERATIONS

    def should_stop(self) -> StopReason | None:
        return self._stop_reason

    def finalize(self) -> AlgorithmRecommendation:
        return AlgorithmRecommendation(
            parameters=self._best.parameters if self._best is not None else {},
            note=f"evaluated_candidates={len(self._results)}",
        )

    def state_metadata(self) -> dict[str, Any]:
        return {"used_candidates": len(self._used), "observed_results": len(self._results)}
