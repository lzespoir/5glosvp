"""
KPI 计算 / KPI evaluators.

KPI 只能在这里计算；API 与前端只展示结果。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .definitions import (
    AVG_UE_THROUGHPUT,
    BITS_PER_MEGABIT,
    NETWORK_THROUGHPUT,
    P5_PERCENTILE,
    P5_PERCENTILE_METHOD,
    P5_UE_THROUGHPUT,
    UE_THROUGHPUT,
)
from .models import KpiContext, KpiDefinition, KpiResult, UeThroughputInput

NO_UE_REASON = "场景中没有 active UE / No active UE in the population"


def _result(
    definition: KpiDefinition,
    context: KpiContext,
    *,
    sample_size: int,
    calculation_method: str,
    value: float | None = None,
    per_ue: dict[str, float] | None = None,
    unavailable_reason: str | None = None,
) -> KpiResult:
    return KpiResult(
        metric_id=definition.id,
        version=definition.version,
        name_zh=definition.name_zh,
        name_en=definition.name_en,
        unit=definition.unit,
        scope=definition.scope,
        available=unavailable_reason is None,
        value=value,
        per_ue=per_ue,
        unavailable_reason=unavailable_reason,
        sample_size=sample_size,
        calculation_method=calculation_method,
        source_experiment=context.source_experiment,
        backend=context.backend,
        scenario_id=context.scenario_id,
        seed=context.seed,
        source_type=context.source_type,
        measured=context.measured,
        assumptions=list(definition.assumptions),
        acceptance_kpi=definition.acceptance_kpi,
    )


def ue_throughput_mbps(item: UeThroughputInput) -> float:
    return item.decoded_bits / item.simulated_duration_s / BITS_PER_MEGABIT


class UeThroughputEvaluator:
    definition = UE_THROUGHPUT

    def evaluate(self, inputs: list[UeThroughputInput], context: KpiContext) -> KpiResult:
        method = "decoded_bits / simulated_duration_s / 1e6"
        if not inputs:
            return _result(self.definition, context, sample_size=0, calculation_method=method,
                           unavailable_reason=NO_UE_REASON)
        per_ue = {i.ue_id: ue_throughput_mbps(i) for i in inputs}
        return _result(self.definition, context, sample_size=len(per_ue), calculation_method=method, per_ue=per_ue)


class NetworkKpiEvaluator(ABC):
    """由 UE_THROUGHPUT_V0_1 的全部 UE 样本得到网络级 KPI。"""

    definition: KpiDefinition
    calculation_method: str

    @abstractmethod
    def aggregate(self, values: np.ndarray) -> float: ...

    def evaluate(self, ue_throughput: KpiResult, context: KpiContext) -> KpiResult:
        values = np.array(list((ue_throughput.per_ue or {}).values()), dtype=float)
        if not ue_throughput.available or values.size == 0:
            return _result(self.definition, context, sample_size=0, calculation_method=self.calculation_method,
                           unavailable_reason=ue_throughput.unavailable_reason or NO_UE_REASON)
        return _result(self.definition, context, sample_size=int(values.size),
                       calculation_method=self.calculation_method, value=float(self.aggregate(values)))


class NetworkThroughputEvaluator(NetworkKpiEvaluator):
    definition = NETWORK_THROUGHPUT
    calculation_method = "sum(T_u)"

    def aggregate(self, values: np.ndarray) -> float:
        return float(np.sum(values))


class AverageUeThroughputEvaluator(NetworkKpiEvaluator):
    definition = AVG_UE_THROUGHPUT
    calculation_method = "mean(T_u)"

    def aggregate(self, values: np.ndarray) -> float:
        return float(np.mean(values))


class P5UeThroughputEvaluator(NetworkKpiEvaluator):
    definition = P5_UE_THROUGHPUT
    calculation_method = f"numpy.percentile(T_u, {P5_PERCENTILE:g}, method='{P5_PERCENTILE_METHOD}')"

    def aggregate(self, values: np.ndarray) -> float:
        return float(np.percentile(values, P5_PERCENTILE, method=P5_PERCENTILE_METHOD))
