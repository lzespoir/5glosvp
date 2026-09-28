"""
系统级仿真后端接口、能力声明与注册表 / System backend interface, capabilities and registry.

业务层按 capability 选择后端，不写死具体仿真器。未来可接入
FastSystemBackend / MATLAB / ns-3 / 外部仿真器，只需实现 SystemSimulationBackend。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from .errors import SystemBackendNotFoundError
from .models import SystemScenario, SystemSimulationResult


class Capability(str, Enum):
    PROPAGATION = "propagation"
    RADIO_MAP = "radio_map"
    SYSTEM_SIMULATION = "system_simulation"
    SCHEDULING = "scheduling"
    LINK_ADAPTATION = "link_adaptation"
    UE_METRICS = "ue_metrics"
    THROUGHPUT = "throughput"
    # 可导出冻结信道实现并在多次系统仿真中复用（公平比较前提）
    CHANNEL_REUSE = "channel_reuse"


class ModelType(str, Enum):
    """结果的模型来源；前端据此区分 Sionna 仿真、工程近似与测试夹具。"""

    SIONNA_SYS = "sionna_sys"
    ENGINEERING_APPROXIMATION = "engineering_approximation"
    TEST_FIXTURE = "test_fixture"


@dataclass(frozen=True)
class SystemRunOutput:
    result: SystemSimulationResult
    # 每时隙原始记录，键 → [num_slots, num_ue] 数组；用于独立复核
    slot_trace: dict[str, np.ndarray]


@dataclass(frozen=True)
class ChannelRealization:
    """
    冻结的信道实现（平台自有数据，不含引擎对象）。
    arrays 为后端私有的数值载荷（例如 {"cfr": complex64 数组}），平台只负责保存与哈希。
    propagation_fingerprint 标识生成该信道的传播相关场景字段，复用前必须一致。
    """

    ue_ids: tuple[str, ...]
    serving_cell_ids: tuple[str, ...]
    positions: np.ndarray                 # [num_ue, 3] m
    mean_channel_gain_db: np.ndarray      # [num_ue]
    arrays: dict[str, np.ndarray]
    provider: str
    provider_versions: dict[str, str | None]
    propagation_fingerprint: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SystemSimulationBackend(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """不得抛出异常；返回 available / version / errors / warnings。"""

    @abstractmethod
    def run(
        self,
        scenario: SystemScenario,
        experiment_id: str,
        log: logging.Logger,
        channel: ChannelRealization | None = None,
    ) -> SystemRunOutput:
        """
        执行系统级仿真；场景无法执行时抛出 InvalidSystemScenarioError。
        channel 非空时必须复用该冻结信道（不重新生成 UE / 传播），仅声明 CHANNEL_REUSE 的后端支持。
        """

    def realize_channel(self, scenario: SystemScenario, log: logging.Logger) -> ChannelRealization:
        """生成一次冻结信道实现；仅声明 CHANNEL_REUSE 能力的后端实现。"""
        raise NotImplementedError(f"Backend '{self.name}' does not support channel realization reuse")


@dataclass(frozen=True)
class SystemBackendDescriptor:
    id: str
    name_zh: str
    name_en: str
    factory: Callable[[], SystemSimulationBackend]
    capabilities: tuple[Capability, ...]
    model_type: ModelType
    source_type: str = "simulation"
    category: str = "system"
    provider: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for c in self.capabilities:
            if not isinstance(c, Capability):
                raise ValueError(f"Unknown backend capability: {c!r}")

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities


class SystemBackendRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, SystemBackendDescriptor] = {}

    def register(self, descriptor: SystemBackendDescriptor) -> None:
        if descriptor.id in self._descriptors:
            raise ValueError(f"System backend '{descriptor.id}' already registered")
        self._descriptors[descriptor.id] = descriptor

    def get(self, backend_id: str) -> SystemBackendDescriptor:
        try:
            return self._descriptors[backend_id]
        except KeyError:
            raise SystemBackendNotFoundError(
                f"Unknown system backend '{backend_id}'. Available: {', '.join(sorted(self._descriptors)) or '-'}"
            ) from None

    def list(self) -> list[SystemBackendDescriptor]:
        return [self._descriptors[k] for k in sorted(self._descriptors)]

    def with_capability(self, capability: Capability) -> list[SystemBackendDescriptor]:
        return [d for d in self.list() if d.supports(capability)]
