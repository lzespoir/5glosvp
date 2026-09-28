"""
真实 Sionna RT → SYS 系统级优化集成测试（3 个候选）/ Real Sionna system optimization integration test.

一次光线追踪冻结信道，基线与候选在同一 CommonEvaluationContext 下评估；
不断言哪个 β 更优（不以结果调参），只断言公平性、可追溯性与独立复核通过。
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from algorithms import default_algorithm_registry
from evaluation.kpi import default_kpi_registry
from optimization import OptimizationStatus
from optimization.models import CandidateStatus
from simulation.backends.system import default_system_registry
from system_helpers import TEST_PROTOCOL_ID, make_test_protocol, write_scenario
from system_optimization import (
    BenchmarkProtocolRegistry,
    FileSystemOptimizationStore,
    ParameterSpec,
    SystemOptimizationService,
    default_system_objective_registry,
    default_system_parameter_catalog,
)
from system_simulation import FileSystemExperimentStore, SystemExperimentService, SystemScenarioCatalog

REPO_ROOT = Path(__file__).resolve().parents[1]
_HEALTH = default_system_registry().get("sionna_system").factory().health_check()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.sionna,
    pytest.mark.skipif(not _HEALTH["available"], reason=f"Sionna SYS unavailable: {_HEALTH['errors']}"),
]

CANDIDATES = [0.3, 0.9, 0.99]
DEMO_BUDGET = 3


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sysopt")
    demo = SystemScenarioCatalog(REPO_ROOT / "configs" / "system").get("SYSTEM-DEMO-001")
    small = demo.model_dump(mode="json")
    small["ue_generator"]["count"] = 3
    write_scenario(tmp / "configs", **{**small, "scenario_id": "SYSTEM-OPT-IT-001"})
    experiments = SystemExperimentService(
        FileSystemExperimentStore(tmp / "system_experiments"), default_system_registry(),
        SystemScenarioCatalog(tmp / "configs"), default_kpi_registry(), "test", None,
    )
    service = SystemOptimizationService(
        experiments=experiments,
        store=FileSystemOptimizationStore(tmp / "system_optimizations"),
        algorithms=default_algorithm_registry(),
        objectives=default_system_objective_registry(),
        protocols=BenchmarkProtocolRegistry([make_test_protocol(simulation_slots=20)]),
        parameters=default_system_parameter_catalog(),
        git_commit="test",
        runner=lambda fn: fn(),
    )
    return tmp, service


@pytest.fixture(scope="module")
def run(env):
    tmp, service = env
    created = service.create("integration", "SYSTEM-OPT-IT-001", "grid_search", "NETWORK_THROUGHPUT_MAX_V0_1",
                             "scheduler_beta", CANDIDATES, TEST_PROTOCOL_ID)
    return tmp, service.get(created.optimization_id)


@pytest.fixture(scope="module")
def demo_run(env):
    tmp, service = env
    created = service.create_run(
        name="integration-demo", scenario_id="SYSTEM-OPT-IT-001", algorithm_id="research_demo_optimizer",
        objective_id="NETWORK_THROUGHPUT_MAX_V0_1",
        parameter_space=[ParameterSpec(id="scheduler_beta", type="continuous")],
        benchmark_protocol_id=TEST_PROTOCOL_ID, max_evaluations=DEMO_BUDGET,
    )
    return tmp, service.get(created.optimization_id)


def _verify(tmp: Path, script: str, opt_id: str) -> dict:
    out = tmp / f"verification-{opt_id}.json"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), opt_id,
         "--data-dir", str(tmp / "system_optimizations"), "--experiments-dir", str(tmp / "system_experiments"),
         "--out", str(out)],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_optimization_succeeds_with_all_candidates(run):
    _, record = run
    assert record.status is OptimizationStatus.SUCCEEDED, record.error
    assert record.backend_id == "sionna_system"
    assert [c.parameters["scheduler_beta"] for c in record.candidates] == CANDIDATES
    assert all(c.status is CandidateStatus.EVALUATED for c in [record.baseline, *record.candidates])
    assert record.best_candidate_id is not None and record.comparison is not None


def test_single_frozen_channel_shared_by_every_experiment(run):
    _, record = run
    ctx = record.evaluation_context
    assert record.fairness is not None and record.fairness.fair, record.fairness
    for c in [record.baseline, *record.candidates]:
        assert c.evaluation_context_id == ctx.context_id
        assert c.fairness.channel_sha256 == ctx.channel_realization.sha256
        assert c.fairness.channel_reused is True
        assert c.fairness.num_slots == 20


def test_baseline_value_candidate_reuses_baseline(run):
    _, record = run
    same = next(c for c in record.candidates if c.parameters == record.baseline_parameters)
    assert same.reused_baseline and same.experiment_ids == record.baseline.experiment_ids


def test_independent_verifier_passes(run):
    tmp, record = run
    assert _verify(tmp, "verify_system_optimization.py", record.optimization_id)["overall"] == "PASS"


def test_research_demo_runs_in_frozen_context(demo_run):
    _, record = demo_run
    assert record.status is OptimizationStatus.SUCCEEDED, record.error
    assert record.algorithm.algorithm_id == "research_demo_optimizer" and record.algorithm.learning_algorithm is False
    budget = record.evaluation_budget
    assert 1 <= budget.evaluations_used == len(record.candidates) <= DEMO_BUDGET
    assert record.algorithm_trace is not None and record.stop_reason is not None
    assert record.fairness is not None and record.fairness.fair, record.fairness


def test_research_demo_independent_verifier_passes(demo_run):
    tmp, record = demo_run
    report = _verify(tmp, "verify_algorithm_run.py", record.optimization_id)
    assert report["overall"] == "PASS" and report["algorithm"]["replay"]["mismatches"] == []
