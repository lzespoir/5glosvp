"""
仿真后端统一接口 / Unified simulation backend interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import ScenarioConfig, SimulationResult


class SimulationBackend(ABC):
    """
    仿真后端统一接口
    Unified simulation backend interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """后端名称 / Backend name."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """
        环境检查，不得抛出异常，失败原因写入返回值
        Check whether the backend is available. Must not raise.
        """
        raise NotImplementedError

    @abstractmethod
    def load_scenario(self, config: ScenarioConfig) -> None:
        """
        加载场景
        Load simulation scenario.
        """
        raise NotImplementedError

    @abstractmethod
    def run(self, experiment_id: str | None = None) -> SimulationResult:
        """
        执行仿真
        Run simulation.
        """
        raise NotImplementedError

    @abstractmethod
    def export(self, result: SimulationResult, output_dir: Path) -> None:
        """
        导出实验产物
        Export simulation artifacts.
        """
        raise NotImplementedError
