"""Day 7 算法接入 × 系统级优化服务（FakeSystemBackend，同步 runner）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from algorithms import (
    AlgorithmCategory,
    AlgorithmCompatibilityError,
    AlgorithmRecommendation,
    CompatibilityCode,
    StopReason,
    default_algorithm_registry,
)
from algorithms.examples.research_demo_optimizer import RESEARCH_DEMO_ID, ResearchDemoOptimizer
from evidence import AcceptanceIneligibilityReason, VerificationStatus
from optimization import InvalidParameterSpaceError
from optimization.models import CandidateStatus, OptimizationStatus
from system_optimization import NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA, ParameterSpec, SystemOptimizationRecord
from system_optimization.cache import EvaluationCache, evaluation_cache_key
from system_optimization.service import select_best

from system_helpers import TEST_PROTOCOL_ID, make_optimization_service

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[1]
DAY6_REFERENCE = REPO / "reference" / "system_optimization" / "OPT-9A16123C" / "optimization.json"


def _continuous(lower=None, upper=None) -> list[ParameterSpec]:
    return [ParameterSpec(id=SCHEDULER_BETA, type="continuous", lower=lower, upper=upper)]


def _run_demo(tmp_path, budget=8, hyperparameters=None, algorithms=None, algorithm_id=RESEARCH_DEMO_ID,
              space=None):
    service = make_optimization_service(tmp_path, algorithms=algorithms)
    record = service.create_run(
        name="demo", scenario_id="SYSTEM-TEST-001", algorithm_id=algorithm_id, objective_id=NETWORK_THROUGHPUT_MAX_V0_1,
        parameter_space=space or _continuous(), benchmark_protocol_id=TEST_PROTOCOL_ID,
        algorithm_hyperparameters=hyperparameters, max_evaluations=budget,
    )
    return service, record


def _betas(record: SystemOptimizationRecord) -> list[float]:
    return [c.parameters[SCHEDULER_BETA] for c in record.candidates]


# ---------------------------------------------------------------------------
# Research Demo end-to-end (iterative suggest → evaluate → observe)
# ---------------------------------------------------------------------------


def test_research_demo_iterative_run(tmp_path):
    _, record = _run_demo(tmp_path)
    assert record.status is OptimizationStatus.SUCCEEDED, record.error
    # 假后端：网络吞吐率随 β 单调增大 → 0.99 最优，随后步长缩小直至收敛
    assert _betas(record) == [0.7, 0.99, 0.89, 0.94]
    assert [c.algorithm_round for c in record.candidates] == [1, 1, 2, 3]
    assert record.best_candidate_id == "CAND-002" and record.recommendation_matches_best is True
    assert record.stop_reason is StopReason.CONVERGED
    assert record.candidate_values == [] and record.parameter_space.parameters[0].type.value == "continuous"
    budget = record.evaluation_budget
    assert (budget.max_evaluations, budget.evaluations_used, budget.simulations_run, budget.cache_hits) == (8, 4, 4, 0)
    assert record.fairness.fair is True


def test_trace_persisted(tmp_path):
    service, record = _run_demo(tmp_path)
    stored = service.get(record.optimization_id)
    trace = stored.algorithm_trace
    assert trace.algorithm_id == RESEARCH_DEMO_ID and trace.sdk_version == "0.1"
    assert [e.candidate_id for e in trace.evaluations] == ["BASELINE", "CAND-001", "CAND-002", "CAND-003", "CAND-004"]
    assert [e.best_so_far_candidate_id for e in trace.evaluations] == ["BASELINE", "BASELINE", "CAND-002",
                                                                        "CAND-002", "CAND-002"]
    assert trace.rounds[0].state_after["last_decision"] == "move 0.9 → 0.99 (improved)"
    assert trace.stop_reason is StopReason.CONVERGED and trace.recommendation.parameters == {SCHEDULER_BETA: 0.99}
    _, path = service.resolve_artifact(record.optimization_id, "algorithm-trace.json")
    assert json.loads(path.read_text())["stop_reason"] == "converged"


def test_algorithm_provenance(tmp_path):
    _, record = _run_demo(tmp_path)
    info = record.algorithm
    assert info.algorithm_id == RESEARCH_DEMO_ID and info.algorithm_category is AlgorithmCategory.RESEARCH_DEMO
    assert info.learning_algorithm is False and info.project_research_deliverable is False
    assert info.sdk_version == "0.1" and info.auto_configured is True
    assert len(info.algorithm_config_hash) == 64 and info.parameter_space_hash == record.parameter_space.sha256()
    assert info.source_revision == {"type": "git_commit", "value": "test"}
    prov = record.provenance
    assert prov["algorithm"] == RESEARCH_DEMO_ID and prov["learning_algorithm"] is False
    assert prov["search_space_source"].startswith("[A] Engineering demonstration interval")
    assert record.optimizer_id == RESEARCH_DEMO_ID and record.optimizer_version == info.algorithm_version


def test_hyperparameters_recorded_and_budget_limits_run(tmp_path):
    _, record = _run_demo(tmp_path, budget=2, hyperparameters={"initial_step": 0.1})
    assert record.algorithm.auto_configured is False
    assert record.algorithm_hyperparameters["initial_step"] == 0.1
    assert len(record.candidates) == 2 and record.stop_reason is StopReason.BUDGET_EXHAUSTED


def test_grid_search_via_registry_keeps_day6_semantics(tmp_path):
    service = make_optimization_service(tmp_path)
    record = service.create("t", "SYSTEM-TEST-001", "grid_search", NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA,
                            [0.3, 0.6, 0.9, 0.99], TEST_PROTOCOL_ID)
    assert record.status is OptimizationStatus.SUCCEEDED
    assert _betas(record) == [0.3, 0.6, 0.9, 0.99] and record.stop_reason is StopReason.COMPLETED
    reused = record.candidates[2]
    assert reused.reused_baseline and reused.cache_hit and reused.reused_candidate_id == "BASELINE"
    assert reused.experiment_id == record.baseline.experiment_id
    assert record.evaluation_budget.max_evaluations == 4 and record.evaluation_budget.simulations_run == 3
    assert record.algorithm.algorithm_category is AlgorithmCategory.ENGINEERING_BASELINE
    assert record.recommendation_matches_best is None  # Grid Search 不给推荐，由平台选择


def test_incompatible_rejected_before_running(tmp_path):
    service = make_optimization_service(tmp_path)
    with pytest.raises(AlgorithmCompatibilityError) as err:
        service.create_run(name="x", scenario_id="SYSTEM-TEST-001", algorithm_id="grid_search",
                           objective_id=NETWORK_THROUGHPUT_MAX_V0_1, parameter_space=_continuous(),
                           benchmark_protocol_id=TEST_PROTOCOL_ID)
    assert err.value.code is CompatibilityCode.ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED
    with pytest.raises(AlgorithmCompatibilityError) as err:
        _run_demo(tmp_path / "b", budget=99)
    assert err.value.code is CompatibilityCode.INVALID_EVALUATION_BUDGET
    assert service.list()[1] == 0  # 没有创建任何运行


def test_search_bounds_validated(tmp_path):
    service = make_optimization_service(tmp_path)
    for lower, upper in ((0.0, 0.5), (0.2, 1.0), (0.6, 0.4)):
        with pytest.raises(InvalidParameterSpaceError):
            service.build_parameter_space(_continuous(lower, upper))
    with pytest.raises(InvalidParameterSpaceError):
        service.build_parameter_space([ParameterSpec(id=SCHEDULER_BETA, type="continuous", choices=[0.3])])
    space, _ = service.build_parameter_space(_continuous(0.2, 0.8))
    assert space.parameters[0].bounds.describe() == "[0.2, 0.8]"


def test_evidence_descriptor_not_acceptance(tmp_path):
    service, record = _run_demo(tmp_path)
    descriptor = service.evidence(record)
    assert descriptor.verification_status is VerificationStatus.PLATFORM_CHECKS_PASSED
    assert descriptor.acceptance_eligible is False and descriptor.verified is False
    assert {AcceptanceIneligibilityReason.SIMULATION_ONLY, AcceptanceIneligibilityReason.NOT_MEASURED,
            AcceptanceIneligibilityReason.NOT_HUAWEI_DATA, AcceptanceIneligibilityReason.UNCONFIRMED_ACCEPTANCE_KPI,
            AcceptanceIneligibilityReason.INTEGRATION_DEMO_ALGORITHM,
            AcceptanceIneligibilityReason.TEST_FIXTURE} <= set(descriptor.acceptance_reason)
    _, path = service.resolve_artifact(record.optimization_id, "evidence-descriptor.json")
    assert json.loads(path.read_text())["acceptance_eligible"] is False


def test_day6_reference_record_still_loads():
    record = SystemOptimizationRecord.model_validate_json(DAY6_REFERENCE.read_text(encoding="utf-8"))
    assert record.optimization_id == "OPT-9A16123C" and record.algorithm is None and record.algorithm_trace is None
    assert select_best(record, record.objective.direction).candidate_id == record.best_candidate_id == "CAND-002"


# ---------------------------------------------------------------------------
# §87 Cache / dedup
# ---------------------------------------------------------------------------


class _Repeater(ResearchDemoOptimizer):
    """一轮内重复建议相同参数（含基线值），验证平台去重。"""

    @classmethod
    def metadata(cls):
        return super().metadata().model_copy(update={"algorithm_id": "repeater", "hyperparameter_schema": []})

    def validate_problem(self, problem, hyperparameters):
        return []

    def initialize(self, problem, hyperparameters, incumbents):
        self._done = False

    def suggest(self, max_suggestions):
        return [{SCHEDULER_BETA: 0.5}, {SCHEDULER_BETA: 0.5}, {SCHEDULER_BETA: 0.9}]

    def observe(self, results):
        self._done = True

    def should_stop(self):
        return StopReason.COMPLETED if self._done else None

    def finalize(self):
        return AlgorithmRecommendation(parameters=None)

    def state_metadata(self):
        return {}


def test_duplicate_candidate_reuses_evaluation(tmp_path):
    registry = default_algorithm_registry()
    registry.register(_Repeater)
    service, record = _run_demo(tmp_path, algorithms=registry, algorithm_id="repeater")
    first, dup, base = record.candidates
    assert not first.cache_hit and first.status is CandidateStatus.EVALUATED
    assert dup.cache_hit and dup.reused_candidate_id == "CAND-001" and dup.experiment_id == first.experiment_id
    assert base.cache_hit and base.reused_baseline and base.reused_candidate_id == "BASELINE"
    assert dup.objective == first.objective and dup.evaluation_cache_key == first.evaluation_cache_key
    budget = record.evaluation_budget
    assert (budget.evaluations_used, budget.simulations_run, budget.cache_hits) == (3, 1, 2)
    experiments = {e.experiment_id for e in service.experiments.list(limit=100)[0]}
    assert len(experiments) == 2  # 只运行了基线 + 1 次仿真
    assert [e.cache_hit for e in record.algorithm_trace.evaluations] == [False, False, True, True]
    assert record.fairness.fair is True


def _context(tmp_path):
    _, record = _run_demo(tmp_path, budget=1)
    return record.evaluation_context


def test_cache_same_context(tmp_path):
    ctx = _context(tmp_path)
    a = evaluation_cache_key(ctx, {SCHEDULER_BETA: 0.5}, "fake_system", "fixture")
    assert a == evaluation_cache_key(ctx.model_copy(deep=True), {SCHEDULER_BETA: 0.5}, "fake_system", "fixture")
    assert a == evaluation_cache_key(ctx.model_copy(update={"context_id": "CTX-OTHER"}), {SCHEDULER_BETA: 0.5},
                                     "fake_system", "fixture")  # 内容相同 → 同一键


def test_cache_different_context_miss(tmp_path):
    ctx = _context(tmp_path)
    key = evaluation_cache_key(ctx, {SCHEDULER_BETA: 0.5}, "fake_system", "fixture")
    other_channel = ctx.model_copy(deep=True)
    other_channel.channel_realization.sha256 = "0" * 64
    other_ue = ctx.model_copy(deep=True)
    other_ue.ue_population.sha256 = "1" * 64
    other_protocol = ctx.model_copy(update={"benchmark_protocol_version": "0.2"})
    for changed in (other_channel, other_ue, other_protocol):
        assert evaluation_cache_key(changed, {SCHEDULER_BETA: 0.5}, "fake_system", "fixture") != key
    assert evaluation_cache_key(ctx, {SCHEDULER_BETA: 0.5}, "fake_system", "other-version") != key


def test_cache_different_parameter_miss(tmp_path):
    ctx = _context(tmp_path)
    assert evaluation_cache_key(ctx, {SCHEDULER_BETA: 0.5}, "b", "v") != evaluation_cache_key(
        ctx, {SCHEDULER_BETA: 0.500001}, "b", "v")
    cache = EvaluationCache()
    assert cache.get("missing") is None and len(cache) == 0
