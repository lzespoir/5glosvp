"""Day 6 系统级优化单元测试（FakeSystemBackend，确定性）。"""

from __future__ import annotations

import json
import logging

import pytest

from algorithms.builtin import GridSearchAlgorithm
from optimization import (
    InvalidParameterSpaceError,
    ObjectiveNotFoundError,
    ParameterBounds,
    ParameterDefinition,
    ParameterRole,
    ParameterType,
    ValueGeneration,
)
from optimization.models import CandidateStatus, Direction, ObjectiveEvaluation, OptimizationStatus
from system_optimization import (
    NETWORK_THROUGHPUT_MAX_V0_1,
    SCHEDULER_BETA,
    NetworkThroughputMaxV01,
    SystemOptimizationBusyError,
    SystemOptimizationCandidate,
    SystemOptimizationRecord,
    UnsupportedProblemTypeError,
)
from system_optimization.context import apply_protocol, build_context, fairness_report
from system_optimization.models import (
    AggregationMethod,
    CommonEvaluationContext,
    KpiStatistic,
    SystemOptimizationStage,
)
from system_optimization.parameters import SCHEDULER_BETA_PARAMETER
from system_optimization.service import build_system_comparison, relative_change
from system_simulation import Capability, InvalidSystemScenarioError, SystemCapabilityNotSupportedError
from system_simulation.fake_backend import FakeSystemBackend
from system_simulation.models import SystemExperimentPurpose, SystemExperimentStatus
from system_simulation.realization import (
    hash_arrays,
    load_channel,
    propagation_fingerprint,
    save_channel,
    ue_population_hash,
)

from system_helpers import (
    TEST_PROTOCOL_ID,
    fake_registry,
    make_optimization_service,
    make_scenario,
    make_test_protocol,
)

pytestmark = pytest.mark.unit

LOG = logging.getLogger("test")
CANDIDATES = [0.3, 0.6, 0.9, 0.99]


def _run(tmp_path, values=CANDIDATES, **kwargs):
    service = make_optimization_service(tmp_path, **kwargs)
    record = service.create("t", "SYSTEM-TEST-001", "grid_search", NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA,
                            list(values), TEST_PROTOCOL_ID)
    return service, record


def _context(tmp_path) -> tuple[CommonEvaluationContext, object]:
    scenario = make_scenario()
    protocol = make_test_protocol()
    ps = apply_protocol(scenario, protocol)
    channel = FakeSystemBackend().realize_channel(ps, LOG)
    path = save_channel(tmp_path, channel)
    ctx = build_context(context_id="CTX-00000001", channel_realization_id="CH-00000001", base_scenario=scenario,
                        protocol_scenario=ps, channel=channel, channel_path=path, backend_id="fake_system",
                        backend_version="fixture", protocol=protocol)
    return ctx, channel


# ---------------------------------------------------------------------------
# §73 Evaluation context
# ---------------------------------------------------------------------------


def test_evaluation_context_creation(tmp_path):
    ctx, _ = _context(tmp_path)
    assert ctx.context_id == "CTX-00000001"
    assert ctx.scenario_id == "SYSTEM-TEST-001" and ctx.seed == 7
    assert ctx.simulation_horizon.num_slots == 10 and ctx.simulation_horizon.warmup_slots == 0
    assert ctx.benchmark_protocol_id == TEST_PROTOCOL_ID
    assert ctx.backend_id == "fake_system" and len(ctx.scenario_version) == 64


def test_ue_population_frozen(tmp_path):
    _, record = _run(tmp_path)
    ctx = record.evaluation_context
    assert len(ctx.ue_population.ues) == 4
    assert ctx.ue_population_id.startswith("UEP-")
    for c in record.all_evaluations():
        assert c.fairness.ue_population_sha256 == ctx.ue_population.sha256


def test_channel_realization_frozen(tmp_path):
    service, record = _run(tmp_path)
    ctx = record.evaluation_context
    ids = {c.fairness.channel_realization_id for c in record.all_evaluations()}
    assert ids == {ctx.channel_realization_id}
    for c in record.all_evaluations():
        for exp_id in c.experiment_ids:
            exp = service.experiments.get(exp_id)
            assert exp.result.channel_reused is True
            assert {u.ue_id: u.mean_channel_gain_db for u in exp.result.ue_results} == \
                ctx.channel_realization.mean_channel_gain_db


