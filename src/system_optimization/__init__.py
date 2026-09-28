"""
系统级优化 / System-level optimization.

冻结公共评价上下文（同一 UE / 业务 / 信道实现 / 仿真时长）下，用统一 Optimizer 接口
改变一个系统参数，以版本化系统 KPI 评价候选。本包不依赖任何仿真引擎。
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
from .service import MAX_SYSTEM_CANDIDATES, SystemOptimizationService
from .store import FileSystemOptimizationStore

__all__ = [
    "MAX_SYSTEM_CANDIDATES",
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
