"""系统级优化 API 模型 / System optimization API schemas."""

from __future__ import annotations

from typing import Any, Literal, assert_never
from urllib.parse import quote

from pydantic import BaseModel, Field, model_validator

from algorithms import AlgorithmCategory, AlgorithmMetadata, HyperparameterDefinition
from evidence import EvidenceDescriptor
from optimization.models import Direction
from optimization.optimizers.grid_search import GRID_SEARCH_ID
from optimization.parameters import ParameterDefinition
from system_optimization.models import BenchmarkProtocol, ParameterSpec, SystemOptimizationRecord
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
RESEARCH_DEMO_NOTICE_ZH = "Research Demo Optimizer 为算法接入验证算法，不是项目科研成果，也不是学习优化算法。"
RESEARCH_DEMO_NOTICE_EN = (
    "Research Demo Optimizer is an algorithm-integration validation algorithm; it is neither a project research "
    "deliverable nor a learning optimization algorithm."
)
RESEARCH_NOTICE_ZH = "科研算法结果仍为仿真验证结果，不构成验收结论。"
RESEARCH_NOTICE_EN = "Research algorithm results are simulation validation results, not acceptance conclusions."


def algorithm_notice(category: AlgorithmCategory) -> tuple[str, str]:
    match category:
        case AlgorithmCategory.ENGINEERING_BASELINE:
            return OPTIMIZER_NOTICE_ZH, OPTIMIZER_NOTICE_EN
        case AlgorithmCategory.RESEARCH_DEMO:
            return RESEARCH_DEMO_NOTICE_ZH, RESEARCH_DEMO_NOTICE_EN
        case AlgorithmCategory.RESEARCH | AlgorithmCategory.EXTERNAL:
            return RESEARCH_NOTICE_ZH, RESEARCH_NOTICE_EN
        case _:
            assert_never(category)


def record_category(r: SystemOptimizationRecord) -> AlgorithmCategory:
    if r.algorithm is not None:
        return r.algorithm.algorithm_category
    return AlgorithmCategory(r.provenance.get("optimizer_category", AlgorithmCategory.ENGINEERING_BASELINE.value))


class SystemOptimizerView(BaseModel):
    id: str
    name_zh: str
    name_en: str
    version: str
    category: AlgorithmCategory
    learning_algorithm: bool
    description_zh: str
    description_en: str
    supported_problem_types: list[str]
    hyperparameters: list[HyperparameterDefinition]

    @classmethod
    def from_metadata(cls, m: AlgorithmMetadata) -> SystemOptimizerView:
        return cls(id=m.algorithm_id, name_zh=m.name_zh, name_en=m.name_en, version=m.version, category=m.category,
                   learning_algorithm=m.learning_algorithm, description_zh=m.description_zh,
                   description_en=m.description_en, supported_problem_types=list(m.supported_problem_types),
                   hyperparameters=list(m.hyperparameter_schema))


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
    recommended_search_bounds: list[float]
    recommended_search_bounds_source: str

    @classmethod
    def from_parameter(cls, p: SystemParameter) -> SystemParameterView:
        return cls(definition=p.definition, affects_propagation=p.affects_propagation,
                   recommended_values=list(p.recommended_values),
                   recommended_values_source=p.recommended_values_source,
                   recommended_search_bounds=list(p.recommended_search_bounds),
                   recommended_search_bounds_source=p.recommended_search_bounds_source)


class SystemOptimizerList(BaseModel):
    items: list[SystemOptimizerView]


class SystemObjectiveList(BaseModel):
    items: list[SystemObjectiveView]


class SystemParameterList(BaseModel):
    items: list[SystemParameterView]


class ParameterSelection(BaseModel):
    """Day 6 兼容字段：一个参数 + Grid Search 候选值。"""

    id: str = Field(description="Optimization variable id, e.g. scheduler_beta")
    candidate_values: list[float] = Field(min_length=1, description="Grid Search candidate values")


class ParameterSpaceRequest(BaseModel):
    parameters: list[ParameterSpec] = Field(min_length=1)


class EvaluationBudgetRequest(BaseModel):
    max_evaluations: int = Field(description="Platform-enforced number of candidate evaluations (baseline excluded)")


class SystemOptimizationCreateRequest(BaseModel):
    problem_type: Literal["system"] = "system"
    name: str = Field(min_length=1, max_length=120)
    scenario_id: str
    algorithm_id: str | None = None
    algorithm_hyperparameters: dict[str, Any] = Field(default_factory=dict)
    parameter_space: ParameterSpaceRequest | None = None
    evaluation_budget: EvaluationBudgetRequest | None = None
    objective_id: str
    benchmark_protocol_id: str
    backend_id: str | None = None
    # Day 6 兼容字段
    optimizer_id: str | None = None
    parameter: ParameterSelection | None = None

    @model_validator(mode="after")
    def _check(self) -> SystemOptimizationCreateRequest:
        if (self.parameter is None) == (self.parameter_space is None):
            raise ValueError("provide exactly one of parameter_space or (legacy) parameter")
        if self.algorithm_id and self.optimizer_id and self.algorithm_id != self.optimizer_id:
            raise ValueError("algorithm_id and legacy optimizer_id disagree")
        return self

    def resolved_algorithm_id(self) -> str:
        return self.algorithm_id or self.optimizer_id or GRID_SEARCH_ID

    def resolved_parameter_space(self) -> list[ParameterSpec]:
        if self.parameter_space is not None:
            return list(self.parameter_space.parameters)
        assert self.parameter is not None
        return [ParameterSpec(id=self.parameter.id, type="discrete", choices=list(self.parameter.candidate_values))]


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
    evidence_descriptor: EvidenceDescriptor | None = None

    @classmethod
    def from_record(
        cls, r: SystemOptimizationRecord, evidence: EvidenceDescriptor | None = None
    ) -> SystemOptimizationResponse:
        links = [
            SystemOptimizationArtifactView(
                name=a.name, media_type=a.media_type, description=a.description,
                url=f"{API_PREFIX}/system-optimizations/{r.optimization_id}/artifacts/{quote(a.name)}",
            )
            for a in r.artifacts
        ]
        notice_zh, notice_en = algorithm_notice(record_category(r))
        return cls(**r.model_dump(), artifact_links=links, optimizer_notice_zh=notice_zh,
                   optimizer_notice_en=notice_en, evidence_descriptor=evidence)


class SystemOptimizationList(BaseModel):
    items: list[SystemOptimizationResponse]
    total: int
    limit: int
    offset: int


class BenchmarkProtocolList(BaseModel):
    items: list[BenchmarkProtocol]
