"""
优化模型 / Optimization models.

Experiment = 一次仿真；OptimizationRun = 一次优化过程（基线 + 多个候选实验）。
本模块不依赖任何仿真引擎。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

OPTIMIZATION_ID_PATTERN = re.compile(r"^OPT-[0-9A-F]{8}$")
TX_POWER_PARAMETER = "tx_power_dbm"
BASELINE_CANDIDATE_ID = "BASELINE"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_optimization_id() -> str:
    return f"OPT-{uuid.uuid4().hex[:8].upper()}"


def candidate_id_for(iteration: int) -> str:
    return f"CAND-{iteration:03d}"


class OptimizationStatus(str, Enum):
    """CREATED → RUNNING → SUCCEEDED / FAILED"""

    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (OptimizationStatus.SUCCEEDED, OptimizationStatus.FAILED)


class Direction(str, Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class ParameterSpace(BaseModel):
    """
    搜索空间。Day 4 只支持发射功率（作用于场景中所有发射机）。
    候选顺序即定义顺序，不做随机打乱。
    """

    model_config = ConfigDict(extra="forbid")

    tx_power_dbm: list[float] = Field(min_length=1)

    @field_validator("tx_power_dbm")
    @classmethod
    def _unique(cls, v: list[float]) -> list[float]:
        if len(set(v)) != len(v):
            raise ValueError("tx_power_dbm candidates must be unique")
        return v

    def candidates(self) -> list[dict[str, float]]:
        return [{TX_POWER_PARAMETER: p} for p in self.tx_power_dbm]


class ObjectiveSpec(BaseModel):
    """本次运行使用的目标函数及其参数（版本化，用于跨运行比较）。"""

    id: str
    version: str
    direction: Direction
    params: dict[str, float] = Field(default_factory=dict)


class OptimizationProblem(BaseModel):
    scenario_id: str
    parameter_space: ParameterSpace
    objective: ObjectiveSpec
    baseline_parameters: dict[str, float]
    seed: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectiveEvaluation(BaseModel):
    objective_id: str
    objective_version: str
    value: float
    components: dict[str, float] = Field(default_factory=dict)


class CandidateStatus(str, Enum):
    EVALUATED = "evaluated"
    FAILED = "failed"


class CandidateError(BaseModel):
    code: str
    message: str


class OptimizationCandidate(BaseModel):
    """一个候选（或基线）配置及其可追溯的实验与目标值。"""

    candidate_id: str
    iteration: int = Field(description="0 = baseline；候选从 1 开始")
    parameters: dict[str, float]
    status: CandidateStatus
    experiment_id: str | None = None
    is_baseline: bool = False
    reused_baseline: bool = False
    objective: ObjectiveEvaluation | None = None
    runtime_seconds: float | None = None
    error: CandidateError | None = None


class OptimizationComparison(BaseModel):
    """
    优化目标改善（不是验收 KPI 改善）。
    relative_improvement_percent 在 |baseline| 过小时为 None，避免除零。
    """

    baseline_experiment_id: str
    optimized_experiment_id: str
    optimized_candidate_id: str
    baseline_parameters: dict[str, float]
    optimized_parameters: dict[str, float]
    baseline_objective: float
    optimized_objective: float
    absolute_improvement: float
    relative_improvement_percent: float | None


class OptimizationErrorCode(str, Enum):
    OPTIMIZATION_FAILED = "OPTIMIZATION_FAILED"


class OptimizationError(BaseModel):
    code: OptimizationErrorCode
    message: str
    type: str
    failed_candidate_id: str | None = None
    experiment_id: str | None = None


class OptimizationRuntime(BaseModel):
    baseline_seconds: float | None = None
    candidate_evaluation_seconds: float | None = None
    total_seconds: float | None = None


class OptimizationEvent(BaseModel):
    """时间线事件，时间戳为事件真实发生时间。"""

    event: str
    at: str
    candidate_id: str | None = None
    experiment_id: str | None = None


class OptimizationStatusTransition(BaseModel):
    status: OptimizationStatus
    at: str


class OptimizationRecord(BaseModel):
    optimization_id: str
    name: str
    status: OptimizationStatus
    scenario_id: str
    scenario_name_zh: str
    scenario_name_en: str
    simulation_backend: str
    optimizer_id: str
    objective: ObjectiveSpec
    parameter_space: ParameterSpace
    baseline_parameters: dict[str, float]
    seed: int
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    baseline: OptimizationCandidate | None = None
    candidates: list[OptimizationCandidate] = Field(default_factory=list)
    best_candidate_id: str | None = None
    comparison: OptimizationComparison | None = None
    runtime: OptimizationRuntime = Field(default_factory=OptimizationRuntime)
    provenance: dict[str, Any] = Field(default_factory=dict)
    error: OptimizationError | None = None
    events: list[OptimizationEvent] = Field(default_factory=list)
    status_history: list[OptimizationStatusTransition] = Field(default_factory=list)

    def transition(self, status: OptimizationStatus) -> None:
        self.status = status
        self.status_history.append(OptimizationStatusTransition(status=status, at=utc_now()))

    def add_event(self, event: str, candidate_id: str | None = None, experiment_id: str | None = None) -> None:
        self.events.append(
            OptimizationEvent(event=event, at=utc_now(), candidate_id=candidate_id, experiment_id=experiment_id)
        )