def test_traffic_frozen(tmp_path):
    _, record = _run(tmp_path)
    ctx = record.evaluation_context
    assert ctx.traffic_realization_id == "FULL_BUFFER_V0_1"
    assert {c.fairness.traffic_sha256 for c in record.all_evaluations()} == {ctx.traffic_realization.sha256}


def test_context_hashes(tmp_path):
    ctx, channel = _context(tmp_path)
    assert ctx.channel_realization.sha256 == hash_arrays(channel.arrays)
    loaded = load_channel(tmp_path / "channel.npz", channel.provider, channel.provider_versions,
                          channel.propagation_fingerprint, {})
    assert hash_arrays(loaded.arrays) == ctx.channel_realization.sha256
    assert ctx.ue_population.sha256 == ue_population_hash(
        list(channel.ue_ids), list(channel.serving_cell_ids), channel.positions.tolist())
    changed = {k: v.copy() for k, v in channel.arrays.items()}
    changed["gain_linear"][0] *= 1.0001
    assert hash_arrays(changed) != ctx.channel_realization.sha256


def test_context_serialization(tmp_path):
    ctx, _ = _context(tmp_path)
    again = CommonEvaluationContext.model_validate_json(ctx.model_dump_json())
    assert again == ctx
    assert json.loads(ctx.model_dump_json())["channel_realization"]["hash_rule"].startswith("sha256")


def test_channel_reuse_rejected_for_different_propagation(tmp_path):
    scenario = make_scenario()
    channel = FakeSystemBackend().realize_channel(scenario, LOG)
    moved = make_scenario(base_stations=[{"bs_id": "BS-001", "position": [5.0, 0.0, 30.0]}])
    assert propagation_fingerprint(moved) != channel.propagation_fingerprint
    with pytest.raises(InvalidSystemScenarioError):
        FakeSystemBackend().run(moved, "EXP-00000000", LOG, channel=channel)


def test_scheduler_change_keeps_propagation_fingerprint():
    scenario = make_scenario()
    assert propagation_fingerprint(SCHEDULER_BETA_PARAMETER.apply(scenario, 0.3)) == propagation_fingerprint(scenario)


def test_warmup_excluded_from_aggregation():
    scenario = make_scenario(simulation={"num_slots": 10, "warmup_slots": 4})
    out = FakeSystemBackend().run(scenario, "EXP-00000000", LOG)
    ue = out.result.ue_results[0]
    assert ue.simulated_duration_s == pytest.approx(6 * 0.5e-3)
    assert ue.decoded_bits == int(out.slot_trace["decoded_bits"][4:, 0].sum())
    with pytest.raises(ValueError):
        make_scenario(simulation={"num_slots": 10, "warmup_slots": 10})


# ---------------------------------------------------------------------------
# §74 Parameter definition
# ---------------------------------------------------------------------------


def _param(**overrides):
    base = dict(id="p", name_zh="p", name_en="p", role=ParameterRole.OPTIMIZATION_VARIABLE, unit="1", source="test")
    base.update(overrides)
    return ParameterDefinition(**base)


def test_discrete_parameter():
    p = _param(type=ParameterType.DISCRETE, choices=[0.3, 0.6])
    assert p.validate_value(0.6) == 0.6
    with pytest.raises(ValueError):
        p.validate_value(0.5)


def test_continuous_parameter_schema():
    p = _param(type=ParameterType.CONTINUOUS, bounds=ParameterBounds(lower=0, upper=1, lower_inclusive=False,
                                                                       upper_inclusive=False))
    assert p.validate_value(0.734) == 0.734
    for bad in (0.0, 1.0, float("nan")):
        with pytest.raises(ValueError):
            p.validate_value(bad)
    with pytest.raises(ValueError):
        _param(type=ParameterType.CONTINUOUS)


def test_invalid_bounds():
    with pytest.raises(ValueError):
        ParameterBounds(lower=1.0, upper=0.5)
    with pytest.raises(ValueError):
        ParameterBounds(lower=0.0, upper=float("inf"))


def test_invalid_choice():
    with pytest.raises(ValueError):
        _param(type=ParameterType.CONTINUOUS, bounds=ParameterBounds(lower=0, upper=1), choices=[2.0])
    cat = _param(type=ParameterType.CATEGORICAL, choices=["pf", "rr"])
    with pytest.raises(ValueError):
        cat.validate_value("max_cqi")
    with pytest.raises(ValueError):
        _param(type=ParameterType.INTEGER, bounds=ParameterBounds(lower=0, upper=10)).validate_value(2.5)


