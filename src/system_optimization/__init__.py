"""
系统级优化 / System-level optimization.

冻结公共评价上下文（同一 UE / 业务 / 信道实现 / 仿真时长）下，由算法 SDK（Registry 中的算法）
生成系统参数候选，以版本化系统 KPI 评价候选。本包不依赖任何仿真引擎。
"""

from .errors import (
    BenchmarkProtocolNotFoundError,
    SystemOptimizationArtifactNotFoundError,
    SystemOptimizationBusyError,
    SystemOptimizationNotFoundError,
    SystemOptimizationServiceError,
    UnsupportedProblemTypeError,
)
from .models import (
    BenchmarkProtocol,
    CommonEvaluationContext,
    ParameterSpec,
    SystemOptimizationCandidate,
    SystemOptimizationRecord,
)
from .objectives import (
    NETWORK_THROUGHPUT_MAX_V0_1,
    NetworkThroughputMaxV01,
    SystemObjective,
    SystemObjectiveRegistry,
    default_system_objective_registry,
)
from .parameters import SCHEDULER_BETA, SystemParameter, SystemParameterCatalog, default_system_parameter_catalog
from .protocols import SYSTEM_BENCHMARK_V0_1, BenchmarkProtocolRegistry, default_protocol_registry
from .service import (
    DEFAULT_EVALUATION_BUDGET,
    MAX_EVALUATION_BUDGET,
    MAX_SYSTEM_CANDIDATES,
    SystemOptimizationService,
)
from .store import FileSystemOptimizationStore

__all__ = [
    "DEFAULT_EVALUATION_BUDGET",
    "MAX_EVALUATION_BUDGET",
    "MAX_SYSTEM_CANDIDATES",
    "ParameterSpec",
    "NETWORK_THROUGHPUT_MAX_V0_1",
    "SCHEDULER_BETA",
    "SYSTEM_BENCHMARK_V0_1",
    "BenchmarkProtocol",
    "BenchmarkProtocolNotFoundError",
    "BenchmarkProtocolRegistry",
    "CommonEvaluationContext",
    "FileSystemOptimizationStore",
    "NetworkThroughputMaxV01",
    "SystemObjective",
    "SystemObjectiveRegistry",
    "SystemOptimizationArtifactNotFoundError",
    "SystemOptimizationBusyError",
    "SystemOptimizationCandidate",
    "SystemOptimizationNotFoundError",
    "SystemOptimizationRecord",
    "SystemOptimizationService",
    "SystemOptimizationServiceError",
    "SystemParameter",
    "SystemParameterCatalog",
    "UnsupportedProblemTypeError",
    "default_protocol_registry",
    "default_system_objective_registry",
    "default_system_parameter_catalog",
]
