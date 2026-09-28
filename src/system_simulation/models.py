"""
系统级仿真统一领域模型 / Canonical system-level domain models.

五层模型 / Five layers:
    1 Scenario     BaseStation · Cell · UserEquipment · TrafficDemand
    2 Propagation  信道 / Path Gain（由仿真后端提供）
    3 PHY          SINR · Link Adaptation (MCS) · 译码 / HARQ
    4 System       调度 · 资源分配
    5 KPI          见 evaluation.kpi

平台自有模型，不包含任何仿真引擎对象。输入（*Config）与结果（*Result）分开。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from evaluation.kpi import KpiResult

Vec3 = list[float]
EXPERIMENT_ID_PATTERN = re.compile(r"^EXP-[0-9A-F]{8}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Layer 1 — Scenario
# ---------------------------------------------------------------------------


class BaseStation(_Strict):
    bs_id: str
    name: str | None = None
    position: Vec3 = Field(min_length=3, max_length=3)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AntennaArrayConfig(_Strict):
    num_rows: int = Field(ge=1, le=16)
    num_cols: int = Field(ge=1, le=16)
    pattern: str = "tr38901"
    polarization: str = "V"
    source: str = "[A] Assumption"

    @property
    def num_elements(self) -> int:
        return self.num_rows * self.num_cols


class Cell(_Strict):
    cell_id: str
    bs_id: str
    position: Vec3 | None = Field(default=None, description="省略时使用所属基站位置")
    carrier_frequency_hz: float = Field(gt=0)
    bandwidth_hz: float = Field(gt=0)
    tx_power_dbm: float = Field(ge=-10, le=70)
    antenna: AntennaArrayConfig
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrafficModelType(str, Enum):
    FULL_BUFFER = "full_buffer"


class TrafficDemand(_Strict):
    type: TrafficModelType = TrafficModelType.FULL_BUFFER
    direction: Literal["downlink"] = "downlink"
    source: Literal["assumption"] = "assumption"
    tag: Literal["[A]"] = "[A]"


class UserEquipmentConfig(_Strict):
    ue_id: str
    position: Vec3 = Field(min_length=3, max_length=3)
    serving_cell_id: str | None = None
    traffic_demand: TrafficDemand | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UeGeneratorType(str, Enum):
    UNIFORM_AREA_WITH_PATH = "uniform_area_with_path"


class UeGeneratorConfig(_Strict):
    """程序生成 UE：在矩形区域内均匀撒点，按生成顺序保留前 count 个与服务小区存在传播路径的位置。"""

    type: UeGeneratorType = UeGeneratorType.UNIFORM_AREA_WITH_PATH
    count: int = Field(ge=1, le=10)
    seed: int
    area_center: list[float] = Field(min_length=2, max_length=2)
    area_size: list[float] = Field(min_length=2, max_length=2)
    height_m: float = 1.5
    max_candidates: int = Field(default=60, ge=1, le=1000)
    source: str = "[A] Assumption"


class SchedulerConfig(_Strict):
    id: Literal["pf_su_mimo"] = "pf_su_mimo"
    beta: float = Field(default=0.9, gt=0, lt=1)


class LinkAdaptationConfig(_Strict):
    id: Literal["olla"] = "olla"
    bler_target: float = Field(default=0.1, gt=0, lt=1)
    mcs_table_index: int = Field(default=1, ge=1, le=4)


class PowerControlConfig(_Strict):
    id: Literal["downlink_fair"] = "downlink_fair"
    guaranteed_power_ratio: float = Field(default=0.5, ge=0, le=1)
    fairness: float = Field(default=0.0, ge=0)


class SystemSimulationConfig(_Strict):
    num_slots: int = Field(default=200, ge=1, le=2000)
    subcarrier_spacing_hz: float = 30e3
    num_prb: int = Field(default=273, ge=1, le=275)
    num_data_symbols_per_slot: int = Field(default=12, ge=1, le=14)
    slot_duration_s: float = Field(default=0.5e-3, gt=0)
    noise_figure_db: float = 7.0
    temperature_k: float = 290.0
    max_depth: int = Field(default=5, ge=0, le=10)
    samples_per_src: int = Field(default=1_000_000, ge=1000)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    link_adaptation: LinkAdaptationConfig = Field(default_factory=LinkAdaptationConfig)
    power_control: PowerControlConfig = Field(default_factory=PowerControlConfig)

    @property
    def num_subcarriers(self) -> int:
        return self.num_prb * 12

    @property
    def simulated_duration_s(self) -> float:
        return self.num_slots * self.slot_duration_s


class SystemScenario(_Strict):
    scenario_id: str
    name_zh: str
    name_en: str
    description: str | None = None
    backend: str
    scene: str
    base_stations: list[BaseStation] = Field(min_length=1)
    cells: list[Cell] = Field(min_length=1)
    ues: list[UserEquipmentConfig] = Field(default_factory=list)
    ue_generator: UeGeneratorConfig | None = None
    traffic: TrafficDemand = Field(default_factory=TrafficDemand)
    simulation: SystemSimulationConfig = Field(default_factory=SystemSimulationConfig)
    seed: int
    assumptions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> SystemScenario:
        if bool(self.ues) == (self.ue_generator is not None):
            raise ValueError("Exactly one of 'ues' or 'ue_generator' must be provided")
        bs_ids = {b.bs_id for b in self.base_stations}
        cell_ids = {c.cell_id for c in self.cells}
        if len(bs_ids) != len(self.base_stations) or len(cell_ids) != len(self.cells):
            raise ValueError("Duplicate base station or cell id")
        for c in self.cells:
            if c.bs_id not in bs_ids:
                raise ValueError(f"Cell {c.cell_id} references unknown base station {c.bs_id}")
        ue_ids = [u.ue_id for u in self.ues]
        if len(set(ue_ids)) != len(ue_ids):
            raise ValueError("Duplicate UE id")
        for u in self.ues:
            if u.serving_cell_id is not None and u.serving_cell_id not in cell_ids:
                raise ValueError(f"UE {u.ue_id} references unknown cell {u.serving_cell_id}")
        return self

    @property
    def ue_count(self) -> int:
        return self.ue_generator.count if self.ue_generator else len(self.ues)

    def base_station(self, bs_id: str) -> BaseStation:
        return next(b for b in self.base_stations if b.bs_id == bs_id)

    def cell_position(self, cell: Cell) -> Vec3:
        return cell.position or self.base_station(cell.bs_id).position


# ---------------------------------------------------------------------------
# Layers 2–4 — Results
# ---------------------------------------------------------------------------


class UserEquipmentResult(BaseModel):
    """
    单 UE 结果。值为 None 时必须在 unavailable 中给出原因。
    throughput_mbps 由 KPI 引擎（UE_THROUGHPUT_V0_1）根据 decoded_bits 计算后写入。
    """

    ue_id: str
    serving_cell_id: str
    position: Vec3
    # Layer 2 — Propagation
    mean_channel_gain_db: float | None = None
    # Layer 3 — PHY
    sinr_eff_db_mean: float | None = None
    mcs_index_mean: float | None = None
    scheduled_slots: int
    acked_slots: int
    tbler: float | None = None
    # Layer 4 — System
    allocated_re_per_slot_mean: float
    allocated_re_share: float
    tx_power_w_mean: float | None = None
    # Layer 5 inputs / outputs
    decoded_bits: int
    simulated_duration_s: float
    throughput_mbps: float | None = None
    throughput_metric_id: str | None = None
    unavailable: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemRuntime(BaseModel):
    propagation_seconds: float | None = None
    system_seconds: float | None = None
    total_seconds: float | None = None


class CellTopology(BaseModel):
    cell_id: str
    bs_id: str
    position: Vec3
    carrier_frequency_hz: float
    bandwidth_hz: float
    tx_power_dbm: float


class SystemSimulationResult(BaseModel):
    """后端产出的统一系统级结果（不含 KPI；KPI 由评价层计算）。"""

    scenario_id: str
    cells: list[CellTopology] = Field(default_factory=list)
    backend: str
    backend_version: str | None
    provider_versions: dict[str, str | None] = Field(default_factory=dict)
    seed: int
    num_slots: int
    slot_duration_s: float
    simulated_duration_s: float
    num_data_re_per_slot: int
    ue_results: list[UserEquipmentResult]
    scheduler: dict[str, Any]
    link_adaptation: dict[str, Any]
    power_control: dict[str, Any]
    ue_generation: dict[str, Any] | None = None
    compute_device: str | None = None
    runtime: SystemRuntime = Field(default_factory=SystemRuntime)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Persisted experiment record
# ---------------------------------------------------------------------------


class ExperimentType(str, Enum):
    PROPAGATION = "propagation"
    SYSTEM = "system"


class SystemExperimentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SystemErrorCode(str, Enum):
    SYSTEM_SIMULATION_FAILED = "SYSTEM_SIMULATION_FAILED"
    INVALID_SYSTEM_SCENARIO = "INVALID_SYSTEM_SCENARIO"
    NO_UE_RESULTS = "NO_UE_RESULTS"
    KPI_CALCULATION_FAILED = "KPI_CALCULATION_FAILED"
    ARTIFACT_EXPORT_FAILED = "ARTIFACT_EXPORT_FAILED"


class SystemExperimentError(BaseModel):
    code: SystemErrorCode
    message: str
    type: str


class StatusTransition(BaseModel):
    status: SystemExperimentStatus
    at: datetime


class ArtifactRef(BaseModel):
    name: str
    type: str
    media_type: str
    description: str | None = None


class SystemExperimentRecord(BaseModel):
    experiment_id: str
    name: str
    experiment_type: ExperimentType = ExperimentType.SYSTEM
    purpose: Literal["standalone"] = "standalone"
    status: SystemExperimentStatus = SystemExperimentStatus.CREATED
    scenario_id: str
    scenario_name_zh: str
    scenario_name_en: str
    backend: str
    backend_version: str | None = None
    seed: int
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: SystemSimulationResult | None = None
    kpis: list[KpiResult] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    error: SystemExperimentError | None = None
    warnings: list[str] = Field(default_factory=list)
    status_history: list[StatusTransition] = Field(default_factory=list)

    def transition(self, status: SystemExperimentStatus) -> None:
        now = utc_now()
        self.status = status
        self.status_history.append(StatusTransition(status=status, at=now))
        if status == SystemExperimentStatus.RUNNING:
            self.started_at = now
        if status in (SystemExperimentStatus.SUCCEEDED, SystemExperimentStatus.FAILED):
            self.finished_at = now