def test_parameter_unit():
    d = SCHEDULER_BETA_PARAMETER.definition
    assert d.unit == "1" and d.type is ParameterType.CONTINUOUS
    assert d.bounds.describe() == "(0, 1)"
    assert _param(type=ParameterType.VECTOR, unit="deg", vector_length=2,
                  bounds=ParameterBounds(lower=-90, upper=90)).validate_value([1, 2]) == [1.0, 2.0]


def test_algorithm_generated_future_schema():
    d = SCHEDULER_BETA_PARAMETER.definition
    assert ValueGeneration.ALGORITHM_GENERATED in d.value_generation
    assert d.choices is None  # 值域由 bounds 定义，不写死为枚举
    assert d.validate_value(0.734) == 0.734
    assert d.role is ParameterRole.OPTIMIZATION_VARIABLE


def test_hyperparameters_separate_from_variables(tmp_path):
    service = make_optimization_service(tmp_path)
    grid, demo = service.list_optimizers()
    assert grid.hyperparameter_schema == []
    assert {h.id for h in demo.hyperparameter_schema} >= {"initial_step", "min_step", "max_iterations"}
    assert all(p.definition.role is ParameterRole.OPTIMIZATION_VARIABLE for p in service.list_parameters())


# ---------------------------------------------------------------------------
# §75 System objective
# ---------------------------------------------------------------------------


def _cand(cid, value, net, avg=None, p5=None, it=1, baseline=False):
    stat = lambda v: KpiStatistic(mean=v, std=0, min=v, max=v, n=1)  # noqa: E731
    return SystemOptimizationCandidate(
        candidate_id=cid, iteration=it, parameters={SCHEDULER_BETA: value}, status=CandidateStatus.EVALUATED,
        experiment_id=f"EXP-{it:08d}", is_baseline=baseline,
        objective=ObjectiveEvaluation(objective_id=NETWORK_THROUGHPUT_MAX_V0_1, objective_version="0.1", value=net),
        network_throughput_mbps=stat(net), average_ue_throughput_mbps=stat(avg if avg is not None else net / 4),
        p5_ue_throughput_mbps=stat(p5 if p5 is not None else net / 10),
    )


def test_network_throughput_objective():
    ev = NetworkThroughputMaxV01().evaluate({"NETWORK_THROUGHPUT_V0_1": 123.5, "P5_UE_THROUGHPUT_V0_1": 1.0})
    assert ev.value == 123.5 and ev.components == {"NETWORK_THROUGHPUT_V0_1": 123.5}
    with pytest.raises(KeyError):
        NetworkThroughputMaxV01().evaluate({"P5_UE_THROUGHPUT_V0_1": 1.0})


def test_objective_direction_maximize():
    assert NetworkThroughputMaxV01().info.direction is Direction.MAXIMIZE


def test_objective_version():
    info = NetworkThroughputMaxV01().info
    assert (info.id, info.version) == ("NETWORK_THROUGHPUT_MAX_V0_1", "0.1")
    assert info.acceptance_kpi is False and info.measured_data is False and info.huawei_data is False
    assert info.input_kpis == ("NETWORK_THROUGHPUT_V0_1",)


def test_zero_baseline_relative_improvement():
    assert relative_change(0.0, 5.0) is None
    c = build_system_comparison(_cand("BASELINE", 0.9, 0.0, 0.0, 0.0, it=0, baseline=True),
                                _cand("CAND-001", 0.3, 5.0), Direction.MAXIMIZE, 1.0)
    assert c.relative_improvement_percent is None and c.absolute_improvement == 5.0


def test_negative_improvement():
    c = build_system_comparison(_cand("BASELINE", 0.9, 100.0, 25.0, 10.0, it=0, baseline=True),
                                _cand("CAND-001", 0.3, 104.0, 26.0, 8.0), Direction.MAXIMIZE, 1.0)
    assert c.improved and c.relative_improvement_percent == pytest.approx(4.0)
    p5 = next(k for k in c.kpi_changes if k.kpi_id == "P5_UE_THROUGHPUT_V0_1")
    assert p5.direction == "decrease" and p5.relative_change_percent == pytest.approx(-20.0)
    assert c.negative_kpi_changes == ["P5_UE_THROUGHPUT_V0_1"]
    worse = build_system_comparison(_cand("BASELINE", 0.9, 100.0, it=0, baseline=True),
                                    _cand("CAND-001", 0.3, 90.0), Direction.MAXIMIZE, 1.0)
    assert not worse.improved and worse.relative_improvement_percent == pytest.approx(-10.0)


