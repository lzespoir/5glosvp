"""
优化层 / Optimization layer.

Optimizer（参数枚举）与 Objective（目标值计算）都不依赖任何仿真引擎；
OptimizationService 通过 ExperimentService 运行每个候选。
"""

from .base import CandidateEvaluator, Objective, ObjectiveInputs, Optimizer, OptimizerInfo, SearchResult
from .errors import (
    CandidateEvaluationError,
    InvalidParameterSpaceError,
    ObjectiveNotFoundError,
    OptimizationNotFoundError,
    OptimizationServiceError,
    OptimizerNotFoundError,
)
from .models import (
    OptimizationCandidate,
    OptimizationComparison,
    OptimizationProblem,
    OptimizationRecord,
    OptimizationStatus,
    ParameterSpace,
)
from .registry import ObjectiveRegistry, OptimizerRegistry, default_objective_registry, default_optimizer_registry
from .service import MAX_CANDIDATES, OptimizationService
from .store import FileOptimizationStore, OptimizationStore

__all__ = [
    "MAX_CANDIDATES",
    "CandidateEvaluationError",
    "CandidateEvaluator",
    "FileOptimizationStore",
    "InvalidParameterSpaceError",
    "Objective",
    "ObjectiveInputs",
    "ObjectiveNotFoundError",
    "ObjectiveRegistry",
    "OptimizationCandidate",
    "OptimizationComparison",
    "OptimizationNotFoundError",
    "OptimizationProblem",
    "OptimizationRecord",
    "OptimizationService",
    "OptimizationServiceError",
    "OptimizationStatus",
    "OptimizationStore",
    "Optimizer",
    "OptimizerInfo",
    "OptimizerNotFoundError",
    "OptimizerRegistry",
    "ParameterSpace",
    "SearchResult",
    "default_objective_registry",
    "default_optimizer_registry",
]
