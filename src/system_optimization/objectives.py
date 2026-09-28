"""
系统级目标函数 / System-level objectives.

    System Result → KPI Engine → Objective Evaluator
目标函数只读取版本化 KPI 数值，不访问仿真结果或仿真引擎。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field

from evaluation.kpi import NETWORK_THROUGHPUT_V0_1
from optimization.errors import ObjectiveNotFoundError
from optimization.models import Direction, ObjectiveEvaluation

NETWORK_THROUGHPUT_MAX_V0_1 = "NETWORK_THROUGHPUT_MAX_V0_1"


@dataclass(frozen=True)
class SystemObjectiveInfo:
    id: str
    version: str
    direction: Direction
    name_zh: str
    name_en: str
    input_kpis: tuple[str, ...]
    formula: str
    unit: str
    required_experiment_type: str
    required_capabilities: tuple[str, ...]
    description_zh: str
    description_en: str
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    acceptance_kpi: bool = False
    measured_data: bool = False
    huawei_data: bool = False
    document: str = ""
    extra: dict[str, str] = field(default_factory=dict)


class SystemObjective(ABC):
    """版本化系统级目标；公式一旦发布不得在同一 id 下修改。"""

    @property
    @abstractmethod
    def info(self) -> SystemObjectiveInfo: ...

    @property
    def id(self) -> str:
        return self.info.id

    @abstractmethod
    def evaluate(self, kpis: Mapping[str, float]) -> ObjectiveEvaluation:
        """kpis: KPI id → 数值（已按 Benchmark Protocol 聚合）。缺失输入时抛出 KeyError。"""


class NetworkThroughputMaxV01(SystemObjective):
    _INFO = SystemObjectiveInfo(
        id=NETWORK_THROUGHPUT_MAX_V0_1,
        version="0.1",
        direction=Direction.MAXIMIZE,
        name_zh="网络吞吐率最大化",
        name_en="Network Throughput Maximization",
        input_kpis=(NETWORK_THROUGHPUT_V0_1,),
        formula="J = NETWORK_THROUGHPUT_V0_1   (maximize)",
        unit="Mbps",
        required_experiment_type="system",
        required_capabilities=("system_simulation", "throughput", "channel_reuse"),
        description_zh="以网络吞吐率（全部 UE 吞吐率之和）为唯一目标；平均 / P5 UE 吞吐率作为次要 KPI 同时记录，不参与目标。",
        description_en=(
            "Single objective: network throughput (sum of UE throughputs). Average and P5 UE throughput are "
            "recorded as secondary KPIs and do not enter the objective."
        ),
        assumptions=("[A] Full buffer downlink traffic", "[A] KPI aggregated per SYSTEM_BENCHMARK protocol"),
        limitations=(
            "Maximizing sum throughput may reduce edge-user throughput; P5 change is always reported",
            "System simulation result, not measured network data",
        ),
        document="docs/objectives/network-throughput-max-v0.1.md",
    )

    @property
    def info(self) -> SystemObjectiveInfo:
        return self._INFO

    def evaluate(self, kpis: Mapping[str, float]) -> ObjectiveEvaluation:
        value = float(kpis[NETWORK_THROUGHPUT_V0_1])
        return ObjectiveEvaluation(
            objective_id=self._INFO.id, objective_version=self._INFO.version, value=value,
            components={NETWORK_THROUGHPUT_V0_1: value},
        )


class SystemObjectiveRegistry:
    def __init__(self) -> None:
        self._objectives: dict[str, SystemObjective] = {}

    def register(self, objective: SystemObjective) -> None:
        if objective.id in self._objectives:
            raise ValueError(f"System objective '{objective.id}' already registered")
        self._objectives[objective.id] = objective

    def get(self, objective_id: str) -> SystemObjective:
        try:
            return self._objectives[objective_id]
        except KeyError:
            raise ObjectiveNotFoundError(
                f"Unknown system objective '{objective_id}'. Available: {', '.join(sorted(self._objectives)) or '-'}"
            ) from None

    def list(self) -> list[SystemObjective]:
        return [self._objectives[k] for k in sorted(self._objectives)]


def default_system_objective_registry() -> SystemObjectiveRegistry:
    registry = SystemObjectiveRegistry()
    registry.register(NetworkThroughputMaxV01())
    return registry
