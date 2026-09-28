"""
默认后端注册 / Default backend registration.
"""

from ..base import SimulationBackend
from ..fake_backend import FAKE_BACKEND_ID, FakeBackend
from ..registry import BackendDescriptor, BackendRegistry
from .sionna_backend import BACKEND_NAME as SIONNA_BACKEND_ID
from .sionna_backend import SionnaBackend


def default_registry(include_testing: bool = False) -> BackendRegistry:
    """
    生产后端注册表；include_testing=True（即 TESTING=true）时才加入 FakeBackend。
    """
    registry = BackendRegistry()
    registry.register(
        BackendDescriptor(
            id=SIONNA_BACKEND_ID,
            name_zh="Sionna RT 高保真仿真",
            name_en="Sionna RT High-Fidelity Simulation",
            factory=SionnaBackend,
            capabilities=["radio_map", "rss", "path_gain", "sinr"],
        )
    )
    if include_testing:
        registry.register(
            BackendDescriptor(
                id=FAKE_BACKEND_ID,
                name_zh="测试用假后端（仅软件测试）",
                name_en="Fake Backend (software testing only)",
                factory=FakeBackend,
                capabilities=["radio_map"],
            )
        )
    return registry


def get_backend(name: str) -> SimulationBackend:
    return default_registry().create(name)


__all__ = ["SionnaBackend", "default_registry", "get_backend"]
