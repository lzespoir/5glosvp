"""
系统级仿真错误 / System simulation errors.
"""

from __future__ import annotations


class SystemSimulationError(Exception):
    """系统级仿真错误基类。"""


class SystemScenarioNotFoundError(SystemSimulationError):
    pass


class SystemExperimentNotFoundError(SystemSimulationError):
    pass


class SystemBackendNotFoundError(SystemSimulationError):
    pass


class SystemCapabilityNotSupportedError(SystemSimulationError):
    pass


class InvalidSystemScenarioError(SystemSimulationError):
    """场景配置无法被该后端执行（如 V0.1 后端只支持单小区）。"""


class SystemBackendUnavailableError(SystemSimulationError):
    pass


class SystemArtifactNotFoundError(SystemSimulationError):
    pass
