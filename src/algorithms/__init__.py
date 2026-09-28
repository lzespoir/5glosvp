"""
算法接入框架 / Algorithm integration framework (SDK 0.1).

    Research Algorithm → Algorithm SDK (lifecycle) → AlgorithmDriver（预算 / trace）→ 平台评价回调

本包不依赖任何仿真引擎、实验仓库或 KPI 实现。
"""

from .compatibility import CompatibilityReport, check_compatibility, resolve_hyperparameters
from .driver import AlgorithmDriver
from .errors import AlgorithmCompatibilityError, AlgorithmError, AlgorithmExecutionError, AlgorithmNotFoundError
from .parameter_space import ParameterConstraint, ParameterSpace, canonical_json, canonical_sha256
from .registry import AlgorithmRegistry, default_algorithm_registry
from .sdk import (
    ALGORITHM_SDK_VERSION,
    Algorithm,
    AlgorithmCapabilities,
    AlgorithmCategory,
    AlgorithmMetadata,
    AlgorithmProblem,
    AlgorithmRecommendation,
    AlgorithmStatus,
    CompatibilityCode,
    CompatibilityIssue,
    ConstraintResult,
    EvaluationResult,
    EvaluationStatus,
    HyperparameterDefinition,
    HyperparameterType,
    HyperparameterValue,
    StopReason,
)
from .trace import AlgorithmTrace, TraceEvaluation, TraceRound

__all__ = [
    "ALGORITHM_SDK_VERSION",
    "Algorithm",
    "AlgorithmCapabilities",
    "AlgorithmCategory",
    "AlgorithmCompatibilityError",
    "AlgorithmDriver",
    "AlgorithmError",
    "AlgorithmExecutionError",
    "AlgorithmMetadata",
    "AlgorithmNotFoundError",
    "AlgorithmProblem",
    "AlgorithmRecommendation",
    "AlgorithmRegistry",
    "AlgorithmStatus",
    "AlgorithmTrace",
    "CompatibilityCode",
    "CompatibilityIssue",
    "CompatibilityReport",
    "ConstraintResult",
    "EvaluationResult",
    "EvaluationStatus",
    "HyperparameterDefinition",
    "HyperparameterType",
    "HyperparameterValue",
    "ParameterConstraint",
    "ParameterSpace",
    "StopReason",
    "TraceEvaluation",
    "TraceRound",
    "canonical_json",
    "canonical_sha256",
    "check_compatibility",
    "default_algorithm_registry",
    "resolve_hyperparameters",
]
