"""
公共评价上下文与公平性检查 / Common evaluation context and fairness checks.

公平性证据取自每个候选实验的实际结果（UE 位置、后端由实际信道计算的平均增益、时隙数、后端版本），
而不是从请求参数复制。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from system_simulation.base import ChannelRealization
from system_simulation.models import (
    EvaluationContextLink,
    SystemExperimentRecord,
    SystemScenario,
    TrafficDemand,
    TrafficModelType,
)
from system_simulation.realization import hash_arrays, traffic_hash, ue_population_hash

from .models import (
    BenchmarkProtocol,
    ChannelRealizationRef,
    CommonEvaluationContext,
    FairnessCheck,
    FairnessEvidence,
    FairnessReport,
    SimulationHorizon,
    SystemOptimizationCandidate,
    TrafficRealization,
    UePopulation,
    UePopulationEntry,
    ue_population_id_for,
    utc_now,
)

CHANNEL_HASH_RULE = "sha256 over sorted array keys; per key: key utf-8, dtype str, JSON shape, C-order bytes"
TRAFFIC_REALIZATION_IDS = {TrafficModelType.FULL_BUFFER: "FULL_BUFFER_V0_1"}
# 调度参数中属于优化变量、允许在候选之间变化的键
VARIABLE_SCHEDULER_KEYS = frozenset({"beta"})


def scenario_version(scenario: SystemScenario) -> str:
    payload = json.dumps(scenario.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def apply_protocol(scenario: SystemScenario, protocol: BenchmarkProtocol) -> SystemScenario:
    """协议冻结仿真时长与 warm-up；场景其余字段不变。"""
    sim = scenario.simulation.model_copy(
        update={"num_slots": protocol.simulation_slots, "warmup_slots": protocol.warmup_slots}
    )
    return scenario.model_copy(update={"simulation": sim}, deep=True)


def build_context(
    *,
    context_id: str,
    channel_realization_id: str,
    base_scenario: SystemScenario,
    protocol_scenario: SystemScenario,
    channel: ChannelRealization,
    channel_path: Path,
    backend_id: str,
    backend_version: str | None,
    protocol: BenchmarkProtocol,
) -> CommonEvaluationContext:
    ue_hash = ue_population_hash(list(channel.ue_ids), list(channel.serving_cell_ids), channel.positions.tolist())
    traffic = protocol_scenario.traffic
    sim = protocol_scenario.simulation
    return CommonEvaluationContext(
        context_id=context_id,
        scenario_id=base_scenario.scenario_id,
        scenario_version=scenario_version(base_scenario),
        seed=base_scenario.seed,
        ue_population=UePopulation(
            ue_population_id=ue_population_id_for(ue_hash),
            sha256=ue_hash,
            generator=channel.metadata.get("ue_generation"),
            seed=base_scenario.ue_generator.seed if base_scenario.ue_generator else base_scenario.seed,
            ues=[UePopulationEntry(ue_id=u, serving_cell_id=c, position=[float(v) for v in p])
                 for u, c, p in zip(channel.ue_ids, channel.serving_cell_ids, channel.positions.tolist())],
        ),
        traffic_realization=TrafficRealization(
            traffic_realization_id=TRAFFIC_REALIZATION_IDS[traffic.type],
            sha256=traffic_hash(traffic),
            model=traffic.model_dump(mode="json"),
        ),
        channel_realization=ChannelRealizationRef(
            channel_realization_id=channel_realization_id,
            sha256=hash_arrays(channel.arrays),
            hash_rule=CHANNEL_HASH_RULE,
            artifact=channel_path.name,
            arrays={k: {"shape": list(v.shape), "dtype": str(v.dtype)} for k, v in channel.arrays.items()},
            size_bytes=channel_path.stat().st_size,
            source_scenario_id=base_scenario.scenario_id,
            seed=base_scenario.seed,
            provider=channel.provider,
            provider_versions=channel.provider_versions,
            propagation_fingerprint=channel.propagation_fingerprint,
            mean_channel_gain_db={u: float(g) for u, g in zip(channel.ue_ids, channel.mean_channel_gain_db)},
            created_at=utc_now(),
        ),
        simulation_horizon=SimulationHorizon(
            num_slots=sim.num_slots, warmup_slots=sim.warmup_slots, slot_duration_s=sim.slot_duration_s,
            measured_duration_s=sim.simulated_duration_s,
        ),
        backend_id=backend_id,
        backend_version=backend_version,
        scheduler_config=sim.scheduler.model_dump(mode="json"),
        link_adaptation_config=sim.link_adaptation.model_dump(mode="json"),
        power_control_config=sim.power_control.model_dump(mode="json"),
        benchmark_protocol_id=protocol.protocol_id,
        benchmark_protocol_version=protocol.version,
        created_at=utc_now(),
        metadata={"propagation_seconds": channel.metadata.get("propagation_seconds"),
                  "candidate_indices": channel.metadata.get("candidate_indices")},
    )


def context_link(context: CommonEvaluationContext) -> EvaluationContextLink:
    return EvaluationContextLink(
        evaluation_context_id=context.context_id,
        channel_realization_id=context.channel_realization_id,
        channel_sha256=context.channel_realization.sha256,
        ue_population_id=context.ue_population_id,
        traffic_realization_id=context.traffic_realization_id,
        benchmark_protocol_id=context.benchmark_protocol_id,
        benchmark_protocol_version=context.benchmark_protocol_version,
    )


def fairness_evidence(experiment: SystemExperimentRecord) -> FairnessEvidence:
    """从已成功的候选实验中读取实际评价条件。"""
    result, link = experiment.result, experiment.evaluation_context
    assert result is not None and link is not None
    ues = result.ue_results
    traffic = TrafficDemand.model_validate(experiment.provenance["traffic_model"])
    return FairnessEvidence(
        evaluation_context_id=link.evaluation_context_id,
        ue_population_sha256=ue_population_hash([u.ue_id for u in ues], [u.serving_cell_id for u in ues],
                                                [u.position for u in ues]),
        channel_realization_id=link.channel_realization_id,
        channel_sha256=link.channel_sha256,
        traffic_realization_id=TRAFFIC_REALIZATION_IDS[traffic.type],
        traffic_sha256=traffic_hash(traffic),
        num_slots=result.num_slots,
        warmup_slots=result.warmup_slots,
        backend_id=experiment.backend,
        backend_version=experiment.backend_version,
        channel_reused=result.channel_reused,
    )


def fairness_report(
    context: CommonEvaluationContext,
    evaluations: list[SystemOptimizationCandidate],
    experiments: dict[str, SystemExperimentRecord],
) -> FairnessReport:
    """基线与全部成功候选是否在同一冻结条件下评价（失败候选不参与比较，不计入）。"""
    evaluated = [c for c in evaluations if c.fairness is not None and not c.reused_baseline]
    ev = [c.fairness for c in evaluated if c.fairness is not None]
    ctx_gain = context.channel_realization.mean_channel_gain_db
    horizon = context.simulation_horizon

    def gains_match(exp_ids: list[str]) -> bool:
        for exp_id in exp_ids:
            result = experiments[exp_id].result
            if result is None or {u.ue_id: u.mean_channel_gain_db for u in result.ue_results} != ctx_gain:
                return False
        return True

    expected_config = {
        "scheduler": {k: v for k, v in context.scheduler_config.items() if k not in VARIABLE_SCHEDULER_KEYS | {"id"}},
        "link_adaptation": {k: v for k, v in context.link_adaptation_config.items() if k != "id"},
        "power_control": {k: v for k, v in context.power_control_config.items() if k != "id"},
    }

    def config_matches(exp_ids: list[str]) -> bool:
        """后端结果中报告的调度（β 除外）/ 链路自适应 / 功控参数与上下文一致。"""
        for exp_id in exp_ids:
            result = experiments[exp_id].result
            if result is None:
                return False
            for attr, expected in expected_config.items():
                reported = getattr(result, attr)
                if any(k in reported and reported[k] != v for k, v in expected.items()):
                    return False
        return True

    all_exp_ids = [e for c in evaluated for e in c.experiment_ids]
    n = len(ev)
    checks = [
        FairnessCheck(
            id="same_ue_population", label_zh="相同 UE 集合", label_en="Same UE Population",
            passed=n > 0 and all(e.ue_population_sha256 == context.ue_population.sha256 for e in ev),
            detail=f"{context.ue_population_id} sha256 {context.ue_population.sha256[:16]}… ({n} evaluations)",
        ),
        FairnessCheck(
            id="same_channel_realization", label_zh="相同信道实现", label_en="Same Channel Realization",
            passed=n > 0 and all(
                e.channel_realization_id == context.channel_realization_id
                and e.channel_sha256 == context.channel_realization.sha256 and e.channel_reused for e in ev
            ) and gains_match(all_exp_ids),
            detail=(f"{context.channel_realization_id} sha256 {context.channel_realization.sha256[:16]}…; "
                    "per-UE mean channel gain recomputed by the backend from the consumed channel matches"),
        ),
        FairnessCheck(
            id="same_traffic", label_zh="相同业务模型", label_en="Same Traffic Model",
            passed=n > 0 and all(e.traffic_realization_id == context.traffic_realization_id
                                 and e.traffic_sha256 == context.traffic_realization.sha256 for e in ev),
            detail=context.traffic_realization_id,
        ),
        FairnessCheck(
            id="same_simulation_horizon", label_zh="相同仿真时长", label_en="Same Simulation Horizon",
            passed=n > 0 and all(e.num_slots == horizon.num_slots and e.warmup_slots == horizon.warmup_slots
                                 for e in ev),
            detail=f"{horizon.num_slots} slots, warm-up {horizon.warmup_slots}",
        ),
        FairnessCheck(
            id="same_backend_version", label_zh="相同后端版本", label_en="Same Backend Version",
            passed=n > 0 and all(e.backend_id == context.backend_id and e.backend_version == context.backend_version
                                 for e in ev),
            detail=f"{context.backend_id} {context.backend_version}",
        ),
        FairnessCheck(
            id="only_variable_changed", label_zh="仅优化变量不同", label_en="Only Optimization Variable Changed",
            passed=n > 0 and config_matches(all_exp_ids),
            detail="scheduler (except β), link adaptation and power control identical to the context",
        ),
    ]
    return FairnessReport(fair=all(c.passed for c in checks), checks=checks)
