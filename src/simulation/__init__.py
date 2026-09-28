"""
5G 网络学习优化仿真验证平台 - 仿真层
5G Learning Optimization Simulation & Validation Platform - simulation layer.

具体后端请通过 `simulation.backends.get_backend()` 获取。
"""

from .base import SimulationBackend
from .errors import (
    ArtifactExportError,
    BackendUnavailableError,
    ScenarioConfigError,
    SimulationError,
    SimulationRunError,
)
from .models import (
    Artifact,
    RadioMapConfig,
    RadioMapData,
    RuntimeInfo,
    ScenarioConfig,
    SimulationResult,
    SimulationStatus,
    TransmitterConfig,
    new_experiment_id,
)

__all__ = [
    "Artifact",
    "ArtifactExportError",
    "BackendUnavailableError",
    "RadioMapConfig",
    "RadioMapData",
    "RuntimeInfo",
    "ScenarioConfig",
    "ScenarioConfigError",
    "SimulationBackend",
    "SimulationError",
    "SimulationResult",
    "SimulationRunError",
    "SimulationStatus",
    "TransmitterConfig",
    "new_experiment_id",
]
