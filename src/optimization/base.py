"""
优化接口 / Optimization interfaces.

依赖方向：Optimizer → CandidateEvaluator（接口）← OptimizationService → ExperimentService → SimulationBackend。
Optimizer 只看到参数与目标值，永远不知道仿真引擎的存在。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from .models import Direction, ObjectiveEvaluation, OptimizationCandidate
from .parameters import ParameterDefinition


@dataclass(frozen=True)
class ParameterInfo:
    id: str
    name_zh: str
    name_en: str
    unit: str


@dataclass(frozen=True)
class ObjectiveInputs:
    """
    目标函数输入：来自真实仿真的 Radio Map 数值层 + 候选参数。
    parameter_bounds: 参数在本次运行（搜索空间 ∪ 基线）中的 (min, max)，用于归一化。
    """

    layers: Mapping[str, np.ndarray]
    parameters: Mapping[str, float]
    parameter_bounds: Mapping[str, tuple[float, float]]


class Objective(ABC):
    """版本化目标函数。公式一旦发布不得在同一 id 下修改。"""

    id: str
    version: str
    direction: Direction
    name_zh: str
    name_en: str
    description_zh: str
    description_en: str
    formula: str
    required_layers: tuple[str, ...]
    default_params: Mapping[str, float]
    # 参数/阈值的来源说明，例如 "[A] Assumption — engineering demonstration parameter"
    assumptions: Mapping[str, str]

    @abstractmethod
    def evaluate(self, inputs: ObjectiveInputs, params: Mapping[str, float]) -> ObjectiveEvaluation: ...


class SearchProblem(Protocol):
    """
    Optimizer 看到的问题：候选参数、优化方向、已评价的现任解（例如基线）与确定性 tie-break。
    传播层（Day 4）与系统级（Day 6）问题都实现该协议，从而复用同一个 Optimizer。
    """

    @property
    def direction(self) -> Direction: ...

    def candidate_parameters(self) -> list[dict[str, float]]: ...

    def incumbents(self) -> list[OptimizationCandidate]:
        """参与最优选择但无需再次评价的候选（例如同一评价上下文中的基线）。"""
        ...

    def tie_break_key(self, candidate: OptimizationCandidate) -> tuple[float, ...]:
        """目标值相同时比较该键，较大者胜出。"""
        ...


class CandidateEvaluator(ABC):
    """评价一个候选配置（运行仿真并计算目标值），由 OptimizationService 实现。"""

    @abstractmethod
    def evaluate(self, parameters: Mapping[str, float], iteration: int) -> OptimizationCandidate:
        """返回已评价的候选；失败时抛出 CandidateEvaluationError。"""


@dataclass
class SearchResult:
    candidates: list[OptimizationCandidate]
    best_candidate_id: str


@dataclass(frozen=True)
class OptimizerInfo:
    id: str
    name_zh: str
    name_en: str
    category: str
    learning_algorithm: bool
    description_zh: str
    description_en: str
    supported_parameters: tuple[ParameterInfo, ...]
    # 演示搜索空间：工程演示值，不是标准值或现网配置
    recommended_parameter_space: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    recommended_parameter_space_source: str = "[A] Assumption — engineering demonstration search space"
    supported_problem_types: tuple[str, ...] = ("propagation",)
    # 算法超参数（与网络优化变量分开）；Grid Search 没有超参数
    hyperparameters: tuple[ParameterDefinition, ...] = ()


class Optimizer(ABC):
    @property
    @abstractmethod
    def info(self) -> OptimizerInfo: ...

    @property
    def id(self) -> str:
        return self.info.id

    @abstractmethod
    def optimize(self, problem: SearchProblem, evaluator: CandidateEvaluator) -> SearchResult: ...
