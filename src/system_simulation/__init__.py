"""
系统级仿真领域 / System-level simulation domain.

平台拥有统一领域模型；具体仿真器只是 SystemSimulationBackend 的一个实现。
"""

from .base import (
    Capability,
    ChannelRealization,
    ModelType,
    SystemBackendDescriptor,
    SystemBackendRegistry,
    SystemRunOutput,
    SystemSimulationBackend,
)
from .errors import (
    InvalidSystemScenarioError,
    SystemArtifactNotFoundError,
    SystemBackendNotFoundError,
    SystemBackendUnavailableError,
    SystemCapabilityNotSupportedError,
    SystemExperimentNotFoundError,
    SystemScenarioNotFoundError,
)
from .fake_backend import FAKE_SYSTEM_BACKEND_ID, FakeSystemBackend
from .models import (
    BaseStation,
    Cell,
    EvaluationContextLink,
    ExperimentType,
    SystemExperimentPurpose,
    SystemExperimentRecord,
    SystemExperimentStatus,
    SystemScenario,
    SystemSimulationResult,
    TrafficDemand,
    UeGeneratorConfig,
    UserEquipmentConfig,
    UserEquipmentResult,
)
from .scenarios import SystemScenarioCatalog
from .service import MODEL_LABELS, SystemBackendStatus, SystemExperimentService
from .store import FileSystemExperimentStore

__all__ = [
    "FAKE_SYSTEM_BACKEND_ID",
    "MODEL_LABELS",
    "BaseStation",
    "Capability",
    "Cell",
    "ChannelRealization",
    "EvaluationContextLink",
    "ExperimentType",
    "FakeSystemBackend",
    "FileSystemExperimentStore",
    "InvalidSystemScenarioError",
    "ModelType",
    "SystemArtifactNotFoundError",
    "SystemBackendDescriptor",
    "SystemBackendNotFoundError",
    "SystemBackendRegistry",
    "SystemBackendStatus",
    "SystemBackendUnavailableError",
    "SystemCapabilityNotSupportedError",
    "SystemExperimentNotFoundError",
    "SystemExperimentPurpose",
    "SystemExperimentRecord",
    "SystemExperimentService",
    "SystemExperimentStatus",
    "SystemRunOutput",
    "SystemScenario",
    "SystemScenarioCatalog",
    "SystemScenarioNotFoundError",
    "SystemSimulationBackend",
    "SystemSimulationResult",
    "TrafficDemand",
    "UeGeneratorConfig",
    "UserEquipmentConfig",
    "UserEquipmentResult",
]
