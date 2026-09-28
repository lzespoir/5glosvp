"""优化服务异常 / Optimization service exceptions."""

from __future__ import annotations


class OptimizationServiceError(Exception):
    """优化服务错误基类 / Base class for optimization errors."""


class OptimizerNotFoundError(OptimizationServiceError):
    pass


class ObjectiveNotFoundError(OptimizationServiceError):
    pass


class OptimizationNotFoundError(OptimizationServiceError):
    pass


class InvalidParameterSpaceError(OptimizationServiceError):
    pass


class CandidateEvaluationError(OptimizationServiceError):
    """候选评价失败（仿真失败或目标函数无法计算）；整个优化运行随之失败。"""

    def __init__(self, candidate_id: str, message: str, experiment_id: str | None = None, code: str = "") -> None:
        super().__init__(message)
        self.candidate_id = candidate_id
        self.experiment_id = experiment_id
        self.code = code
