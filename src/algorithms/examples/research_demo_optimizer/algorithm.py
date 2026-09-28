"""
Research Demo Optimizer —— 自适应局部搜索（Adaptive Local Search），用于验证算法接入框架。

它不是项目科研成果，也不是学习优化算法（learning_algorithm = false）：
“会根据结果调整”不等于“学习优化”。它存在的唯一目的是证明 suggest → evaluate → observe 链路可用，
并作为科研团队接入算法的模板。

一维连续参数 x ∈ [lower, upper]：
    start   : 从基线（或区间中点）出发
    explore : 评价 x − step 与 x + step；若更优者严格优于 x → 移动并记住方向，进入 extend；否则 step *= shrink
    extend  : 沿同一方向再走一步 x + direction·step；更优 → 继续；否则 step *= shrink 并回到 explore
停止：step < min_step（converged）或完成 max_iterations 轮 suggest/observe（max_iterations）；
评价预算由平台执行（budget_exhausted）。
"""

from __future__ import annotations

import math
from typing import Any

from optimization.models import Direction
from optimization.parameters import ParameterBounds, ParameterType, ParameterValue

from ...sdk import (
    Algorithm,
    AlgorithmCapabilities,
    AlgorithmCategory,
    AlgorithmMetadata,
    AlgorithmProblem,
    AlgorithmRecommendation,
    AlgorithmStatus,
    CompatibilityCode,
    CompatibilityIssue,
    EvaluationResult,
    HyperparameterDefinition,
    HyperparameterType,
    HyperparameterValue,
    StopReason,
)

RESEARCH_DEMO_ID = "research_demo_optimizer"
RESEARCH_DEMO_VERSION = "0.1.0"
# 建议值统一舍入，避免 0.9 − 0.2 = 0.7000000000000001 这类浮点噪声进入缓存键与 trace
ROUND_DIGITS = 6

_METADATA = AlgorithmMetadata(
    algorithm_id=RESEARCH_DEMO_ID,
    name_zh="Research Demo Optimizer（自适应局部搜索）",
    name_en="Research Demo Optimizer (Adaptive Local Search)",
    version=RESEARCH_DEMO_VERSION,
    category=AlgorithmCategory.RESEARCH_DEMO,
    description_zh=(
        "一维连续参数的自适应局部搜索：从基线出发评价两侧邻点，朝更优方向移动，无改善时缩小步长。"
        "每一步都依据上一次目标值反馈决定下一个参数。用于验证算法接入框架，不是项目科研成果。"
    ),
    description_en=(
        "Adaptive local search over one continuous parameter: starts at the baseline, evaluates both "
        "neighbours, moves toward the better direction and shrinks the step when nothing improves. Each "
        "suggestion depends on the previous objective feedback. Validates the algorithm integration framework; "
        "not a project research deliverable."
    ),
    purpose_zh="算法接入验证（Integration Demo）",
    purpose_en="Algorithm Integration Validation",
    provider="5GLOSVP platform (integration template)",
    learning_algorithm=False,
    project_research_deliverable=False,
    acceptance_algorithm=False,
    capabilities=AlgorithmCapabilities(
        supports_discrete=False,
        supports_continuous=True,
        supports_integer=False,
        supports_categorical=False,
        supports_vector=False,
        supports_constraints=False,
        supports_multi_objective=False,
        supports_batch_suggestions=True,
        supports_iterative_feedback=True,
        supports_auto_configuration=True,
        max_parameters=1,
    ),
    hyperparameter_schema=[
        HyperparameterDefinition(
            id="initial_step", name_zh="初始步长", name_en="Initial Step", type=HyperparameterType.FLOAT,
            default=0.2, bounds=ParameterBounds(lower=0.0, upper=1.0, lower_inclusive=False),
            description_zh="首轮邻点距离（参数单位）", description_en="Neighbour distance of the first round",
        ),
        HyperparameterDefinition(
            id="min_step", name_zh="最小步长", name_en="Minimum Step", type=HyperparameterType.FLOAT,
            default=0.05, bounds=ParameterBounds(lower=0.0, upper=1.0, lower_inclusive=False),
            description_zh="步长缩小到低于该值时停止（converged）", description_en="Stop (converged) below this step",
        ),
        HyperparameterDefinition(
            id="shrink_factor", name_zh="步长缩小因子", name_en="Shrink Factor", type=HyperparameterType.FLOAT,
            default=0.5, bounds=ParameterBounds(lower=0.0, upper=1.0, lower_inclusive=False, upper_inclusive=False),
            description_zh="无改善时 step *= shrink_factor", description_en="step *= shrink_factor on no improvement",
        ),
        HyperparameterDefinition(
            id="max_iterations", name_zh="最大迭代轮数", name_en="Max Iterations", type=HyperparameterType.INTEGER,
            default=8, bounds=ParameterBounds(lower=1, upper=50),
            description_zh="suggest/observe 轮数上限（评价次数另由平台预算限制）",
            description_en="Upper bound of suggest/observe rounds (evaluations are capped by the platform budget)",
        ),
        HyperparameterDefinition(
            id="start_point", name_zh="起点", name_en="Start Point", type=HyperparameterType.CATEGORICAL,
            default="baseline", choices=["baseline", "center"],
            description_zh="baseline：从场景基线值出发；center：从搜索区间中点出发",
            description_en="baseline: scenario baseline value; center: midpoint of the search bounds",
        ),
    ],
    supported_problem_types=["system"],
    source="src/algorithms/examples/research_demo_optimizer/algorithm.py",
    status=AlgorithmStatus.EXPERIMENTAL,
    labels=["Integration Demo", "接入验证算法", "Not Project Research Deliverable"],
)


