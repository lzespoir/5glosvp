"""
系统级仿真 API Schema / System-level simulation API schemas.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, Field

from evaluation.kpi import KpiDefinition, KpiResult
from system_simulation import (
    MODEL_LABELS,
    SystemBackendStatus,
    SystemExperimentRecord,
    SystemExperimentStatus,
    SystemScenario,
    SystemSimulationResult,
)
from system_simulation.base import SystemBackendDescriptor
from system_simulation.models import ArtifactRef

from .schemas import API_PREFIX

SCIENTIFIC_BOUNDARY_ZH = "当前结果来自系统级仿真，不是华为实测网络数据。"
SCIENTIFIC_BOUNDARY_EN = "Results come from system-level simulation, not Huawei measured network data."


class SystemBackendView(BaseModel):
    id: str
    name_zh: str
    name_en: str
    category: str = Field(description="propagation | system")
    available: bool
    version: str | None = None
    capabilities: list[str]
    model_type: str = Field(description="sionna_sys | engineering_approximation | test_fixture")
    model_label: str = Field(description="结果标识 / Result label, e.g. 'Sionna Simulation Generated'")
    source_type: str
    provider: str | None = None
    compute_device: str | None = None
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def from_status(cls, status: SystemBackendStatus) -> SystemBackendView:
        d, h = status.descriptor, status.health
        available = bool(h.get("available"))
        return cls(
            id=d.id, name_zh=d.name_zh, name_en=d.name_en, category=d.category, available=available,
            version=h.get("version"), capabilities=[c.value for c in d.capabilities],
            model_type=d.model_type.value, model_label=MODEL_LABELS[d.model_type], source_type=d.source_type,
            provider=d.provider, compute_device=h.get("sys_device"),
            reason=None if available else ("; ".join(h.get("errors") or []) or "unavailable"),
            warnings=list(h.get("warnings") or []),
        )


class SystemBackendList(BaseModel):
    items: list[SystemBackendView]


class SystemScenarioSummary(BaseModel):
    scenario_id: str
    name_zh: str
    name_en: str
    description: str | None = None
    backend: str
    scene: str
    bs_count: int
    cell_count: int
    ue_count: int
    carrier_frequency_hz: float
    bandwidth_hz: float
    traffic_model: str
    seed: int
    ue_placement: str = Field(description="generator:<type> | explicit")
    data_source: str = Field(default="[A] 场景参数为假设 / Scenario parameters are assumptions")

    @classmethod
    def from_scenario(cls, s: SystemScenario) -> SystemScenarioSummary:
        cell = s.cells[0]
        return cls(
            scenario_id=s.scenario_id, name_zh=s.name_zh, name_en=s.name_en, description=s.description,
            backend=s.backend, scene=s.scene, bs_count=len(s.base_stations), cell_count=len(s.cells),
            ue_count=s.ue_count, carrier_frequency_hz=cell.carrier_frequency_hz, bandwidth_hz=cell.bandwidth_hz,
            traffic_model=s.traffic.type.value, seed=s.seed,
            ue_placement=f"generator:{s.ue_generator.type.value}" if s.ue_generator else "explicit",
        )


class SystemScenarioList(BaseModel):
    items: list[SystemScenarioSummary]


class SystemScenarioDetail(SystemScenarioSummary):
    scenario: SystemScenario

    @classmethod
    def from_scenario(cls, s: SystemScenario) -> SystemScenarioDetail:
        return cls(**SystemScenarioSummary.from_scenario(s).model_dump(), scenario=s)


class SystemExperimentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scenario_id: str = Field(min_length=1)
    backend_id: str | None = Field(default=None, description="省略时使用场景默认后端 / Defaults to scenario backend")


class SystemBackendRef(BaseModel):
    id: str
    version: str | None = None
    model_type: str | None = None
    model_label: str | None = None
    source_type: str | None = None


class SystemScenarioRef(BaseModel):
    scenario_id: str
    name_zh: str
    name_en: str


class SystemArtifactView(BaseModel):
    name: str
    type: str
    media_type: str
    description: str | None = None
    url: str

    @classmethod
    def from_ref(cls, experiment_id: str, a: ArtifactRef) -> SystemArtifactView:
        return cls(name=a.name, type=a.type, media_type=a.media_type, description=a.description,
                   url=f"{API_PREFIX}/system-experiments/{experiment_id}/artifacts/{quote(a.name)}")


class SystemErrorView(BaseModel):
    code: str
    message: str
    type: str


class SystemStatusTransitionView(BaseModel):
    status: SystemExperimentStatus
    at: str


class SystemExperimentResponse(BaseModel):
    experiment_id: str
    name: str
    experiment_type: str = Field(description="propagation | system")
    purpose: str
    status: SystemExperimentStatus
    scenario: SystemScenarioRef
    backend: SystemBackendRef
    seed: int
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: SystemSimulationResult | None = None
    kpis: list[KpiResult] = Field(default_factory=list)
    artifacts: list[SystemArtifactView] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    scientific_boundary_zh: str = SCIENTIFIC_BOUNDARY_ZH
    scientific_boundary_en: str = SCIENTIFIC_BOUNDARY_EN
    error: SystemErrorView | None = None
    warnings: list[str] = Field(default_factory=list)
    status_history: list[SystemStatusTransitionView] = Field(default_factory=list)

    @classmethod
    def from_record(cls, r: SystemExperimentRecord,
                    descriptor: SystemBackendDescriptor | None) -> SystemExperimentResponse:
        return cls(
            experiment_id=r.experiment_id, name=r.name, experiment_type=r.experiment_type.value,
            purpose=r.purpose, status=r.status,
            scenario=SystemScenarioRef(scenario_id=r.scenario_id, name_zh=r.scenario_name_zh,
                                       name_en=r.scenario_name_en),
            backend=SystemBackendRef(
                id=r.backend, version=r.backend_version,
                model_type=descriptor.model_type.value if descriptor else r.provenance.get("model_type"),
                model_label=MODEL_LABELS[descriptor.model_type] if descriptor else r.provenance.get("model_label"),
                source_type=descriptor.source_type if descriptor else r.provenance.get("source_type"),
            ),
            seed=r.seed,
            created_at=r.created_at.isoformat(),
            started_at=r.started_at.isoformat() if r.started_at else None,
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
            result=r.result, kpis=r.kpis,
            artifacts=[SystemArtifactView.from_ref(r.experiment_id, a) for a in r.artifacts],
            provenance=r.provenance,
            error=SystemErrorView(code=r.error.code.value, message=r.error.message, type=r.error.type)
            if r.error else None,
            warnings=r.warnings,
            status_history=[SystemStatusTransitionView(status=t.status, at=t.at.isoformat())
                            for t in r.status_history],
        )


class SystemExperimentList(BaseModel):
    items: list[SystemExperimentResponse]
    total: int
    limit: int
    offset: int


class KpiDefinitionList(BaseModel):
    items: list[KpiDefinition]