def test_within_observed_variability_flag():
    c = build_system_comparison(_cand("BASELINE", 0.9, 100.0, it=0, baseline=True), _cand("CAND-001", 0.3, 100.5),
                                Direction.MAXIMIZE, 1.0)
    assert c.improved and c.within_observed_variability
    c2 = build_system_comparison(_cand("BASELINE", 0.9, 100.0, it=0, baseline=True), _cand("CAND-001", 0.3, 105.0),
                                 Direction.MAXIMIZE, 1.0)
    assert not c2.within_observed_variability


def test_tie_break(tmp_path):
    # 所有 β 产生相同吞吐率 → 基线胜出（基线值优先）
    _, record = _run(tmp_path, [0.3, 0.6], registry=fake_registry(bits_scale=lambda s, i: 1.0))
    assert record.best_candidate_id == "BASELINE"
    assert record.comparison.tie_break_rule.startswith("Equal objective")
    # 候选之间相同且优于基线 → 候选顺序在前者胜出
    scale = lambda s, i: 1.0 if s.simulation.scheduler.beta == 0.9 else 2.0  # noqa: E731
    _, record = _run(tmp_path / "b", [0.3, 0.6], registry=fake_registry(bits_scale=scale))
    assert record.best_candidate_id == "CAND-001"


# ---------------------------------------------------------------------------
# §76 Optimization service
# ---------------------------------------------------------------------------


def test_baseline_same_context(tmp_path):
    service, record = _run(tmp_path)
    assert record.status is OptimizationStatus.SUCCEEDED
    assert record.baseline.evaluation_context_id == record.evaluation_context.context_id
    exp = service.experiments.get(record.baseline.experiment_id)
    assert exp.purpose is SystemExperimentPurpose.OPTIMIZATION_BASELINE
    assert exp.evaluation_context.evaluation_context_id == record.evaluation_context.context_id


def test_candidate_same_context(tmp_path):
    _, record = _run(tmp_path)
    assert {c.evaluation_context_id for c in record.candidates} == {record.evaluation_context.context_id}
    assert record.fairness.fair


def test_candidate_parameter_applied(tmp_path):
    service, record = _run(tmp_path)
    for c in record.candidates:
        exp = service.experiments.get(c.experiment_id)
        assert exp.result.scheduler["beta"] == c.parameters[SCHEDULER_BETA]
    assert record.baseline_parameters == {SCHEDULER_BETA: 0.9}


def test_candidate_experiment_created(tmp_path):
    service, record = _run(tmp_path)
    assert [c.candidate_id for c in record.candidates] == ["CAND-001", "CAND-002", "CAND-003", "CAND-004"]
    reused = [c for c in record.candidates if c.reused_baseline]
    assert [c.parameters[SCHEDULER_BETA] for c in reused] == [0.9]
    assert reused[0].experiment_id == record.baseline.experiment_id
    for c in record.candidates:
        exp = service.experiments.get(c.experiment_id)
        assert exp.status is SystemExperimentStatus.SUCCEEDED
        assert exp.optimization_id == record.optimization_id
        if not c.reused_baseline:
            assert exp.purpose is SystemExperimentPurpose.OPTIMIZATION_CANDIDATE
            assert exp.optimization_candidate_id == c.candidate_id


def test_best_candidate_selected(tmp_path):
    _, record = _run(tmp_path)
    assert record.best_candidate_id == "CAND-004"
    comp = record.comparison
    assert comp.improved and comp.best_parameters == {SCHEDULER_BETA: 0.99}
    assert comp.best_objective == max(c.objective.value for c in record.all_evaluations())
    assert comp.negative_kpi_changes == ["P5_UE_THROUGHPUT_V0_1"]
    assert any("P5_UE_THROUGHPUT_V0_1 decreased" in w for w in record.warnings)
    assert record.progress.stage is SystemOptimizationStage.COMPLETED
    assert record.progress.completed_candidates == record.progress.total_candidates == 4


def test_no_improvement(tmp_path):
    _, record = _run(tmp_path, [0.3, 0.6])
    assert record.status is OptimizationStatus.SUCCEEDED
    assert record.best_candidate_id == "BASELINE"
    assert record.comparison.improved is False and record.comparison.absolute_improvement == 0
    assert record.comparison.relative_improvement_percent == 0
    assert any("No candidate improved" in w for w in record.warnings)