class ResearchDemoOptimizer(Algorithm):
    @classmethod
    def metadata(cls) -> AlgorithmMetadata:
        return _METADATA

    def validate_problem(
        self, problem: AlgorithmProblem, hyperparameters: dict[str, HyperparameterValue]
    ) -> list[CompatibilityIssue]:
        issues = []
        if float(hyperparameters["min_step"]) > float(hyperparameters["initial_step"]):
            issues.append(CompatibilityIssue(code=CompatibilityCode.INVALID_HYPERPARAMETER,
                                             message="min_step must be <= initial_step"))
        for p in problem.parameter_space.parameters:
            if p.type is ParameterType.CONTINUOUS and p.bounds is None:
                issues.append(CompatibilityIssue(code=CompatibilityCode.ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED,
                                                 message=f"continuous parameter '{p.id}' needs bounds",
                                                 parameter_id=p.id))
        return issues

    # ------------------------------------------------------------------

    def initialize(
        self,
        problem: AlgorithmProblem,
        hyperparameters: dict[str, HyperparameterValue],
        incumbents: list[EvaluationResult],
    ) -> None:
        (parameter,) = problem.parameter_space.parameters
        bounds = parameter.bounds
        assert bounds is not None
        self._pid = parameter.id
        self._min_step = float(hyperparameters["min_step"])
        self._shrink = float(hyperparameters["shrink_factor"])
        self._max_iterations = int(hyperparameters["max_iterations"])
        # 开区间端点不可取：向内收缩 min_step
        self._lo = bounds.lower if bounds.lower_inclusive else bounds.lower + self._min_step
        self._hi = bounds.upper if bounds.upper_inclusive else bounds.upper - self._min_step
        self._maximize = problem.objective_direction is Direction.MAXIMIZE
        self._memory: dict[float, float] = {}  # x → 方向归一化得分（失败 = -inf）
        for r in incumbents:
            self._remember(r)
        if hyperparameters["start_point"] == "center":
            self._x = self._clip((self._lo + self._hi) / 2)
        else:
            self._x = self._clip(float(problem.baseline_parameters[self._pid]))  # type: ignore[arg-type]
        self._step = float(hyperparameters["initial_step"])
        self._mode = "explore" if self._x in self._memory else "start"
        self._direction = 0
        self._round = 0
        self._stop: StopReason | None = None
        self._pending: list[float] = []
        self._last_decision = f"start at {self._x:g}"

    def suggest(self, max_suggestions: int) -> list[dict[str, ParameterValue]]:
        self._pending = self._next_points()
        return [{self._pid: x} for x in self._pending]

    def observe(self, results: list[EvaluationResult]) -> None:
        self._round += 1
        for r in results:
            self._remember(r)
        if all(x in self._memory for x in self._pending):
            self._decide()
        else:
            known = sum(x in self._memory for x in self._pending)
            self._last_decision = f"partial observation ({known}/{len(self._pending)} suggestions evaluated)"
        if self._stop is None and self._round >= self._max_iterations:
            self._stop = StopReason.MAX_ITERATIONS

    def should_stop(self) -> StopReason | None:
        return self._stop

    def finalize(self) -> AlgorithmRecommendation:
        return AlgorithmRecommendation(
            parameters={self._pid: self._x},
            note=f"incumbent after {self._round} round(s); step {self._step:g}; last decision: {self._last_decision}",
        )

    def state_metadata(self) -> dict[str, Any]:
        score = self._memory.get(self._x)
        objective = None if score is None or math.isinf(score) else (score if self._maximize else -score)
        return {
            "round": self._round,
            "mode": self._mode,
            "incumbent": self._x,
            "incumbent_objective": objective,
            "step": self._step,
            "direction": self._direction,
            "search_bounds": [self._lo, self._hi],
            "last_decision": self._last_decision,
            "stop": self._stop.value if self._stop else None,
        }

    # ------------------------------------------------------------------

    def _clip(self, x: float) -> float:
        return round(min(max(x, self._lo), self._hi), ROUND_DIGITS)

    def _remember(self, r: EvaluationResult) -> None:
        score = r.score()
        self._memory[self._round_raw(r.parameters[self._pid])] = -math.inf if score is None else score

    @staticmethod
    def _round_raw(value: ParameterValue) -> float:
        return round(float(value), ROUND_DIGITS)  # type: ignore[arg-type]

    def _neighbours(self) -> list[float]:
        points = [self._clip(self._x - self._step), self._clip(self._x + self._step)]
        return [p for i, p in enumerate(points) if p != self._x and p not in points[:i]]

    def _next_points(self) -> list[float]:
        """需要评价的下一批点；已知点直接用记忆做决策（不消耗评价）。"""
        while self._stop is None:
            if self._mode == "start":
                return [self._x]
            if self._mode == "explore":
                points = self._neighbours()
            else:
                target = self._clip(self._x + self._direction * self._step)
                points = [] if target == self._x else [target]
            unknown = [p for p in points if p not in self._memory]
            if unknown:
                return unknown
            self._pending = points
            self._decide()
        return []

    def _decide(self) -> None:
        fx = self._memory.get(self._x, -math.inf)
        if self._mode == "start":
            self._mode = "explore"
            self._last_decision = f"start point {self._x:g} evaluated"
            return
        scored = [(self._memory[p], -i, p) for i, p in enumerate(self._pending) if p in self._memory]
        best = max(scored) if scored else None
        if best is not None and best[0] > fx:
            new_x = best[2]
            self._direction = 1 if new_x > self._x else -1
            self._last_decision = f"move {self._x:g} → {new_x:g} (improved)"
            self._x = new_x
            self._mode = "extend"
            return
        old = self._step
        self._step = old * self._shrink
        self._mode = "explore"
        self._last_decision = f"no improvement around {self._x:g}: step {old:g} → {self._step:g}"
        if self._step < self._min_step:
            self._stop = StopReason.CONVERGED
