"""
Grid Search 的算法 SDK 实现 —— Engineering Baseline，不是学习算法。

一次建议全部离散候选（按定义顺序）；不使用评价反馈决定下一次参数。
搜索语义与 Day 4 / Day 6 GridSearchOptimizer 相同，因此沿用版本 0.2；最优选择由平台按冻结的 tie-break 规则完成。
"""

from __future__ import annotations

from typing import Any

from optimization.optimizers.grid_search import GRID_SEARCH_ID, GRID_SEARCH_VERSION
from optimization.parameters import ParameterValue

from ..sdk import (
    Algorithm,
    AlgorithmCapabilities,
    AlgorithmCategory,
    AlgorithmMetadata,
    AlgorithmProblem,
    AlgorithmRecommendation,
    AlgorithmStatus,
    EvaluationResult,
    HyperparameterValue,
    StopReason,
)

_METADATA = AlgorithmMetadata(
    algorithm_id=GRID_SEARCH_ID,
    name_zh="网格搜索",
    name_en="Grid Search",
    version=GRID_SEARCH_VERSION,
    category=AlgorithmCategory.ENGINEERING_BASELINE,
    description_zh="按定义顺序穷举离散候选值。作为所有科研算法的工程对照组，不代表项目最终学习优化算法。",
    description_en=(
        "Exhaustively evaluates every discrete candidate value in definition order. The engineering control "
        "group for research algorithms; not the project's learning optimization algorithm."
    ),
    purpose_zh="工程基线 / 对照组",
    purpose_en="Engineering baseline / control group",
    provider="5GLOSVP platform (built-in)",
    learning_algorithm=False,
    capabilities=AlgorithmCapabilities(
        supports_discrete=True,
        supports_continuous=False,
        supports_integer=False,
        supports_categorical=False,
        supports_vector=False,
        supports_constraints=False,
        supports_multi_objective=False,
        supports_batch_suggestions=True,
        supports_iterative_feedback=False,
        supports_auto_configuration=True,
        max_parameters=1,
    ),
    hyperparameter_schema=[],
    supported_problem_types=["propagation", "system"],
    source="src/algorithms/builtin/grid_search.py",
    status=AlgorithmStatus.AVAILABLE,
    labels=["Engineering Baseline", "工程基线", "Not Learning Algorithm"],
)


class GridSearchAlgorithm(Algorithm):
    def __init__(self) -> None:
        self._queue: list[dict[str, ParameterValue]] = []
        self._suggested = 0
        self._observed = 0
        self._total = 0

    @classmethod
    def metadata(cls) -> AlgorithmMetadata:
        return _METADATA

    def initialize(
        self,
        problem: AlgorithmProblem,
        hyperparameters: dict[str, HyperparameterValue],
        incumbents: list[EvaluationResult],
    ) -> None:
        (parameter,) = problem.parameter_space.parameters
        self._queue = [{parameter.id: v} for v in parameter.choices or []]
        self._total = len(self._queue)

    def suggest(self, max_suggestions: int) -> list[dict[str, ParameterValue]]:
        # 平台会拒绝超出预算的部分；这里一次交出全部剩余候选，便于审计预算执行
        batch, self._queue = self._queue, []
        self._suggested += len(batch)
        return batch

    def observe(self, results: list[EvaluationResult]) -> None:
        self._observed += len(results)

    def should_stop(self) -> StopReason | None:
        return StopReason.COMPLETED if self._total and self._observed >= self._total else None

    def finalize(self) -> AlgorithmRecommendation:
        return AlgorithmRecommendation(parameters=None,
                                       note="Grid Search does not recommend; the platform selects the best "
                                            "evaluated candidate with the frozen tie-break rule.")

    def state_metadata(self) -> dict[str, Any]:
        return {"total_candidates": self._total, "suggested": self._suggested, "observed": self._observed}