def test_failed_candidate(tmp_path):
    service, record = _run(tmp_path, registry=fake_registry(fail_beta=0.6))
    assert record.status is OptimizationStatus.SUCCEEDED
    failed = next(c for c in record.candidates if c.parameters[SCHEDULER_BETA] == 0.6)
    assert failed.status is CandidateStatus.FAILED and failed.error.code == "SYSTEM_SIMULATION_FAILED"
    assert service.experiments.get(failed.experiment_id).status is SystemExperimentStatus.FAILED
    assert any("Failed candidates preserved: CAND-002" in w for w in record.warnings)


def test_partial_failure_policy(tmp_path):
    _, record = _run(tmp_path, registry=fake_registry(fail_beta=0.99))
    assert record.status is OptimizationStatus.SUCCEEDED
    assert len(record.candidates) == 4
    assert record.best_candidate_id == "BASELINE"  # 0.99 失败后不参与选择
    assert record.fairness.fair  # 失败候选不参与公平性比较


def test_failed_baseline(tmp_path):
    _, record = _run(tmp_path, registry=fake_registry(fail_beta=0.9))
    assert record.status is OptimizationStatus.FAILED
    assert record.error.code.value == "BASELINE_FAILED" and record.error.failed_candidate_id == "BASELINE"
    assert record.baseline.status is CandidateStatus.FAILED
    assert record.candidates == []


def test_all_candidates_failed(tmp_path):
    def scale(s, i):
        if s.simulation.scheduler.beta != 0.9:
            raise RuntimeError("boom")
        return 1.0

    _, record = _run(tmp_path, [0.3, 0.6], registry=fake_registry(bits_scale=scale))
    assert record.status is OptimizationStatus.FAILED
    assert record.error.code.value == "ALL_CANDIDATES_FAILED"
    assert len(record.candidates) == 2 and record.baseline.status is CandidateStatus.EVALUATED
    assert {a.name for a in record.artifacts} >= {"candidate-summary.json", "evaluation-context.json"}


def test_invalid_candidates_rejected(tmp_path):
    service = make_optimization_service(tmp_path)
    for values in ([0.0], [1.0], [0.3, 0.3], [], [0.1] * 9):
        with pytest.raises(InvalidParameterSpaceError):
            service.create("t", "SYSTEM-TEST-001", "grid_search", NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA,
                           values, TEST_PROTOCOL_ID)
    with pytest.raises(InvalidParameterSpaceError):
        service.create("t", "SYSTEM-TEST-001", "grid_search", NETWORK_THROUGHPUT_MAX_V0_1, "tx_power_dbm",
                       [40.0], TEST_PROTOCOL_ID)
    with pytest.raises(ObjectiveNotFoundError):
        service.create("t", "SYSTEM-TEST-001", "grid_search", "PROPAGATION_UTILITY_V0_1", SCHEDULER_BETA,
                       [0.3], TEST_PROTOCOL_ID)


def test_backend_without_channel_reuse_rejected(tmp_path):
    registry = fake_registry(capabilities=(Capability.SYSTEM_SIMULATION, Capability.THROUGHPUT))
    service = make_optimization_service(tmp_path, registry=registry)
    with pytest.raises(SystemCapabilityNotSupportedError):
        service.create("t", "SYSTEM-TEST-001", "grid_search", NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA,
                       [0.3], TEST_PROTOCOL_ID)


def test_optimizer_must_support_system_problems(tmp_path):
    service = make_optimization_service(tmp_path)
    grid = service.list_optimizers()[0]
    assert "system" in grid.supported_problem_types and grid.learning_algorithm is False
    service.algorithms.register(_PropagationOnly)
    with pytest.raises(UnsupportedProblemTypeError):
        service.create("t", "SYSTEM-TEST-001", "propagation_only", NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA,
                       [0.3], TEST_PROTOCOL_ID)


class _PropagationOnly(GridSearchAlgorithm):
    @classmethod
    def metadata(cls):
        return super().metadata().model_copy(update={"algorithm_id": "propagation_only",
                                                     "supported_problem_types": ["propagation"]})


def test_busy_rejected(tmp_path):
    service = make_optimization_service(tmp_path)
    service._busy.acquire()
    try:
        with pytest.raises(SystemOptimizationBusyError):
            service.create("t", "SYSTEM-TEST-001", "grid_search", NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA,
                           [0.3], TEST_PROTOCOL_ID)
    finally:
        service._busy.release()


