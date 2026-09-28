"""
仿真后端注册表 / Simulation backend registry.

业务代码通过 registry 按 id 获取后端，禁止散落 if backend == "..." 判断。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .base import SimulationBackend
from .errors import BackendUnavailableError


@dataclass(frozen=True)
class BackendDescriptor:
    """后端描述 / Backend descriptor."""

    id: str
    name_zh: str
    name_en: str
    factory: Callable[[], SimulationBackend]
    capabilities: list[str] = field(default_factory=list)


class BackendRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, BackendDescriptor] = {}

    def register(self, descriptor: BackendDescriptor) -> None:
        if descriptor.id in self._descriptors:
            raise ValueError(f"Backend '{descriptor.id}' already registered")
        self._descriptors[descriptor.id] = descriptor

    def get(self, backend_id: str) -> BackendDescriptor:
        try:
            return self._descriptors[backend_id]
        except KeyError:
            raise BackendUnavailableError(
                f"Unknown backend '{backend_id}'. Available: {', '.join(self.ids()) or '-'}"
            ) from None

    def create(self, backend_id: str) -> SimulationBackend:
        return self.get(backend_id).factory()

    def ids(self) -> list[str]:
        return sorted(self._descriptors)

    def list(self) -> list[BackendDescriptor]:
        return [self._descriptors[i] for i in self.ids()]
