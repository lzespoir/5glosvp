"""
KPI 定义与结果模型 / KPI definition and result models.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class KpiScope(str, Enum):
    UE = "ue"
    NETWORK = "network"


class KpiDefinition(BaseModel):
    """版本化 KPI 定义；公式或口径的任何改变都必须使用新的 id。"""

    model_config = ConfigDict(frozen=True)

    id: str
    version: str
    name_zh: str
    name_en: str
    unit: str
    scope: KpiScope
    formula: str
    measurement_method: str
    required_inputs: list[str]
    source: str
    assumptions: list[str] = Field(default_factory=list)
    acceptance_kpi: bool = False
    note_zh: str | None = None
    doc: str


class UeThroughputInput(BaseModel):
    """单个 UE 的 KPI 输入：成功译码比特数与仿真时长（来自系统级仿真结果）。"""

    ue_id: str
    decoded_bits: int = Field(ge=0)
    simulated_duration_s: float = Field(gt=0)


class KpiContext(BaseModel):
    """KPI 溯源上下文。"""

    source_experiment: str
    backend: str
    scenario_id: str
    seed: int
    source_type: str
    measured: bool = False


class KpiResult(BaseModel):
    metric_id: str
    version: str
    name_zh: str
    name_en: str
    unit: str
    scope: KpiScope
    available: bool
    value: float | None = None
    per_ue: dict[str, float] | None = None
    unavailable_reason: str | None = None
    sample_size: int
    calculation_method: str
    source_experiment: str
    backend: str
    scenario_id: str
    seed: int
    source_type: str
    measured: bool = False
    assumptions: list[str] = Field(default_factory=list)
    acceptance_kpi: bool = False
