"""
算法 SDK / Algorithm SDK (ALGORITHM_SDK_VERSION 0.1).

平台拥有场景、参数空间、评价协议、仿真、KPI、目标函数、实验与证据；算法只拥有候选生成 / 搜索逻辑。

生命周期（由平台 AlgorithmDriver 驱动，算法不能自行调用仿真）：

    algorithm.validate_problem(problem, hyperparameters)
    algorithm.initialize(problem, hyperparameters, incumbents)
    while algorithm.should_stop() is None and 预算未用尽:
        suggestions = algorithm.suggest(max_suggestions)
        results = platform.evaluate(suggestions)      # 同一冻结评价上下文
        algorithm.observe(results)
    recommendation = algorithm.finalize()

算法只看到参数、目标值反馈、次要指标、约束结果与必要元数据；
看不到 Sionna、实验仓库、NPZ 路径或 KPI 实现。
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from optimization.models import Direction
from optimization.parameters import ParameterBounds, ParameterType, ParameterValue

from .parameter_space import ParameterSpace

ALGORITHM_SDK_VERSION = "0.1"

HyperparameterValue = Union[bool, int, float, str]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class AlgorithmCategory(str, Enum):
    ENGINEERING_BASELINE = "engineering_baseline"
    RESEARCH_DEMO = "research_demo"
    RESEARCH = "research"
    EXTERNAL = "external"


class AlgorithmStatus(str, Enum):
    AVAILABLE = "available"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class AlgorithmCapabilities(_Strict):
    """能力声明：只写真实实现的能力，不为“看起来高级”而全部置 true。"""

    supports_discrete: bool
    supports_continuous: bool
    supports_integer: bool
    supports_categorical: bool
    supports_vector: bool
    supports_constraints: bool
    supports_multi_objective: bool
    supports_batch_suggestions: bool
    supports_iterative_feedback: bool
    supports_auto_configuration: bool
    max_parameters: int | None = Field(default=None, ge=1, description="None = no declared limit")

    def supported_parameter_types(self) -> list[ParameterType]:
        flags = {
            ParameterType.CONTINUOUS: self.supports_continuous,
            ParameterType.INTEGER: self.supports_integer,
            ParameterType.DISCRETE: self.supports_discrete,
            ParameterType.CATEGORICAL: self.supports_categorical,
            ParameterType.VECTOR: self.supports_vector,
        }
        return [t for t, ok in flags.items() if ok]


class HyperparameterType(str, Enum):
    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"


class HyperparameterDefinition(_Strict):
    """算法超参数（与网络优化变量完全分离）。"""

    id: str
    name_zh: str
    name_en: str
    type: HyperparameterType
    default: HyperparameterValue
    bounds: ParameterBounds | None = None
    choices: list[HyperparameterValue] | None = None
    unit: str = "1"
    description_zh: str = ""
    description_en: str = ""

    @model_validator(mode="after")
    def _check(self) -> HyperparameterDefinition:
        if self.type is HyperparameterType.CATEGORICAL and not self.choices:
            raise ValueError(f"categorical hyperparameter '{self.id}' requires choices")
        self.default = self.validate_value(self.default)
        return self

    def validate_value(self, value: Any) -> HyperparameterValue:
        t = self.type
        if t is HyperparameterType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValueError(f"{self.id}: expected a boolean, got {value!r}")
            return value
        if t is HyperparameterType.CATEGORICAL:
            if value not in (self.choices or []):
                raise ValueError(f"{self.id}: {value!r} is not one of {self.choices}")
            return value
        if isinstance(value, (bool, str)) or not isinstance(value, (int, float)):
            raise ValueError(f"{self.id}: expected a number, got {value!r}")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{self.id}: value must be finite")
        if self.bounds is not None and not self.bounds.contains(number):
            raise ValueError(f"{self.id}: {number:g} outside bounds {self.bounds.describe()}")
        if t is HyperparameterType.INTEGER:
            if not number.is_integer():
                raise ValueError(f"{self.id}: {value!r} is not an integer")
            return int(number)
        return number


class AlgorithmMetadata(_Strict):
    algorithm_id: str
    name_zh: str
    name_en: str
    version: str
    category: AlgorithmCategory
    description_zh: str
    description_en: str
    purpose_zh: str
    purpose_en: str
    provider: str
    learning_algorithm: bool
    project_research_deliverable: bool = False
    acceptance_algorithm: bool = False
    capabilities: AlgorithmCapabilities
    hyperparameter_schema: list[HyperparameterDefinition] = Field(default_factory=list)
    supported_problem_types: list[str]
    source: str
    status: AlgorithmStatus
    sdk_version: str = ALGORITHM_SDK_VERSION
    labels: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def supported_parameter_types(self) -> list[ParameterType]:
        return self.capabilities.supported_parameter_types()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def auto_configuration(self) -> bool:
        return self.capabilities.supports_auto_configuration


# ---------------------------------------------------------------------------
# Problem / evaluation interface
# ---------------------------------------------------------------------------


class AlgorithmProblem(_Strict):
    """算法看到的优化问题（不含任何仿真器 / 实验仓库对象）。"""

    problem_type: str
    parameter_space: ParameterSpace
    objective_id: str
    objective_direction: Direction
    objective_count: int = Field(default=1, ge=1)
    baseline_parameters: dict[str, ParameterValue]
    max_evaluations: int = Field(description="validated by check_compatibility (INVALID_EVALUATION_BUDGET)")


class EvaluationStatus(str, Enum):
    EVALUATED = "evaluated"
    FAILED = "failed"


class ConstraintResult(_Strict):
    id: str
    satisfied: bool
    value: float | None = None
    detail: str = ""


class EvaluationResult(_Strict):
    """平台返回给算法的规范化评价结果。"""

    candidate_id: str
    parameters: dict[str, ParameterValue]
    objective: float | None
    objective_direction: Direction
    secondary_metrics: dict[str, float] = Field(default_factory=dict)
    constraint_results: list[ConstraintResult] = Field(default_factory=list)
    status: EvaluationStatus
    runtime_seconds: float | None = None
    cache_hit: bool = False

    def score(self) -> float | None:
        """方向归一化的目标值：越大越好；失败时为 None。"""
        if self.status is not EvaluationStatus.EVALUATED or self.objective is None:
            return None
        return self.objective if self.objective_direction is Direction.MAXIMIZE else -self.objective


class StopReason(str, Enum):
    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    CONVERGED = "converged"
    NO_IMPROVEMENT = "no_improvement"
    BUDGET_EXHAUSTED = "budget_exhausted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AlgorithmRecommendation(_Strict):
    parameters: dict[str, ParameterValue] | None
    note: str = ""


class CompatibilityCode(str, Enum):
    ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED = "ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED"
    ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED = "ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED"
    ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED = "ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED"
    ALGORITHM_CONSTRAINTS_NOT_SUPPORTED = "ALGORITHM_CONSTRAINTS_NOT_SUPPORTED"
    ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED = "ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED"
    INVALID_HYPERPARAMETER = "INVALID_HYPERPARAMETER"
    INVALID_EVALUATION_BUDGET = "INVALID_EVALUATION_BUDGET"


class CompatibilityIssue(_Strict):
    code: CompatibilityCode
    message: str
    parameter_id: str | None = None


# ---------------------------------------------------------------------------
# Algorithm lifecycle
# ---------------------------------------------------------------------------


class Algorithm(ABC):
    """一个算法实例对应一次优化运行（有状态）。"""

    @classmethod
    @abstractmethod
    def metadata(cls) -> AlgorithmMetadata: ...

    def validate_problem(
        self, problem: AlgorithmProblem, hyperparameters: dict[str, HyperparameterValue]
    ) -> list[CompatibilityIssue]:
        """能力声明之外的算法特定检查（例如超参数之间的关系）；默认无。"""
        return []

    @abstractmethod
    def initialize(
        self,
        problem: AlgorithmProblem,
        hyperparameters: dict[str, HyperparameterValue],
        incumbents: list[EvaluationResult],
    ) -> None:
        """incumbents：平台已在同一上下文中评价的现任解（例如基线）。"""

    @abstractmethod
    def suggest(self, max_suggestions: int) -> list[dict[str, ParameterValue]]:
        """返回下一批候选（≤ max_suggestions）；空列表表示没有更多建议。"""

    @abstractmethod
    def observe(self, results: list[EvaluationResult]) -> None: ...

    @abstractmethod
    def should_stop(self) -> StopReason | None: ...

    @abstractmethod
    def finalize(self) -> AlgorithmRecommendation: ...

    def state_metadata(self) -> dict[str, Any]:
        """可审计的 JSON 状态快照（写入 algorithm trace）；不得包含二进制 / pickle。"""
        return {}
