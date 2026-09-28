"""
Grid Search —— 工程基线优化器（Engineering Baseline Optimizer），不是学习算法。

按候选定义顺序逐个评价，在“现任解（例如基线）+ 已评价候选”中选择目标值最优者；
目标值完全相同时按问题定义的确定性 tie-break 选择（Day 4：较低发射功率；Day 6：基线值优先，其次候选顺序）。
候选评价失败（status = failed）不会中断搜索，失败者不参与选择。
"""

from __future__ import annotations

from ..base import CandidateEvaluator, Optimizer, OptimizerInfo, ParameterInfo, SearchProblem, SearchResult
from ..models import TX_POWER_PARAMETER, Direction, OptimizationCandidate

GRID_SEARCH_ID = "grid_search"
GRID_SEARCH_VERSION = "0.2"

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
    supported_problem_types=("propagation", "system"),
)


def select_best(candidates: list[OptimizationCandidate], problem: SearchProblem) -> OptimizationCandidate:
    scored = [c for c in candidates if c.objective is not None]
    if not scored:
        raise ValueError("No evaluated candidates to select from")
    sign = 1.0 if problem.direction is Direction.MAXIMIZE else -1.0

    def key(c: OptimizationCandidate) -> tuple[float, ...]:
        assert c.objective is not None
        return (sign * c.objective.value, *problem.tie_break_key(c))

    return max(scored, key=key)


class GridSearchOptimizer(Optimizer):
    @property
    def info(self) -> OptimizerInfo:
        return _INFO

    def optimize(self, problem: SearchProblem, evaluator: CandidateEvaluator) -> SearchResult:
        candidates = [
            evaluator.evaluate(parameters, iteration=i)
            for i, parameters in enumerate(problem.candidate_parameters(), start=1)
        ]
        best = select_best([*problem.incumbents(), *candidates], problem)
        return SearchResult(candidates=candidates, best_candidate_id=best.candidate_id)
