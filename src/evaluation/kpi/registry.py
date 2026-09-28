"""
KPI 注册表 / KPI registry.
"""

from __future__ import annotations

from .evaluators import (
    AverageUeThroughputEvaluator,
    NetworkKpiEvaluator,
    NetworkThroughputEvaluator,
    P5UeThroughputEvaluator,
    UeThroughputEvaluator,
)
from .models import KpiContext, KpiDefinition, KpiResult, UeThroughputInput


class KpiNotFoundError(KeyError):
    pass


class KpiRegistry:
    def __init__(self, ue_evaluator: UeThroughputEvaluator, network_evaluators: list[NetworkKpiEvaluator]) -> None:
        ids = [ue_evaluator.definition.id, *(e.definition.id for e in network_evaluators)]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate KPI ids: {ids}")
        self._ue = ue_evaluator
        self._network = list(network_evaluators)

    def definitions(self) -> list[KpiDefinition]:
        return [self._ue.definition, *(e.definition for e in self._network)]

    def get(self, metric_id: str) -> KpiDefinition:
        for d in self.definitions():
            if d.id == metric_id:
                return d
        raise KpiNotFoundError(metric_id)

    def evaluate(self, inputs: list[UeThroughputInput], context: KpiContext) -> list[KpiResult]:
        """先计算 UE 吞吐率，再由其样本计算全部网络级 KPI。"""
        ue_result = self._ue.evaluate(inputs, context)
        return [ue_result, *(e.evaluate(ue_result, context) for e in self._network)]


def default_kpi_registry() -> KpiRegistry:
    return KpiRegistry(
        UeThroughputEvaluator(),
        [NetworkThroughputEvaluator(), AverageUeThroughputEvaluator(), P5UeThroughputEvaluator()],
    )
