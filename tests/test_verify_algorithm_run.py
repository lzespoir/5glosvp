"""独立复核脚本 scripts/verify_algorithm_run.py：算法运行正常通过，篡改算法层可被发现。"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from algorithms import AlgorithmRecommendation, StopReason, default_algorithm_registry
from algorithms.examples.research_demo_optimizer import ResearchDemoOptimizer
from system_optimization import NETWORK_THROUGHPUT_MAX_V0_1, SCHEDULER_BETA, ParameterSpec

from system_helpers import TEST_PROTOCOL_ID, make_optimization_service

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ONLY_FAILURES = {"not_test_fixture"}


def _create(tmp_path, algorithm_id, space, budget=None, hyperparameters=None, algorithms=None):
    service = make_optimization_service(tmp_path, algorithms=algorithms)
    record = service.create_run(
        name="verify", scenario_id="SYSTEM-TEST-001", algorithm_id=algorithm_id,
        objective_id=NETWORK_THROUGHPUT_MAX_V0_1, parameter_space=space, benchmark_protocol_id=TEST_PROTOCOL_ID,
        algorithm_hyperparameters=hyperparameters, max_evaluations=budget,
    )
    return tmp_path, record.optimization_id


@pytest.fixture
def demo(tmp_path):
    return _create(tmp_path, "research_demo_optimizer", [ParameterSpec(id=SCHEDULER_BETA, type="continuous")])


def verify(tmp: Path, opt_id: str) -> dict:
    out = tmp / "verification.json"
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_algorithm_run.py"), opt_id,
         "--data-dir", str(tmp / "system_optimizations"), "--experiments-dir", str(tmp / "system_experiments"),
         "--out", str(out)],
        capture_output=True, text=True, check=False,
    )
    return json.loads(out.read_text(encoding="utf-8"))


def failed(report: dict) -> set[str]:
    return {c["check"] for c in report["checks"] if c["status"] == "FAIL"}


def edit(tmp: Path, opt_id: str, mutate, name: str = "optimization.json") -> None:
    path = tmp / "system_optimizations" / opt_id / ("" if name == "optimization.json" else "artifacts") / name
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_demo_run_passes_and_replays(demo):
    report = verify(*demo)
    assert failed(report) == FIXTURE_ONLY_FAILURES
    assert report["algorithm"]["algorithm_id"] == "research_demo_optimizer"
    replay = report["algorithm"]["replay"]
    assert replay["stop_reason"] == "converged" and replay["recommendation"] == {SCHEDULER_BETA: 0.99}
    assert replay["mismatches"] == [] and report["verification_is_not_acceptance"] is True
    names = {c["check"] for c in report["checks"]}
    assert {"algorithm.replay_suggestions", "algorithm.trace_best_so_far", "algorithm.cache_keys_recomputed",
            "algorithm.parameter_space_hash", "algorithm.algorithm_config_hash", "best_candidate_selection"} <= names


def test_budget_exhausted_run_passes(tmp_path):
    report = verify(*_create(tmp_path, "research_demo_optimizer",
                             [ParameterSpec(id=SCHEDULER_BETA, type="continuous", lower=0.2, upper=0.95)],
                             budget=2, hyperparameters={"initial_step": 0.1, "start_point": "center"}))
    assert failed(report) == FIXTURE_ONLY_FAILURES
    assert report["algorithm"]["stop_reason"] == "budget_exhausted"


def test_grid_search_run_passes(tmp_path):
    report = verify(*_create(tmp_path, "grid_search",
                             [ParameterSpec(id=SCHEDULER_BETA, type="discrete", choices=[0.3, 0.6, 0.9, 0.99])]))
    assert failed(report) == FIXTURE_ONLY_FAILURES
    assert "algorithm.replay_grid_search" in {c["check"] for c in report["checks"]}


class _Repeater(ResearchDemoOptimizer):
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


@pytest.fixture
def repeater(tmp_path):
    registry = default_algorithm_registry()
    registry.register(_Repeater)
    return _create(tmp_path, "repeater", [ParameterSpec(id=SCHEDULER_BETA, type="continuous")], algorithms=registry)


def test_cache_hit_run_passes(repeater):
    assert failed(verify(*repeater)) == FIXTURE_ONLY_FAILURES


def test_tampered_cache_source_is_detected(repeater):
    tmp, opt_id = repeater
    edit(tmp, opt_id, lambda d: d["candidates"][1].update(reused_candidate_id="CAND-003"))
    assert "algorithm.cache_hits_reuse_earlier_evaluation" in failed(verify(tmp, opt_id))


def test_tampered_trace_suggestion_is_detected(demo):
    tmp, opt_id = demo

    def mutate(d):
        d["algorithm_trace"]["rounds"][1]["suggestions"][0][SCHEDULER_BETA] = 0.5
    edit(tmp, opt_id, mutate)
    assert {"algorithm.replay_suggestions", "algorithm.trace_rounds"} <= failed(verify(tmp, opt_id))


def test_tampered_objective_breaks_replay(demo):
    tmp, opt_id = demo

    def mutate(d):
        d["candidates"][1]["objective"]["value"] = 0.0
        d["algorithm_trace"]["evaluations"][2]["objective"] = 0.0
    edit(tmp, opt_id, mutate)
    bad = failed(verify(tmp, opt_id))
    assert "CAND-002.objective" in bad and "algorithm.replay_suggestions" in bad


def test_tampered_hyperparameter_is_detected(demo):
    tmp, opt_id = demo

    def mutate(d):
        for target in (d["algorithm"]["hyperparameters"], d["algorithm_hyperparameters"],
                       d["algorithm_trace"]["hyperparameters"]):
            target["initial_step"] = 0.3
    edit(tmp, opt_id, mutate)
    assert "algorithm.algorithm_config_hash" in failed(verify(tmp, opt_id))


def test_tampered_parameter_space_is_detected(demo):
    tmp, opt_id = demo
    edit(tmp, opt_id, lambda d: d["parameter_space"]["parameters"][0]["bounds"].update(upper=0.9))
    bad = failed(verify(tmp, opt_id))
    assert {"algorithm.parameter_space_hash", "algorithm.candidates_in_parameter_space"} <= bad


def test_budget_overrun_is_detected(demo):
    tmp, opt_id = demo
    edit(tmp, opt_id, lambda d: d["evaluation_budget"].update(max_evaluations=3))
    bad = failed(verify(tmp, opt_id))
    assert "algorithm.budget_used" in bad and "candidate_count" in bad


def test_tampered_stop_reason_is_detected(demo):
    tmp, opt_id = demo
    edit(tmp, opt_id, lambda d: d.update(stop_reason="max_iterations"))
    assert "algorithm.stop_reason" in failed(verify(tmp, opt_id))


def test_learning_claim_is_detected(demo):
    tmp, opt_id = demo
    edit(tmp, opt_id, lambda d: d.update(learning_algorithm=True), name="algorithm-metadata.json")
    assert "algorithm.not_learning_not_deliverable_not_acceptance" in failed(verify(tmp, opt_id))


def test_verifier_imports_nothing_from_src():
    pattern = re.compile(
        r"^\s*(from|import)\s+(algorithms|evaluation|system_optimization|optimization|system_simulation|simulation"
        r"|evidence|experiments|api|sionna)\b",
        re.MULTILINE,
    )
    for script in ("verify_algorithm_run.py", "verify_system_optimization.py"):
        assert not pattern.search((REPO_ROOT / "scripts" / script).read_text(encoding="utf-8")), script
