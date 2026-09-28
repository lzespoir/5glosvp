"""
实验模型 / Experiment models.

Simulation（一次仿真计算）≠ Experiment（平台管理的完整实验生命周期）。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from simulation.models import Artifact, RuntimeInfo, SimulationResult

EXPERIMENT_ID_PATTERN = re.compile(r"^EXP-[0-9A-F]{8}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExperimentStatus(str, Enum):
    """
    实验生命周期 / Experiment lifecycle.

    CREATED → QUEUED → RUNNING → SUCCEEDED
                               ↘ FAILED
    """

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (ExperimentStatus.SUCCEEDED, ExperimentStatus.FAILED)


class ExperimentErrorCode(str, Enum):
    SIMULATION_FAILED = "SIMULATION_FAILED"
    SIMULATION_TIMEOUT = "SIMULATION_TIMEOUT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    SCENARIO_INVALID = "SCENARIO_INVALID"
    ARTIFACT_EXPORT_FAILED = "ARTIFACT_EXPORT_FAILED"


class ExperimentError(BaseModel):
    """实验失败信息（不含 traceback，traceback 只写日志）/ Failure info without traceback."""

    code: ExperimentErrorCode
    message: str
    type: str


class StatusTransition(BaseModel):
    status: ExperimentStatus
    at: str


class ExperimentRecord(BaseModel):
    """平台实验记录 / Platform experiment record."""

    experiment_id: str
    name: str
    status: ExperimentStatus
    scenario_id: str
    scenario_name_zh: str
    scenario_name_en: str
    backend: str
    backend_version: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    # 场景配置快照（ScenarioConfig 的 JSON 形式）
    config: dict[str, Any]
    result: SimulationResult | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    error: ExperimentError | None = None
    runtime: RuntimeInfo | None = None
    provenance: dict[str, Any] | None = None
    status_history: list[StatusTransition] = Field(default_factory=list)

    def transition(self, status: ExperimentStatus) -> None:
        self.status = status
        self.status_history.append(StatusTransition(status=status, at=utc_now()))
