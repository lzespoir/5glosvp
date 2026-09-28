"""
API Schema（HTTP 契约）/ API schemas (HTTP contract).

API 只通过这些 Schema 对外暴露数据，不直接返回内部 Python 对象。
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

from experiments import BackendStatus, ExperimentRecord, ExperimentStatus
from simulation import ScenarioConfig
from simulation.models import Artifact

API_PREFIX = "/api/v1"

# source_type → (中文, English)；当前平台只有仿真生成数据，禁止标为真实/实测数据
DATA_TYPE_LABELS: dict[str, tuple[str, str]] = {
    "simulation": ("仿真生成", "Simulation Generated"),
    "test_fixture": ("软件测试夹具（非仿真结果）", "Software Test Fixture (not a simulation result)"),
}

_ARTIFACT_TYPES = {
    "image/png": "image",
    "application/json": "json",
    "application/yaml": "yaml",
    "text/plain": "text",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorBody(BaseModel):
    code: str = Field(description="错误码 / Error code, e.g. SCENARIO_NOT_FOUND")
    message_zh: str = Field(description="中文错误信息")
    message_en: str = Field(description="English error message")
    detail: dict[str, Any] = Field(default_factory=dict, description="附加信息 / Extra detail")


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---------------------------------------------------------------------------
# Health / Backends
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = Field(description="服务状态 / Service status")
    service: str
    name_zh: str
    name_en: str
    version: str


class BackendInfo(BaseModel):
    id: str = Field(description="后端 ID / Backend id")
    name_zh: str
    name_en: str
    available: bool = Field(description="当前环境是否可运行 / Whether runnable in this environment")
    version: str | None = None
    capabilities: list[str] = Field(default_factory=list, description="支持的能力 / Capabilities")
    reason: str | None = Field(default=None, description="不可用原因 / Reason when unavailable")

    @classmethod
    def from_status(cls, status: BackendStatus) -> BackendInfo:
        d, h = status.descriptor, status.health
        available = bool(h.get("available"))
        return cls(
            id=d.id, name_zh=d.name_zh, name_en=d.name_en, available=available,
            version=h.get("version"), capabilities=list(d.capabilities),
            reason=None if available else ("; ".join(h.get("errors") or []) or "unavailable"),
        )


class BackendList(BaseModel):
    items: list[BackendInfo]


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


class ScenarioSummary(BaseModel):
    scenario_id: str
    name_zh: str
    name_en: str
    backend: str

    @classmethod
    def from_config(cls, c: ScenarioConfig) -> ScenarioSummary:
        return cls(scenario_id=c.scenario_id, name_zh=c.name_zh, name_en=c.name_en, backend=c.backend)


class ScenarioList(BaseModel):
    items: list[ScenarioSummary]


class TransmitterView(BaseModel):
    id: str
    position: list[float] = Field(description="位置 (x, y, z) [m] / Position")
    orientation: list[float] | None = Field(default=None, description="朝向欧拉角 [rad] / Orientation")
    power_dbm: float | None = Field(default=None, description="发射功率 [dBm] / Transmit power")


class MeasurementAreaView(BaseModel):
    center: list[float]
    size: list[float]
    orientation: list[float]


class RadioMapView(BaseModel):
    metric: str = Field(description="主指标 / Primary metric: rss | path_gain | sinr")
    cell_size: list[float] = Field(description="格点尺寸 [m] / Cell size")
    measurement_area: MeasurementAreaView | None = None
    max_depth: int
    samples_per_tx: int


class ScenarioDetail(ScenarioSummary):
    scene_name: str = Field(description="场景名 / Scene name")
    frequency_hz: float = Field(description="载频 [Hz] / Carrier frequency")
    bandwidth_hz: float = Field(description="带宽 [Hz] / Bandwidth")
    random_seed: int
    transmitters: list[TransmitterView]
    radio_map: RadioMapView

    @classmethod
    def from_config(cls, c: ScenarioConfig) -> ScenarioDetail:
        data = c.model_dump(mode="json")
        return cls.model_validate({k: data[k] for k in cls.model_fields})


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


class ExperimentCreateRequest(BaseModel):
    """实验 ID 由服务端生成，客户端不得指定 / Experiment ID is server-generated."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200, description="实验名称 / Experiment name")
    scenario_id: str = Field(min_length=1, description="场景 ID / Scenario id")


