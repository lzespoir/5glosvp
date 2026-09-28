"""
平台统一数据模型 / Canonical data model.

本模块不依赖任何具体仿真引擎（如 Sionna）。
This module must not depend on any concrete simulation engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal

import numpy as np
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .errors import ScenarioConfigError

RadioMapMetric = Literal["rss", "path_gain", "sinr"]

METRIC_UNITS: dict[str, str] = {
    "rss": "dBm",
    "path_gain": "dB",
    "sinr": "dB",
}


class ProvenanceTag(str, Enum):
    """
    数据来源标签 / Data provenance tags.
    """

    STANDARD = "S"  # Standard-based / 标准依据
    MEASURED = "M"  # Measured / 实测
    CALIBRATED = "C"  # Calibrated / 实测校准
    ASSUMPTION = "A"  # Assumption / 工程假设
    GENERATED = "G"  # Generated / 仿真生成


class SimulationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


def new_experiment_id() -> str:
    """生成唯一实验编号 EXP-XXXXXXXX / Generate a unique experiment ID."""
    return f"EXP-{uuid.uuid4().hex[:8].upper()}"


def not_available(reason: str) -> dict[str, str]:
    """无法由后端得到的指标统一用此结构表示，禁止伪造数值。"""
    return {"status": "not_available", "reason": reason}


# ---------------------------------------------------------------------------
# 场景配置 / Scenario configuration
# ---------------------------------------------------------------------------


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TransmitterConfig(_StrictModel):
    """发射端配置 / Transmitter configuration."""

    id: str
    position: list[float] = Field(min_length=3, max_length=3)
    # 欧拉角 (alpha, beta, gamma) [rad]
    orientation: list[float] | None = Field(default=None, min_length=3, max_length=3)
    # None 表示使用后端默认发射功率，实际值会记录在结果中
    power_dbm: float | None = None


class MeasurementArea(_StrictModel):
    """
    测量平面 / Measurement plane.

    center: 平面中心 (x, y, z) [m]
    size: 平面尺寸 (width, height) [m]
    orientation: 平面朝向欧拉角 [rad]
    """

    center: list[float] = Field(min_length=3, max_length=3)
    size: list[float] = Field(min_length=2, max_length=2)
    orientation: list[float] = Field(default=[0.0, 0.0, 0.0], min_length=3, max_length=3)

    @field_validator("size")
    @classmethod
    def _positive_size(cls, v: list[float]) -> list[float]:
        if any(s <= 0 for s in v):
            raise ValueError("measurement_area.size must be positive")
        return v


class RadioMapConfig(_StrictModel):
    """无线电地图配置 / Radio map configuration."""

    metric: RadioMapMetric = "rss"
    cell_size: list[float] = Field(default=[5.0, 5.0], min_length=2, max_length=2)
    # None 表示由后端自动覆盖整个场景
    measurement_area: MeasurementArea | None = None
    max_depth: int = Field(default=5, ge=0)
    samples_per_tx: int = Field(default=1_000_000, gt=0)

    @field_validator("cell_size")
    @classmethod
    def _positive_cell(cls, v: list[float]) -> list[float]:
        if any(s <= 0 for s in v):
            raise ValueError("cell_size must be positive")
        return v


class ScenarioConfig(_StrictModel):
    """场景配置 / Scenario configuration."""

    scenario_id: str
    name_zh: str
    name_en: str
    backend: str
    scene_name: str
    frequency_hz: float = Field(gt=0)
    bandwidth_hz: float = Field(gt=0)
    random_seed: int = Field(ge=0, lt=2**32)
    transmitters: list[TransmitterConfig] = Field(min_length=1)
    radio_map: RadioMapConfig = Field(default_factory=RadioMapConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ScenarioConfig:
        path = Path(path)
        if not path.is_file():
            raise ScenarioConfigError(f"Scenario config not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ScenarioConfigError(f"Malformed YAML in scenario config {path}: {e}") from e
        if not isinstance(data, dict):
            raise ScenarioConfigError(f"Scenario config must be a YAML mapping: {path}")
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            raise ScenarioConfigError(f"Invalid scenario config {path}:\n{e}") from e

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            self.model_dump(mode="json"), allow_unicode=True, sort_keys=False
        )


# ---------------------------------------------------------------------------
# 统一仿真结果 / Canonical simulation result
# ---------------------------------------------------------------------------


@dataclass
class RadioMapData:
    """
    平台自有的无线电地图数值表示 / Platform-owned numeric radio map.

    所有数组形状为 (num_cells_y, num_cells_x)，无覆盖的格点为 NaN。
    values 是 metric 对应单位（dBm / dB）下的数值。
    """

    metric: str
    unit: str
    values: np.ndarray
    x: np.ndarray  # 每个格点中心的全局 x 坐标 [m]
    y: np.ndarray  # 每个格点中心的全局 y 坐标 [m]
    z: np.ndarray  # 每个格点中心的全局 z 坐标 [m]
    center: list[float]
    size: list[float]
    orientation: list[float]
    cell_size: list[float]
    transmitter_positions: np.ndarray  # (num_tx, 3)
    transmitter_ids: list[str]
    # 其他同时得到的指标，key 为 metric 名称
    extra_layers: dict[str, np.ndarray] = field(default_factory=dict)

    def statistics(self) -> dict[str, Any]:
        return layer_statistics(self.values, self.metric)

    def layer_statistics(self) -> dict[str, dict[str, Any]]:
        return {name: layer_statistics(layer, name) for name, layer in self.extra_layers.items()}


def layer_statistics(values: np.ndarray, metric: str) -> dict[str, Any]:
    """统计一层 Radio Map（NaN 视为无覆盖）/ Statistics of one radio map layer."""
    finite = values[np.isfinite(values)]
    total = int(values.size)
    stats: dict[str, Any] = {
        "metric": metric,
        "unit": METRIC_UNITS.get(metric),
        "num_cells": total,
        "num_covered_cells": int(finite.size),
        "coverage_ratio": float(finite.size / total) if total else 0.0,
        "min": None,
        "max": None,
        "mean": None,
        "median": None,
    }
    if finite.size:
        stats.update(
            min=float(finite.min()),
            max=float(finite.max()),
            mean=float(finite.mean()),
            median=float(np.median(finite)),
        )
    return stats


class Artifact(_StrictModel):
    """
    实验产物 / Experiment artifact.

    path 为相对于实验产物目录的路径（可跨机器迁移），禁止写入绝对路径。
    path is relative to the experiment artifact directory; never absolute.
    """

    name: str
    path: str
    kind: str
    media_type: str = "application/octet-stream"
    description: str | None = None

    @field_validator("path")
    @classmethod
    def _relative_path(cls, v: str) -> str:
        p = PurePosixPath(v)
        if p.is_absolute() or PureWindowsPath(v).is_absolute() or ".." in p.parts:
            raise ValueError(f"artifact path must be relative without '..': {v}")
        return v


class RuntimeInfo(BaseModel):
    """
    运行耗时（秒，均为真实测量值）/ Measured runtimes in seconds.

    simulation_seconds: backend.run() 内部仿真计算耗时
    artifact_export_seconds: backend.export() 耗时
    total_seconds: 实验开始 → 产物导出完成（含场景加载、结果转换与编排开销）
    """

    scenario_load_seconds: float | None = None
    simulation_seconds: float
    artifact_export_seconds: float | None = None
    total_seconds: float | None = None


class SimulationResult(BaseModel):
    """
    统一仿真结果 / Canonical simulation result.

    上层代码不需要知道结果来自哪个后端。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    experiment_id: str
    backend: str
    backend_version: str | None
    scenario_id: str
    status: SimulationStatus
    started_at: str
    finished_at: str
    # 兼容 Day 1 schema：等于 runtime.simulation_seconds（仿真计算耗时）
    runtime_seconds: float
    runtime: RuntimeInfo
    random_seed: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # 数值数据不进入 JSON，由 artifact 导出为 NPZ
    radio_map: RadioMapData | None = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _default_runtime(cls, data: Any) -> Any:
        if isinstance(data, dict) and "runtime" not in data and "runtime_seconds" in data:
            data = {**data, "runtime": {"simulation_seconds": data["runtime_seconds"]}}
        return data

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, text: str) -> SimulationResult:
        return cls.model_validate_json(text)
