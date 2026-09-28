"""
评价缓存 / Evaluation cache.

cache key = 冻结评价上下文内容（UE / 信道 / 业务哈希、仿真时长、协议、调度 / 链路自适应 / 功控配置）
          + 参数配置 + 后端 id / 版本。
不同信道、不同 UE、不同协议的键必然不同，因此不会跨错误上下文复用。
失败的评价不缓存。
"""

from __future__ import annotations

from typing import Any

from algorithms import canonical_sha256
from optimization.models import CandidateStatus
from optimization.parameters import ParameterValue

from .models import CommonEvaluationContext, SystemOptimizationCandidate


def evaluation_cache_key(
    context: CommonEvaluationContext,
    parameters: dict[str, ParameterValue],
    backend_id: str,
    backend_version: str | None,
) -> str:
    material: dict[str, Any] = {
        "context": {
            "ue_population_sha256": context.ue_population.sha256,
            "channel_sha256": context.channel_realization.sha256,
            "traffic_sha256": context.traffic_realization.sha256,
            "simulation_horizon": context.simulation_horizon.model_dump(mode="json"),
            "benchmark_protocol": [context.benchmark_protocol_id, context.benchmark_protocol_version],
            "scheduler_config": context.scheduler_config,
            "link_adaptation_config": context.link_adaptation_config,
            "power_control_config": context.power_control_config,
            "scenario_version": context.scenario_version,
        },
        "parameters": {k: parameters[k] for k in sorted(parameters)},
        "backend": {"id": backend_id, "version": backend_version},
    }
    return canonical_sha256(material)


class EvaluationCache:
    def __init__(self) -> None:
        self._entries: dict[str, SystemOptimizationCandidate] = {}

    def get(self, key: str) -> SystemOptimizationCandidate | None:
        return self._entries.get(key)

    def put(self, key: str, candidate: SystemOptimizationCandidate) -> None:
        if candidate.status is CandidateStatus.EVALUATED and key not in self._entries:
            self._entries[key] = candidate

    def __len__(self) -> int:
        return len(self._entries)
