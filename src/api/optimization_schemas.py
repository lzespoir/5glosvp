"""
优化 API Schema / Optimization API schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from optimization import Objective, OptimizationRecord, Optimizer, OptimizationStatus, ParameterSpace
from optimization.models import (
    Direction,
    ObjectiveSpec,
    OptimizationCandidate,
    OptimizationComparison,
    OptimizationEvent,
    OptimizationRuntime,
    OptimizationStatusTransition,
)

from .schemas import ScenarioRef

# 相对基线的目标值变化：improved > 0，no_improvement = 0，worse < 0
ImprovementStatus = Literal["improved", "no_improvement", "worse"]
IMPROVEMENT_TOLERANCE = 1e-12


class OptimizerParameterView(BaseModel):
    id: str
    name_zh: str
    name_en: str
    unit: str


class OptimizerView(BaseModel):
    id: str
    name_zh: str
    name_en: str
    category: str = Field(description="engineering_baseline 等 / Optimizer category")
    learning_algorithm: bool = Field(description="是否为学习算法 / Whether this is a learning algorithm")
    available: bool = True
    description_zh: str
    description_en: str
    supported_parameters: list[OptimizerParameterView]
    recommended_parameter_space: dict[str, list[float]] = Field(
        description="演示搜索空间 / Demo search space (engineering assumption)"
    )
    recommended_parameter_space_source: str
    max_candidates: int

    @classmethod
    def from_optimizer(cls, optimizer: Optimizer, max_candidates: int) -> OptimizerView:
        i = optimizer.info
        return cls(
            id=i.id, name_zh=i.name_zh, name_en=i.name_en, category=i.category,
            learning_algorithm=i.learning_algorithm, description_zh=i.description_zh,
            description_en=i.description_en,
            supported_parameters=[
                OptimizerParameterView(id=p.id, name_zh=p.name_zh, name_en=p.name_en, unit=p.unit)
                for p in i.supported_parameters
            ],
            recommended_parameter_space={k: list(v) for k, v in i.recommended_parameter_space.items()},
            recommended_parameter_space_source=i.recommended_parameter_space_source,
            max_candidates=max_candidates,
        )


class OptimizerList(BaseModel):
    items: list[OptimizerView]


class ObjectiveView(BaseModel):
    id: str
    version: str
    name_zh: str
    name_en: str
    direction: Direction
    description_zh: str
    description_en: str
    formula: str
    required_metrics: list[str]
    default_params: dict[str, float]
    assumptions: dict[str, str]

    @classmethod
    def from_objective(cls, o: Objective) -> ObjectiveView:
        return cls(
            id=o.id, version=o.version, name_zh=o.name_zh, name_en=o.name_en, direction=o.direction,
            description_zh=o.description_zh, description_en=o.description_en, formula=o.formula,
            required_metrics=list(o.required_layers), default_params=dict(o.default_params),
            assumptions=dict(o.assumptions),
        )


class ObjectiveList(BaseModel):
    items: list[ObjectiveView]


class ObjectiveParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lambda_power: float | None = Field(
        default=None, ge=0.0, le=10.0, description="功率成本权重 λ [A] / Power cost weight"
    )


class OptimizationCreateRequest(BaseModel):
    """优化 ID 由服务端生成 / Optimization ID is server-generated."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    scenario_id: str = Field(min_length=1)
    optimizer_id: str = Field(min_length=1)
    objective_id: str = Field(min_length=1)
    parameter_space: ParameterSpace
    objective_params: ObjectiveParams | None = None


class OptimizerRef(BaseModel):
    id: str
    name_zh: str | None = None
    name_en: str | None = None
    category: str | None = None
    learning_algorithm: bool | None = None


class ObjectiveRef(ObjectiveSpec):
    name_zh: str | None = None
    name_en: str | None = None
    formula: str | None = None


class OptimizationErrorView(BaseModel):
    code: str
    message: str
    type: str
    failed_candidate_id: str | None = None
    experiment_id: str | None = None


class OptimizationResponse(BaseModel):
    optimization_id: str
    name: str
    status: OptimizationStatus
    scenario: ScenarioRef
    simulation_backend: str
    optimizer: OptimizerRef
    objective: ObjectiveRef
    parameter_space: ParameterSpace
    baseline_parameters: dict[str, float]
    seed: int
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    baseline: OptimizationCandidate | None = None
    candidates: list[OptimizationCandidate] = Field(default_factory=list)
    best_candidate: OptimizationCandidate | None = None
    comparison: OptimizationComparison | None = None
    improvement_status: ImprovementStatus | None = Field(
        default=None, description="优化目标相对基线的变化（不是验收 KPI）/ Objective change vs. baseline"
    )
    runtime: OptimizationRuntime
    provenance: dict[str, object]
    error: OptimizationErrorView | None = None
    events: list[OptimizationEvent] = Field(default_factory=list)
    status_history: list[OptimizationStatusTransition] = Field(default_factory=list)

    @classmethod
    def from_record(
        cls, r: OptimizationRecord, optimizer: Optimizer | None, objective: Objective | None
    ) -> OptimizationResponse:
        best = next((c for c in r.candidates if c.candidate_id == r.best_candidate_id), None)
        improvement: ImprovementStatus | None = None
        if r.comparison is not None:
            delta = r.comparison.absolute_improvement
            improvement = (
                "improved" if delta > IMPROVEMENT_TOLERANCE
                else "worse" if delta < -IMPROVEMENT_TOLERANCE
                else "no_improvement"
            )
        info = optimizer.info if optimizer else None
        return cls(
            optimization_id=r.optimization_id,
            name=r.name,
            status=r.status,
            scenario=ScenarioRef(scenario_id=r.scenario_id, name_zh=r.scenario_name_zh, name_en=r.scenario_name_en),
            simulation_backend=r.simulation_backend,
            optimizer=OptimizerRef(
                id=r.optimizer_id,
                name_zh=info.name_zh if info else None,
                name_en=info.name_en if info else None,
                category=info.category if info else None,
                learning_algorithm=info.learning_algorithm if info else None,
            ),
            objective=ObjectiveRef(
                **r.objective.model_dump(),
                name_zh=objective.name_zh if objective else None,
                name_en=objective.name_en if objective else None,
                formula=objective.formula if objective else None,
            ),
            parameter_space=r.parameter_space,
            baseline_parameters=r.baseline_parameters,
            seed=r.seed,
            created_at=r.created_at,
            started_at=r.started_at,
            finished_at=r.finished_at,
            baseline=r.baseline,
            candidates=r.candidates,
            best_candidate=best,
            comparison=r.comparison,
            improvement_status=improvement,
            runtime=r.runtime,
            provenance=r.provenance,
            error=OptimizationErrorView(**r.error.model_dump(mode="json")) if r.error else None,
            events=r.events,
            status_history=r.status_history,
        )


class OptimizationList(BaseModel):
    items: list[OptimizationResponse]
    total: int
    limit: int
    offset: int
