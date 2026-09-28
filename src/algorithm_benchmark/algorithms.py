from __future__ import annotations

import random
from typing import Any

from algorithms.sdk import (
    Algorithm, AlgorithmCapabilities, AlgorithmCategory, AlgorithmMetadata, AlgorithmProblem,
    AlgorithmRecommendation, AlgorithmStatus, EvaluationResult, HyperparameterDefinition,
    HyperparameterType, HyperparameterValue, StopReason,
)
from optimization.parameters import ParameterBounds, ParameterType, ParameterValue


PROBLEM_TYPE = "user_association"
ASSOCIATION_PARAMETER = "association_vector"


def _metadata(algorithm_id: str, name_zh: str, name_en: str, category: AlgorithmCategory,
              description: str, source: str) -> AlgorithmMetadata:
    return AlgorithmMetadata(
        algorithm_id=algorithm_id, name_zh=name_zh, name_en=name_en, version="0.1",
        category=category, description_zh=description, description_en=description,
        purpose_zh="Day 9 多算法公平基准", purpose_en="Day 9 fair benchmark",
        provider="5GLOSVP platform (built-in)", learning_algorithm=False,
        capabilities=AlgorithmCapabilities(
            supports_discrete=False, supports_continuous=False, supports_integer=False,
            supports_categorical=True, supports_vector=False, supports_constraints=True,
            supports_multi_objective=False, supports_batch_suggestions=False,
            supports_iterative_feedback=True, supports_auto_configuration=True, max_parameters=1,
        ),
        hyperparameter_schema=[HyperparameterDefinition(
            id="seed", name_zh="随机种子", name_en="Seed", type=HyperparameterType.INTEGER,
            default=20260928, bounds=ParameterBounds(lower=0, upper=2_147_483_647),
            description_zh="可复现随机源", description_en="Reproducible random source",
        )] if algorithm_id == "random_search_v0_1" else [],
        supported_problem_types=[PROBLEM_TYPE], source=source, status=AlgorithmStatus.AVAILABLE,
        labels=["Day 9", "Comparable Benchmark", "Not Learning Algorithm"],
    )


class _AssociationAlgorithm(Algorithm):
    def __init__(self) -> None:
        self._queue: list[dict[str, ParameterValue]] = []
        self._stop: StopReason | None = None
        self._baseline_score: float | None = None
        self._found_improvement = False
        self._seen = 0

    def initialize(self, problem: AlgorithmProblem, hyperparameters: dict[str, HyperparameterValue], incumbents: list[EvaluationResult]) -> None:
        parameter = problem.parameter_space.parameters[0]
        baseline = problem.baseline_parameters.get(parameter.id)
        choices = list(parameter.choices or [])
        self._queue = [{parameter.id: choice} for choice in choices if choice != baseline]
        for incumbent in incumbents:
            if incumbent.objective is not None:
                self._baseline_score = incumbent.score()
        self._initialize_queue(hyperparameters)

    def _initialize_queue(self, hyperparameters: dict[str, HyperparameterValue]) -> None:
        return

    def suggest(self, max_suggestions: int) -> list[dict[str, ParameterValue]]:
        if self._stop is not None or not self._queue:
            if not self._queue and self._stop is None:
                self._stop = StopReason.COMPLETED
            return []
        return [self._queue.pop(0)]

    def observe(self, results: list[EvaluationResult]) -> None:
        self._seen += len(results)
        for result in results:
            score = result.score()
            feasible = all(c.satisfied for c in result.constraint_results)
            if feasible and score is not None and (self._baseline_score is None or score > self._baseline_score):
                self._found_improvement = True

    def should_stop(self) -> StopReason | None:
        if self._stop is not None:
            return self._stop
        return StopReason.CONVERGED if self._found_improvement else None

    def finalize(self) -> AlgorithmRecommendation:
        return AlgorithmRecommendation(parameters=None, note="Platform selects the best feasible candidate.")

    def state_metadata(self) -> dict[str, Any]:
        return {"remaining_candidates": len(self._queue), "evaluated_by_algorithm": self._seen,
                "found_feasible_improvement": self._found_improvement}


class AssociationBaselineAlgorithm(_AssociationAlgorithm):
    @classmethod
    def metadata(cls) -> AlgorithmMetadata:
        return _metadata("association_baseline_v0_1", "Day 8 用户关联基线", "Day 8 Association Baseline",
                         AlgorithmCategory.ENGINEERING_BASELINE,
                         "Frozen Day 8 best-link association used as the common incumbent.",
                         "src/algorithm_benchmark/algorithms.py")

    def initialize(self, problem: AlgorithmProblem, hyperparameters: dict[str, HyperparameterValue], incumbents: list[EvaluationResult]) -> None:
        self._queue = []
        self._stop = StopReason.COMPLETED


class RandomSearchAlgorithm(_AssociationAlgorithm):
    @classmethod
    def metadata(cls) -> AlgorithmMetadata:
        return _metadata("random_search_v0_1", "随机搜索", "Random Search", AlgorithmCategory.ENGINEERING_BASELINE,
                         "Seeded random single-UE reassociation search with shared feasibility evaluation.",
                         "src/algorithm_benchmark/algorithms.py")

    def _initialize_queue(self, hyperparameters: dict[str, HyperparameterValue]) -> None:
        random.Random(int(hyperparameters.get("seed", 20260928))).shuffle(self._queue)


class FirstImprovementLocalSearchAlgorithm(_AssociationAlgorithm):
    @classmethod
    def metadata(cls) -> AlgorithmMetadata:
        return _metadata("first_improvement_local_search_v0_1", "首次改进局部搜索", "First-Improvement Local Search",
                         AlgorithmCategory.CLASSICAL_OPTIMIZATION,
                         "Deterministic single-UE reassociation neighborhood in canonical UE/cell order.",
                         "src/algorithm_benchmark/algorithms.py")


RUNNABLE_ALGORITHMS = (AssociationBaselineAlgorithm, RandomSearchAlgorithm, FirstImprovementLocalSearchAlgorithm)
