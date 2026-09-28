"""
Grid Search —— 工程基线优化器（Engineering Baseline Optimizer），不是学习算法。

按搜索空间定义顺序逐个评价候选，选择目标值最优者；目标值完全相同时选择较低发射功率。
"""

from __future__ import annotations

from ..base import CandidateEvaluator, Optimizer, OptimizerInfo, ParameterInfo, SearchResult
from ..models import TX_POWER_PARAMETER, Direction, OptimizationCandidate, OptimizationProblem

GRID_SEARCH_ID = "grid_search"

_INFO = OptimizerInfo(
    id=GRID_SEARCH_ID,
    name_zh="网格搜索",
    name_en="Grid Search",
    category="engineering_baseline",
    learning_algorithm=False,
    description_zh="按顺序穷举搜索空间中的每个候选配置。用于验证平台优化闭环，不代表项目最终学习优化算法。",
    description_en=(
        "Exhaustively evaluates every candidate in definition order. Validates the optimization loop; "
        "it is not the project's learning optimization algorithm."
    ),
    supported_parameters=(ParameterInfo(TX_POWER_PARAMETER, "发射功率", "TX Power", "dBm"),),
    recommended_parameter_space={TX_POWER_PARAMETER: (38.0, 40.0, 42.0, 44.0, 46.0)},
)


def select_best(candidates: list[OptimizationCandidate], direction: Direction) -> OptimizationCandidate:
    """目标值最优者；完全相同时选择较低发射功率（确定性 tie-breaker）。"""
    scored = [c for c in candidates if c.objective is not None]
    if not scored:
        raise ValueError("No evaluated candidates to select from")
    sign = 1.0 if direction is Direction.MAXIMIZE else -1.0

    def key(c: OptimizationCandidate) -> tuple[float, float]:
        assert c.objective is not None
        return sign * c.objective.value, -c.parameters.get(TX_POWER_PARAMETER, 0.0)

    return max(scored, key=key)


class GridSearchOptimizer(Optimizer):
    @property
    def info(self) -> OptimizerInfo:
        return _INFO

    def optimize(self, problem: OptimizationProblem, evaluator: CandidateEvaluator) -> SearchResult:
        candidates = [
            evaluator.evaluate(parameters, iteration=i)
            for i, parameters in enumerate(problem.parameter_space.candidates(), start=1)
        ]
        best = select_best(candidates, problem.objective.direction)
        return SearchResult(candidates=candidates, best_candidate_id=best.candidate_id)
