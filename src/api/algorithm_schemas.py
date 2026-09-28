"""算法中心 API 模型 / Algorithm catalog API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from algorithms import (
    ALGORITHM_SDK_VERSION,
    AlgorithmCapabilities,
    AlgorithmCategory,
    AlgorithmMetadata,
    AlgorithmStatus,
    CompatibilityReport,
)
from evidence import EvidenceDescriptor
from optimization.parameters import ParameterType
from system_optimization.models import ParameterSpec

from .system_optimization_schemas import EvaluationBudgetRequest, ParameterSpaceRequest, algorithm_notice

INTEGRATION_CONTRACT_DOC = "docs/algorithms/algorithm-integration-contract-v0.1.md"
INTEGRATION_GUIDE_DOC = "docs/algorithms/how-to-integrate-an-algorithm.md"


class AlgorithmSummary(BaseModel):
    id: str
    name_zh: str
    name_en: str
    version: str
    category: AlgorithmCategory
    learning_algorithm: bool
    project_research_deliverable: bool
    capabilities: AlgorithmCapabilities
    supported_parameter_types: list[ParameterType]
    supported_problem_types: list[str]
    auto_configuration: bool
    status: AlgorithmStatus
    sdk_version: str
    purpose_zh: str
    purpose_en: str
    labels: list[str]
    notice_zh: str
    notice_en: str

    @classmethod
    def from_metadata(cls, m: AlgorithmMetadata) -> AlgorithmSummary:
        zh, en = algorithm_notice(m.category)
        return cls(id=m.algorithm_id, name_zh=m.name_zh, name_en=m.name_en, version=m.version, category=m.category,
                   learning_algorithm=m.learning_algorithm, project_research_deliverable=m.project_research_deliverable,
                   capabilities=m.capabilities, supported_parameter_types=m.supported_parameter_types,
                   supported_problem_types=list(m.supported_problem_types), auto_configuration=m.auto_configuration,
                   status=m.status, sdk_version=m.sdk_version, purpose_zh=m.purpose_zh, purpose_en=m.purpose_en,
                   labels=list(m.labels), notice_zh=zh, notice_en=en)


class AlgorithmList(BaseModel):
    sdk_version: str = ALGORITHM_SDK_VERSION
    items: list[AlgorithmSummary]
    integration_contract: str = INTEGRATION_CONTRACT_DOC
    integration_guide: str = INTEGRATION_GUIDE_DOC


class AlgorithmEvidenceStatus(BaseModel):
    """该算法在平台中产生的运行（仿真证据，均不可作为验收证据）。"""

    optimization_runs: int
    succeeded_runs: int
    latest_optimization_id: str | None
    latest_succeeded_optimization_id: str | None
    acceptance_eligible_runs: int = 0


class AlgorithmDetail(BaseModel):
    metadata: AlgorithmMetadata
    notice_zh: str
    notice_en: str
    evidence: AlgorithmEvidenceStatus
    integration_contract: str = INTEGRATION_CONTRACT_DOC
    integration_guide: str = INTEGRATION_GUIDE_DOC


class AlgorithmValidateRequest(BaseModel):
    problem_type: Literal["system"] = "system"
    scenario_id: str | None = None
    objective_id: str
    parameter_space: ParameterSpaceRequest
    algorithm_hyperparameters: dict[str, Any] = Field(default_factory=dict)
    evaluation_budget: EvaluationBudgetRequest | None = None

    def specs(self) -> list[ParameterSpec]:
        return list(self.parameter_space.parameters)


class AlgorithmValidateResponse(CompatibilityReport):
    pass


class EvidenceList(BaseModel):
    items: list[EvidenceDescriptor]
    total: int