def test_interrupted_run_marked_failed(tmp_path):
    service, record = _run(tmp_path, [0.3])
    record.status = OptimizationStatus.RUNNING
    service._store.update(record)
    again = make_optimization_service(tmp_path)
    assert again.get(record.optimization_id).error.code.value == "INTERRUPTED"


def test_evidence_artifacts(tmp_path):
    service, record = _run(tmp_path)
    names = {a.name for a in record.artifacts}
    assert names == {"evaluation-context.json", "benchmark-protocol.json", "candidate-summary.json",
                     "comparison.png", "per-ue-comparison.png", "algorithm-metadata.json", "parameter-space.json",
                     "algorithm-config.json", "algorithm-trace.json", "evidence-descriptor.json"}
    _, path = service.resolve_artifact(record.optimization_id, "candidate-summary.json")
    rows = json.loads(path.read_text())
    assert [r["candidate_id"] for r in rows][0] == "BASELINE" and sum(r["is_best"] for r in rows) == 1


def test_record_roundtrip(tmp_path):
    service, record = _run(tmp_path)
    assert SystemOptimizationRecord.model_validate_json(record.model_dump_json()) == record
    assert record.provenance["learning_algorithm"] is False and record.provenance["measured"] is False
    assert record.provenance["huawei_data"] is False and record.provenance["acceptance_evidence"] is False


def test_repeats_aggregated_with_statistics(tmp_path):
    protocol = make_test_protocol(num_repeats=2, aggregation_method=AggregationMethod.MEAN)
    _, record = _run(tmp_path, [0.3], protocol=protocol)
    base = record.baseline
    assert len(base.experiment_ids) == 2
    assert base.network_throughput_mbps.n == 2 and base.network_throughput_mbps.std == 0


# ---------------------------------------------------------------------------
# §79 Fairness
# ---------------------------------------------------------------------------


def _fair_inputs(tmp_path):
    service, record = _run(tmp_path)
    experiments = {e: service.experiments.get(e) for c in record.all_evaluations() for e in c.experiment_ids}
    return record, experiments


def _check(report, check_id):
    return next(c for c in report.checks if c.id == check_id).passed


def test_same_ue_hash(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    assert _check(record.fairness, "same_ue_population")
    record.candidates[0].fairness.ue_population_sha256 = "0" * 64
    assert not _check(fairness_report(record.evaluation_context, record.all_evaluations(), exps), "same_ue_population")


def test_same_channel_hash(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    assert _check(record.fairness, "same_channel_realization")
    record.candidates[1].fairness.channel_sha256 = "f" * 64
    report = fairness_report(record.evaluation_context, record.all_evaluations(), exps)
    assert not _check(report, "same_channel_realization") and not report.fair


def test_same_channel_requires_identical_gains(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    exp = exps[record.candidates[0].experiment_id]
    exp.result.ue_results[0].mean_channel_gain_db += 0.001
    assert not _check(fairness_report(record.evaluation_context, record.all_evaluations(), exps),
                      "same_channel_realization")


def test_same_traffic(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    assert _check(record.fairness, "same_traffic")
    record.candidates[0].fairness.traffic_sha256 = "1" * 64
    assert not _check(fairness_report(record.evaluation_context, record.all_evaluations(), exps), "same_traffic")


def test_same_slots(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    assert _check(record.fairness, "same_simulation_horizon")
    record.candidates[0].fairness.num_slots = 11
    assert not _check(fairness_report(record.evaluation_context, record.all_evaluations(), exps),
                      "same_simulation_horizon")


def test_backend_version_same(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    assert _check(record.fairness, "same_backend_version")
    record.candidates[0].fairness.backend_version = "other"
    assert not _check(fairness_report(record.evaluation_context, record.all_evaluations(), exps),
                      "same_backend_version")


def test_fairness_false_if_context_differs(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    other_ctx, _ = _context(tmp_path / "other")
    other_ctx = other_ctx.model_copy(update={"simulation_horizon": other_ctx.simulation_horizon.model_copy(
        update={"num_slots": 20})})
    report = fairness_report(other_ctx, record.all_evaluations(), exps)
    assert report.fair is False


def test_only_variable_changed(tmp_path):
    record, exps = _fair_inputs(tmp_path)
    assert _check(record.fairness, "only_variable_changed")
    exp = exps[record.candidates[0].experiment_id]
    exp.result.scheduler["beta"] = 0.123  # β 允许变化
    assert _check(fairness_report(record.evaluation_context, record.all_evaluations(), exps), "only_variable_changed")