class ScenarioRef(BaseModel):
    scenario_id: str
    name_zh: str
    name_en: str


class BackendRef(BaseModel):
    id: str
    version: str | None = None


class RuntimeView(BaseModel):
    simulation_seconds: float | None = Field(default=None, description="仿真计算耗时 / Simulation time")
    artifact_export_seconds: float | None = Field(default=None, description="产物导出耗时 / Export time")
    total_seconds: float | None = Field(default=None, description="完整实验耗时 / Total time")


class ArtifactView(BaseModel):
    name: str
    type: str = Field(description="image | json | yaml | text | binary")
    media_type: str
    description: str | None = None
    url: str = Field(description="下载/查看地址 / Download URL")

    @classmethod
    def from_artifact(cls, experiment_id: str, a: Artifact) -> ArtifactView:
        return cls(
            name=a.name,
            type=_ARTIFACT_TYPES.get(a.media_type, "binary"),
            media_type=a.media_type,
            description=a.description,
            url=f"{API_PREFIX}/experiments/{experiment_id}/artifacts/{quote(a.name)}",
        )


class ArtifactList(BaseModel):
    items: list[ArtifactView]


class ProvenanceView(BaseModel):
    source_type: str | None = Field(description="数据来源类型 / Source type, e.g. simulation")
    data_type_zh: str | None = None
    data_type_en: str | None = None
    engine: str | None = None
    generated: bool | None = None
    measured: bool | None = None
    tag: str | None = Field(default=None, description="[S]/[M]/[C]/[A]/[G] 数据来源标签")


class ExperimentErrorView(BaseModel):
    code: str
    message: str
    type: str


class StatusTransitionView(BaseModel):
    status: ExperimentStatus
    at: str


class ExperimentResponse(BaseModel):
    experiment_id: str
    name: str
    status: ExperimentStatus = Field(description="created | queued | running | succeeded | failed")
    scenario: ScenarioRef
    backend: BackendRef
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    runtime: RuntimeView
    metrics: dict[str, Any] = Field(default_factory=dict, description="仿真指标 / Simulation metrics")
    artifacts: list[ArtifactView] = Field(default_factory=list)
    provenance: ProvenanceView | None = None
    error: ExperimentErrorView | None = None
    warnings: list[str] = Field(default_factory=list)
    status_history: list[StatusTransitionView] = Field(default_factory=list)

    @classmethod
    def from_record(cls, r: ExperimentRecord) -> ExperimentResponse:
        provenance = None
        if r.provenance is not None:
            source_type = r.provenance.get("source_type")
            zh, en = DATA_TYPE_LABELS.get(source_type or "", (None, None))
            provenance = ProvenanceView(
                source_type=source_type, data_type_zh=zh, data_type_en=en,
                engine=r.provenance.get("engine"), generated=r.provenance.get("generated"),
                measured=r.provenance.get("measured"), tag=r.provenance.get("tag"),
            )
        return cls(
            experiment_id=r.experiment_id,
            name=r.name,
            status=r.status,
            scenario=ScenarioRef(
                scenario_id=r.scenario_id, name_zh=r.scenario_name_zh, name_en=r.scenario_name_en
            ),
            backend=BackendRef(id=r.backend, version=r.backend_version),
            created_at=r.created_at,
            started_at=r.started_at,
            finished_at=r.finished_at,
            runtime=RuntimeView(**r.runtime.model_dump(exclude={"scenario_load_seconds"}))
            if r.runtime else RuntimeView(),
            metrics=r.result.metrics if r.result else {},
            artifacts=[ArtifactView.from_artifact(r.experiment_id, a) for a in r.artifacts],
            provenance=provenance,
            error=ExperimentErrorView(code=r.error.code.value, message=r.error.message, type=r.error.type)
            if r.error else None,
            warnings=r.result.warnings if r.result else [],
            status_history=[StatusTransitionView(status=t.status, at=t.at) for t in r.status_history],
        )


class ExperimentList(BaseModel):
    items: list[ExperimentResponse]
    total: int
    limit: int
    offset: int
