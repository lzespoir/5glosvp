"""系统级优化错误 / System optimization errors."""

from __future__ import annotations


class SystemOptimizationServiceError(Exception):
    pass


class SystemOptimizationNotFoundError(SystemOptimizationServiceError):
    pass


class SystemOptimizationArtifactNotFoundError(SystemOptimizationServiceError):
    pass


class BenchmarkProtocolNotFoundError(SystemOptimizationServiceError):
    pass


class SystemOptimizationBusyError(SystemOptimizationServiceError):
    """同一时间只允许一个系统级优化运行（候选实验共享仿真资源）。"""


class UnsupportedProblemTypeError(SystemOptimizationServiceError):
    """优化器不支持系统级问题。"""
