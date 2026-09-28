"""系统级优化 API 模型 / System optimization API schemas."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field

from optimization.base import Optimizer
from optimization.models import Direction
from optimization.parameters import ParameterDefinition
from system_optimization.models import BenchmarkProtocol, SystemOptimizationRecord
from system_optimization.objectives import SystemObjective
from system_optimization.parameters import SystemParameter

from .schemas import API_PREFIX

SCIENTIFIC_BOUNDARY_ZH = "当前结果来自系统级仿真优化验证，不是华为实测网络优化结果。"
SCIENTIFIC_BOUNDARY_EN = (
    "Results come from system-level simulation optimization validation, not from Huawei measured network optimization."
)
OPTIMIZER_NOTICE_ZH = "Grid Search 为工程基线优化器，不属于项目学习优化算法。"
OPTIMIZER_NOTICE_EN = (
    "Grid Search is an engineering baseline optimizer, not the project's learning optimization algorithm."
)


class SystemOptimizerView(BaseModel):
    id: str
    name_zh: str
    name_en: str
    category: str
    learning_algorithm: bool
    description_zh: str
    description_en: str
    supported_problem_types: list[str]
    hyperparameters: list[ParameterDefinition]

    @classmethod
    def from_optimizer(cls, o: Optimizer) -> SystemOptimizerView:
        i = o.info
        return cls(id=i.id, name_zh=i.name_zh, name_en=i.name_en, category=i.category,
                   learning_algorithm=i.learning_algorithm, description_zh=i.description_zh,
                   description_en=i.description_en, supported_problem_types=list(i.supported_problem_types),
                   hyperparameters=list(i.hyperparameters))


class SystemObjectiveView(BaseModel):
    id: str
    version: str
    direction: Direction
    name_zh: str
    name_en: str
    input_kpis: list[str]
    formula: str
    unit: str
    required_experiment_type: str
    required_capabilities: list[str]
    description_zh: str
    description_en: str
    assumptions: list[str]
    limitations: list[str]
    acceptance_kpi: bool
    measured_data: bool
    huawei_data: bool
    document: str

    @classmethod
    def from_objective(cls, o: SystemObjective) -> SystemObjectiveView:
        i = o.info
        return cls(id=i.id, version=i.version, direction=i.direction, name_zh=i.name_zh, name_en=i.name_en,
                   input_kpis=list(i.input_kpis), formula=i.formula, unit=i.unit,
                   required_experiment_type=i.required_experiment_type,
                   required_capabilities=list(i.required_capabilities), description_zh=i.description_zh,
                   description_en=i.description_en, assumptions=list(i.assumptions),
                   limitations=list(i.limitations), acceptance_kpi=i.acceptance_kpi, measured_data=i.measured_data,
                   huawei_data=i.huawei_data, document=i.document)


class SystemParameterView(BaseModel):
    definition: ParameterDefinition
    affects_propagation: bool
    recommended_values: list[float]
    recommended_values_source: str

    @classmethod
    def from_parameter(cls, p: SystemParameter) -> SystemParameterView:
        return cls(definition=p.definition, affects_propagation=p.affects_propagation,
                   recommended_values=list(p.recommended_values),
                   recommended_values_source=p.recommended_values_source)


class SystemOptimizerList(BaseModel):
    items: list[SystemOptimizerView]


class SystemObjectiveList(BaseModel):
    items: list[SystemObjectiveView]


class SystemParameterList(BaseModel):
    items: list[SystemParameterView]


class ParameterSelection(BaseModel):
    id: str = Field(description="Optimization variable id, e.g. scheduler_beta")
    candidate_values: list[float] = Field(min_length=1, description="Grid Search candidate values")


class SystemOptimizationCreateRequest(BaseModel):
    problem_type: Literal["system"] = "system"
    name: str = Field(min_length=1, max_length=120)
    scenario_id: str
    optimizer_id: str = "grid_search"
    objective_id: str
    parameter: ParameterSelection
    benchmark_protocol_id: str
    backend_id: str | None = None


class SystemOptimizationArtifactView(BaseModel):
    name: str
    media_type: str
    description: str
    url: str


class SystemOptimizationResponse(SystemOptimizationRecord):
    artifact_links: list[SystemOptimizationArtifactView] = Field(default_factory=list)
    scientific_boundary_zh: str = SCIENTIFIC_BOUNDARY_ZH
    scientific_boundary_en: str = SCIENTIFIC_BOUNDARY_EN
    optimizer_notice_zh: str = OPTIMIZER_NOTICE_ZH
    optimizer_notice_en: str = OPTIMIZER_NOTICE_EN

    @classmethod
    def from_record(cls, r: SystemOptimizationRecord) -> SystemOptimizationResponse:
        links = [
            SystemOptimizationArtifactView(
                name=a.name, media_type=a.media_type, description=a.description,
                url=f"{API_PREFIX}/system-optimizations/{r.optimization_id}/artifacts/{quote(a.name)}",
            )
            for a in r.artifacts
        ]
        return cls(**r.model_dump(), artifact_links=links)


class SystemOptimizationList(BaseModel):
    items: list[SystemOptimizationResponse]
    total: int
    limit: int
    offset: int


class BenchmarkProtocolList(BaseModel):
    items: list[BenchmarkProtocol]
