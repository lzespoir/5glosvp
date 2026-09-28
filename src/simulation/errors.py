"""
平台统一异常 / Platform-level simulation exceptions.

上层代码只需要捕获这些异常，而不需要了解具体后端的异常类型。
Upper layers only catch these, never backend-specific exceptions.
"""


class SimulationError(Exception):
    """所有仿真相关错误的基类 / Base class for all simulation errors."""


class BackendUnavailableError(SimulationError):
    """后端未安装或运行环境不可用 / Backend not installed or runtime unavailable."""


class ScenarioConfigError(SimulationError):
    """场景配置无效（场景不存在、坐标无效、Radio Map 配置无效等）/ Invalid scenario configuration."""


class SimulationRunError(SimulationError):
    """仿真执行失败 / Simulation execution failed."""


class ArtifactExportError(SimulationError):
    """实验产物导出失败（如输出目录不可写）/ Failed to export artifacts."""
