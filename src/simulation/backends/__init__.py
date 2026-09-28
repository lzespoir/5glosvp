"""
仿真后端注册表 / Simulation backend registry.
"""

from collections.abc import Callable

from ..base import SimulationBackend
from ..errors import BackendUnavailableError
from .sionna_backend import SionnaBackend

_REGISTRY: dict[str, Callable[[], SimulationBackend]] = {
    "sionna_rt": SionnaBackend,
}


def get_backend(name: str) -> SimulationBackend:
    try:
        factory = _REGISTRY[name]
    except KeyError:
        raise BackendUnavailableError(
            f"Unknown backend '{name}'. Available: {', '.join(sorted(_REGISTRY))}"
        ) from None
    return factory()


__all__ = ["SionnaBackend", "get_backend"]
