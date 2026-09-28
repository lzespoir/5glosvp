"""
系统级优化变量目录 / System-level optimization variables.

每个变量 = ParameterDefinition（值域 / 单位 / 来源）+ 如何作用于 SystemScenario。
affects_propagation = False 的变量可以在同一冻结信道实现上公平比较；
改变传播的变量（发射功率、天线下倾角等）不能复用信道，Day 6 不提供。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from optimization.errors import InvalidParameterSpaceError
from optimization.parameters import (
    ParameterBounds,
    ParameterDefinition,
    ParameterRole,
    ParameterType,
    ValueGeneration,
)
from system_simulation.models import SystemScenario

SCHEDULER_BETA = "scheduler_beta"


@dataclass(frozen=True)
class SystemParameter:
    definition: ParameterDefinition
    apply: Callable[[SystemScenario, float], SystemScenario]
    read: Callable[[SystemScenario], float]
    affects_propagation: bool
    # Grid Search 演示候选（工程演示值，不是标准或现网配置）
    recommended_values: tuple[float, ...]
    recommended_values_source: str


def _apply_beta(scenario: SystemScenario, value: float) -> SystemScenario:
    sim = scenario.simulation
    scheduler = sim.scheduler.model_copy(update={"beta": float(value)})
    return scenario.model_copy(update={"simulation": sim.model_copy(update={"scheduler": scheduler})}, deep=True)


def _read_beta(scenario: SystemScenario) -> float:
    return float(scenario.simulation.scheduler.beta)


SCHEDULER_BETA_PARAMETER = SystemParameter(
    definition=ParameterDefinition(
        id=SCHEDULER_BETA,
        name_zh="PF 调度折扣因子 β",
        name_en="PF Scheduler Discount Factor β",
        role=ParameterRole.OPTIMIZATION_VARIABLE,
        type=ParameterType.CONTINUOUS,
        unit="1",
        default=0.98,
        bounds=ParameterBounds(lower=0.0, upper=1.0, lower_inclusive=False, upper_inclusive=False),
        constraints=["0 < β < 1 (sionna.sys.PFSchedulerSUMIMO raises ValueError otherwise)"],
        value_generation=[ValueGeneration.ENUMERATED, ValueGeneration.ALGORITHM_GENERATED],
        source="Sionna 2.1.0 sionna.sys.PFSchedulerSUMIMO(beta=…), default 0.98",
        description_zh=(
            "比例公平调度中历史平均吞吐率的几何折扣因子：T_t = β·T_{t-1} + (1-β)·R_t。"
            "β 越大，历史记忆越长（约 1/(1-β) 个时隙），调度对短期速率波动越不敏感。只影响调度，不改变传播。"
        ),
        description_en=(
            "Geometric discount factor of the PF scheduler's time-averaged throughput: "
            "T_t = β·T_{t-1} + (1-β)·R_t. Larger β = longer memory (≈ 1/(1-β) slots). "
            "Affects scheduling only, not propagation."
        ),
    ),
    apply=_apply_beta,
    read=_read_beta,
    affects_propagation=False,
    recommended_values=(0.1, 0.3, 0.6, 0.9, 0.99),
    recommended_values_source=(
        "[A] Engineering demonstration grid; spans memory lengths ≈1–100 slots. "
        "0.0 is not allowed by the Sionna API, 0.1 is the lowest demo value."
    ),
)


class SystemParameterCatalog:
    def __init__(self, parameters: list[SystemParameter]) -> None:
        self._parameters = {p.definition.id: p for p in parameters}

    def get(self, parameter_id: str) -> SystemParameter:
        try:
            return self._parameters[parameter_id]
        except KeyError:
            raise InvalidParameterSpaceError(
                f"Unknown system parameter '{parameter_id}'. Available: {', '.join(sorted(self._parameters))}"
            ) from None

    def list(self) -> list[SystemParameter]:
        return [self._parameters[k] for k in sorted(self._parameters)]


def default_system_parameter_catalog() -> SystemParameterCatalog:
    return SystemParameterCatalog([SCHEDULER_BETA_PARAMETER])
