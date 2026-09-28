"""
优化层单元测试：Objective / Grid Search / Store / Service（FakeBackend 测试夹具，不依赖 Sionna / GPU）。
"""

import json
import re
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pytest
import yaml

from experiments import ExperimentPurpose, ExperimentService, FileExperimentStore, ScenarioCatalog
from optimization import (
    CandidateEvaluator,
    FileOptimizationStore,
    InvalidParameterSpaceError,
    OptimizationService,
    OptimizationStatus,
    ParameterSpace,
    default_objective_registry,
    default_optimizer_registry,
)
from optimization.base import ObjectiveInputs
from optimization.models import (
    TX_POWER_PARAMETER,
    CandidateStatus,
    Direction,
    ObjectiveEvaluation,
    ObjectiveSpec,
    OptimizationCandidate,
    OptimizationProblem,
    OptimizationRecord,
    candidate_id_for,
    new_optimization_id,
    utc_now,
)
from optimization.objectives import PROPAGATION_UTILITY_V0_1, PropagationUtilityV01
from optimization.optimizers import GridSearchOptimizer
from optimization.service import build_comparison, derive_candidate_config
from simulation import ScenarioConfig
from simulation.fake_backend import FakeBackend
from simulation.registry import BackendDescriptor, BackendRegistry

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_CONFIG = REPO_ROOT / "configs" / "sionna_demo.yaml"
SPACE = [38.0, 40.0, 42.0, 44.0, 46.0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FixedEvaluator(CandidateEvaluator):
    """测试夹具：按 TX power 返回预设目标值，记录评价顺序。"""

    def __init__(self, values: Mapping[float, float]) -> None:
        self.values = values
        self.calls: list[float] = []

    def evaluate(self, parameters, iteration):
        power = parameters[TX_POWER_PARAMETER]
        self.calls.append(power)
        return OptimizationCandidate(
            candidate_id=candidate_id_for(iteration), iteration=iteration, parameters=dict(parameters),
            status=CandidateStatus.EVALUATED, experiment_id=f"EXP-{iteration:08X}",
            objective=ObjectiveEvaluation(objective_id="TEST", objective_version="0", value=self.values[power]),
        )


def _problem(space: list[float], direction: Direction = Direction.MAXIMIZE) -> OptimizationProblem:
    return OptimizationProblem(
        scenario_id="S", parameter_space=ParameterSpace(tx_power_dbm=space),
        objective=ObjectiveSpec(id="TEST", version="0", direction=direction),
        baseline_parameters={TX_POWER_PARAMETER: 44.0}, seed=1,
    )


def _candidate(cid: str, power: float, value: float, exp: str) -> OptimizationCandidate:
    return OptimizationCandidate(
        candidate_id=cid, iteration=0, parameters={TX_POWER_PARAMETER: power},
        status=CandidateStatus.EVALUATED, experiment_id=exp,
        objective=ObjectiveEvaluation(objective_id="T", objective_version="0", value=value),
    )


class _FailAtPower(FakeBackend):
    fail_power = 40.0

    def run(self, experiment_id=None):
        if self._config and self._config.transmitters[0].power_dbm == self.fail_power:
            self._fail_on_run = True
        return super().run(experiment_id)


def _write_scenario(configs: Path, scenario_id: str, backend: str, power: float | None = 44.0) -> None:
    data = yaml.safe_load(DEMO_CONFIG.read_text(encoding="utf-8"))
    data.update(scenario_id=scenario_id, backend=backend)
    data["transmitters"][0]["power_dbm"] = power
    (configs / f"{scenario_id.lower()}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _make(tmp_path: Path, max_candidates: int = 10):
    configs = tmp_path / "configs"
    configs.mkdir()
    _write_scenario(configs, "FAKE-OK-001", "fake")
    _write_scenario(configs, "FAKE-FAIL-001", "fake_failing")
    _write_scenario(configs, "FAKE-FLAKY-001", "fake_flaky")
    _write_scenario(configs, "FAKE-NOPOWER-001", "fake", power=None)
    registry = BackendRegistry()
    registry.register(BackendDescriptor("fake", "假后端", "Fake", FakeBackend, source_type="test_fixture"))
    registry.register(
        BackendDescriptor("fake_failing", "失败", "Failing", lambda: FakeBackend(fail_on_run=True), source_type="test_fixture")
    )
    registry.register(BackendDescriptor("fake_flaky", "部分失败", "Flaky", _FailAtPower, source_type="test_fixture"))
    exp_store = FileExperimentStore(tmp_path / "experiments")
    experiments = ExperimentService(exp_store, registry, ScenarioCatalog(configs))
    opt_store = FileOptimizationStore(tmp_path / "optimizations")
    service = OptimizationService(
        experiments, opt_store, default_optimizer_registry(), default_objective_registry(), max_candidates
    )
    return service, exp_store, opt_store


def _run(service: OptimizationService, space=SPACE, scenario_id="FAKE-OK-001", objective_params=None):
    return service.create_optimization(
        name="test", scenario_id=scenario_id, optimizer_id="grid_search",
        objective_id=PROPAGATION_UTILITY_V0_1, parameter_space=ParameterSpace(tx_power_dbm=space),
        objective_params=objective_params,
    )


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------


def test_objective_formula():
    sinr = np.array([[5.0, 0.0, -0.1], [np.nan, 12.0, -30.0]])  # ≥0 dB: 5, 0, 12 → 3 / 6
    objective = PropagationUtilityV01()
    ev = objective.evaluate(
        ObjectiveInputs(layers={"sinr": sinr}, parameters={TX_POWER_PARAMETER: 42.0},
                        parameter_bounds={TX_POWER_PARAMETER: (38.0, 46.0)}),
        {"lambda_power": 0.1},
    )
    assert ev.value == pytest.approx(0.5 - 0.1 * 0.5)
    assert ev.objective_id == "PROPAGATION_UTILITY_V0_1" and ev.objective_version == "0.1"


def test_objective_breakdown():
    ev = PropagationUtilityV01().evaluate(
        ObjectiveInputs(layers={"sinr": np.full((2, 2), 3.0)}, parameters={TX_POWER_PARAMETER: 46.0},
                        parameter_bounds={TX_POWER_PARAMETER: (38.0, 46.0)}),
        {},
    )
    c = ev.components
    assert c["sinr_coverage_ratio"] == 1.0 and c["covered_cells"] == 4 and c["num_cells"] == 4
    assert c["normalized_power_cost"] == 1.0 and c["lambda_power"] == 0.10
    assert c["sinr_threshold_db"] == 0.0 and c["power_cost_term"] == pytest.approx(0.1)
    assert ev.value == pytest.approx(c["sinr_coverage_ratio"] - c["power_cost_term"])


def test_objective_single_power_has_zero_cost():
    ev = PropagationUtilityV01().evaluate(
        ObjectiveInputs(layers={"sinr": np.zeros((1, 2))}, parameters={TX_POWER_PARAMETER: 44.0},
                        parameter_bounds={TX_POWER_PARAMETER: (44.0, 44.0)}),
        {},
    )
    assert ev.components["normalized_power_cost"] == 0.0


def test_objective_requires_sinr_layer():
    with pytest.raises(ValueError, match="sinr"):
        PropagationUtilityV01().evaluate(
            ObjectiveInputs(layers={"rss": np.zeros((1, 1))}, parameters={TX_POWER_PARAMETER: 44.0},
                            parameter_bounds={TX_POWER_PARAMETER: (38.0, 46.0)}),
            {},
        )


# ---------------------------------------------------------------------------
# Grid Search
# ---------------------------------------------------------------------------


def test_grid_search_selects_best():
    evaluator = _FixedEvaluator({38.0: 0.4, 40.0: 0.6, 42.0: 0.5})
    result = GridSearchOptimizer().optimize(_problem([38.0, 40.0, 42.0]), evaluator)
    best = next(c for c in result.candidates if c.candidate_id == result.best_candidate_id)
    assert best.parameters[TX_POWER_PARAMETER] == 40.0


def test_grid_search_minimize_direction():
    evaluator = _FixedEvaluator({38.0: 0.4, 40.0: 0.6, 42.0: 0.5})
    result = GridSearchOptimizer().optimize(_problem([38.0, 40.0, 42.0], Direction.MINIMIZE), evaluator)
    assert result.best_candidate_id == "CAND-001"


def test_grid_search_deterministic():
    values = {p: 0.1 * i for i, p in enumerate([46.0, 38.0, 42.0])}
    runs = []
    for _ in range(2):
        evaluator = _FixedEvaluator(values)
        result = GridSearchOptimizer().optimize(_problem([46.0, 38.0, 42.0]), evaluator)
        assert evaluator.calls == [46.0, 38.0, 42.0]  # 定义顺序，不打乱
        runs.append((result.best_candidate_id, [c.candidate_id for c in result.candidates]))
    assert runs[0] == runs[1] == ("CAND-003", ["CAND-001", "CAND-002", "CAND-003"])


def test_tie_breaker_lower_power():
    evaluator = _FixedEvaluator({46.0: 0.5, 40.0: 0.5, 44.0: 0.5})
    result = GridSearchOptimizer().optimize(_problem([46.0, 40.0, 44.0]), evaluator)
    best = next(c for c in result.candidates if c.candidate_id == result.best_candidate_id)
    assert best.parameters[TX_POWER_PARAMETER] == 40.0


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def test_negative_improvement_allowed():
    cmp = build_comparison(_candidate("BASELINE", 44, 0.6, "EXP-00000001"), _candidate("CAND-001", 38, 0.5, "EXP-00000002"))
    assert cmp.absolute_improvement == pytest.approx(-0.1)
    assert cmp.relative_improvement_percent == pytest.approx(-100 / 6)


def test_relative_improvement_zero_baseline():
    cmp = build_comparison(_candidate("BASELINE", 44, 0.0, "EXP-00000001"), _candidate("CAND-001", 38, 0.2, "EXP-00000002"))
    assert cmp.absolute_improvement == pytest.approx(0.2)
    assert cmp.relative_improvement_percent is None


# ---------------------------------------------------------------------------
# Scenario derivation
# ---------------------------------------------------------------------------


def test_candidate_scenario_immutable():
    base = ScenarioConfig.from_yaml(DEMO_CONFIG)
    snapshot = base.model_dump()
    a = derive_candidate_config(base, {TX_POWER_PARAMETER: 38.0})
    b = derive_candidate_config(base, {TX_POWER_PARAMETER: 46.0})
    assert base.model_dump() == snapshot
    assert a.transmitters[0].power_dbm == 38.0 and b.transmitters[0].power_dbm == 46.0
    assert a.transmitters[0] is not base.transmitters[0] and a.radio_map is not base.radio_map
    assert a.random_seed == b.random_seed == base.random_seed
    a.radio_map.cell_size[0] = 999.0
    assert base.radio_map.cell_size[0] != 999.0


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


def _record() -> OptimizationRecord:
    return OptimizationRecord(
        optimization_id=new_optimization_id(), name="x", status=OptimizationStatus.CREATED,
        scenario_id="S", scenario_name_zh="场景", scenario_name_en="S", simulation_backend="fake",
        optimizer_id="grid_search",
        objective=ObjectiveSpec(id="T", version="0", direction=Direction.MAXIMIZE),
        parameter_space=ParameterSpace(tx_power_dbm=[38.0]),
        baseline_parameters={TX_POWER_PARAMETER: 44.0}, seed=1, created_at=utc_now(),
    )


def test_optimization_store_atomic_write(tmp_path, monkeypatch):
    store = FileOptimizationStore(tmp_path)
    record = store.create(_record())
    path = tmp_path / record.optimization_id / "optimization.json"
    assert path.is_file() and not list(tmp_path.rglob("*.tmp"))
    assert store.get(record.optimization_id) == record

    def _boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("os.replace", _boom)
    record.name = "changed"
    with pytest.raises(OSError):
        store.update(record)
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "x"  # 原文件未被半写入


def test_optimization_store_rejects_invalid_ids(tmp_path):
    store = FileOptimizationStore(tmp_path)
    assert store.get("../etc") is None and store.get("OPT-deadbeef") is None


# ---------------------------------------------------------------------------
# Service (FakeBackend)
# ---------------------------------------------------------------------------


def test_fake_optimization_end_to_end(tmp_path):
    service, exp_store, opt_store = _make(tmp_path)
    record = _run(service)
    assert record.status is OptimizationStatus.SUCCEEDED, record.error
    assert re.fullmatch(r"OPT-[0-9A-F]{8}", record.optimization_id)
    assert record.baseline and record.baseline.is_baseline and record.baseline.parameters == {TX_POWER_PARAMETER: 44.0}
    assert [c.parameters[TX_POWER_PARAMETER] for c in record.candidates] == SPACE
    assert [c.candidate_id for c in record.candidates] == [f"CAND-{i:03d}" for i in range(1, 6)]

    best = next(c for c in record.candidates if c.candidate_id == record.best_candidate_id)
    values = [c.objective.value for c in record.candidates]
    assert best.objective.value == max(values)
    cmp = record.comparison
    assert cmp.baseline_experiment_id == record.baseline.experiment_id
    assert cmp.optimized_experiment_id == best.experiment_id
    assert cmp.absolute_improvement == pytest.approx(best.objective.value - record.baseline.objective.value)

    prov = record.provenance
    assert prov["optimizer"] == "grid_search" and prov["learning_algorithm"] is False
    assert prov["optimizer_category"] == "engineering_baseline"
    assert prov["source_type"] == "test_fixture" and prov["measured"] is False
    assert prov["objective_id"] == PROPAGATION_UTILITY_V0_1 and prov["objective_version"] == "0.1"
    assert record.runtime.total_seconds >= record.runtime.candidate_evaluation_seconds
    assert [e.event for e in record.events][0] == "optimization_created"
    assert [e.event for e in record.events][-2:] == ["best_candidate_selected", "optimization_completed"]
    assert opt_store.get(record.optimization_id) == record


def test_baseline_reuse(tmp_path):
    service, exp_store, _ = _make(tmp_path)
    record = _run(service)
    reused = [c for c in record.candidates if c.reused_baseline]
    assert len(reused) == 1 and reused[0].parameters[TX_POWER_PARAMETER] == 44.0
    assert reused[0].experiment_id == record.baseline.experiment_id
    assert reused[0].objective == record.baseline.objective
    experiments = exp_store.list(limit=100)
    assert len(experiments) == 5  # baseline + 4 个新候选（44 dBm 复用基线）
    purposes = sorted(e.purpose.value for e in experiments)
    assert purposes == ["optimization_baseline"] + ["optimization_candidate"] * 4
    assert all(e.optimization_id == record.optimization_id for e in experiments)


def test_same_seed_for_all_candidates(tmp_path):
    service, exp_store, _ = _make(tmp_path)
    record = _run(service)
    seeds = {e.config["random_seed"] for e in exp_store.list(limit=100)}
    assert seeds == {record.seed}
    powers = sorted(e.config["transmitters"][0]["power_dbm"] for e in exp_store.list(limit=100))
    assert powers == [38.0, 40.0, 42.0, 44.0, 46.0]


def test_original_scenario_not_mutated(tmp_path):
    service, _, _ = _make(tmp_path)
    before = service.experiments.get_scenario("FAKE-OK-001").model_dump()
    _run(service)
    assert service.experiments.get_scenario("FAKE-OK-001").model_dump() == before


def test_objective_lambda_override_recorded(tmp_path):
    service, _, _ = _make(tmp_path)
    record = _run(service, space=[38.0, 46.0], objective_params={"lambda_power": 0.0})
    assert record.objective.params == {"lambda_power": 0.0}
    assert all(c.objective.components["lambda_power"] == 0.0 for c in record.candidates)


def test_candidate_limit(tmp_path):
    service, exp_store, opt_store = _make(tmp_path)
    with pytest.raises(InvalidParameterSpaceError, match="Too many"):
        _run(service, space=[float(p) for p in range(20, 31)])
    assert opt_store.count() == 0 and exp_store.count() == 0


def test_parameter_space_rejects_out_of_range(tmp_path):
    service, _, _ = _make(tmp_path)
    with pytest.raises(InvalidParameterSpaceError, match="out of range"):
        _run(service, space=[44.0, 500.0])


def test_baseline_requires_explicit_power(tmp_path):
    service, _, _ = _make(tmp_path)
    with pytest.raises(InvalidParameterSpaceError, match="explicit power_dbm"):
        _run(service, scenario_id="FAKE-NOPOWER-001")


def test_optimization_failure_persisted(tmp_path):
    service, _, opt_store = _make(tmp_path)
    record = _run(service, scenario_id="FAKE-FAIL-001")
    assert record.status is OptimizationStatus.FAILED
    assert record.error.code.value == "OPTIMIZATION_FAILED"
    assert record.error.failed_candidate_id == "BASELINE"
    assert record.baseline.status is CandidateStatus.FAILED and record.baseline.experiment_id
    assert record.baseline.error.code == "SIMULATION_FAILED"
    assert record.candidates == [] and record.comparison is None
    assert opt_store.get(record.optimization_id).status is OptimizationStatus.FAILED


def test_candidate_failure_keeps_completed_candidates(tmp_path):
    service, _, _ = _make(tmp_path)
    record = _run(service, scenario_id="FAKE-FLAKY-001")  # 40 dBm 失败
    assert record.status is OptimizationStatus.FAILED
    assert [c.status for c in record.candidates] == [CandidateStatus.EVALUATED, CandidateStatus.FAILED]
    assert record.error.failed_candidate_id == "CAND-002"
    assert record.error.experiment_id == record.candidates[1].experiment_id
    assert record.best_candidate_id is None and record.events[-1].event == "optimization_failed"


def test_experiment_records_link_back(tmp_path):
    service, exp_store, _ = _make(tmp_path)
    record = _run(service, space=[38.0])
    baseline_exp = exp_store.get(record.baseline.experiment_id)
    assert baseline_exp.purpose is ExperimentPurpose.OPTIMIZATION_BASELINE
    assert baseline_exp.optimization_id == record.optimization_id


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------


def test_optimizer_does_not_require_sionna():
    """Optimizer / Objective 不得依赖仿真引擎或实验服务；优化层整体不得 import Sionna。"""
    engine = re.compile(r"^\s*(from|import)\s+(sionna|mitsuba|drjit|simulation\.backends)\b", re.M)
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for p in (REPO_ROOT / "src" / "optimization").rglob("*.py")
        if engine.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders

    layered = re.compile(r"^\s*(from|import)\s+(simulation|experiments|api)\b", re.M)
    pure = [REPO_ROOT / "src" / "optimization" / d for d in ("optimizers", "objectives")]
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for d in pure
        for p in d.rglob("*.py")
        if layered.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


def test_grid_search_identity_is_not_learning():
    info = GridSearchOptimizer().info
    assert (info.id, info.name_en, info.name_zh) == ("grid_search", "Grid Search", "网格搜索")
    assert info.category == "engineering_baseline" and info.learning_algorithm is False
