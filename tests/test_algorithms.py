"""Day 7 算法接入框架单元测试（不依赖仿真器）/ Algorithm integration framework unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from algorithms import (
    ALGORITHM_SDK_VERSION,
    Algorithm,
    AlgorithmCategory,
    AlgorithmDriver,
    AlgorithmExecutionError,
    AlgorithmNotFoundError,
    AlgorithmProblem,
    AlgorithmRecommendation,
    CompatibilityCode,
    EvaluationResult,
    EvaluationStatus,
    ParameterConstraint,
    ParameterSpace,
    StopReason,
    check_compatibility,
    default_algorithm_registry,
)
from algorithms.builtin import GridSearchAlgorithm
from algorithms.examples.research_demo_optimizer import RESEARCH_DEMO_ID, ResearchDemoOptimizer
from algorithms.sdk import HyperparameterDefinition, HyperparameterType
from optimization.models import Direction
from optimization.parameters import (
    ParameterBounds,
    ParameterDefinition,
    ParameterRole,
    ParameterType,
    VectorElementType,
)

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[1]


def _param(**overrides) -> ParameterDefinition:
    base = dict(id="beta", name_zh="β", name_en="beta", role=ParameterRole.OPTIMIZATION_VARIABLE, unit="1",
                source="test")
    base.update(overrides)
    return ParameterDefinition(**base)


def _continuous(lower=0.05, upper=0.99) -> ParameterDefinition:
    return _param(type=ParameterType.CONTINUOUS, bounds=ParameterBounds(lower=lower, upper=upper))


def _discrete(values=(0.3, 0.6, 0.9)) -> ParameterDefinition:
    return _param(type=ParameterType.DISCRETE, choices=list(values),
                  bounds=ParameterBounds(lower=0, upper=1, lower_inclusive=False, upper_inclusive=False))


def _problem(*params: ParameterDefinition, budget=8, baseline=0.9, constraints=(), objectives=1) -> AlgorithmProblem:
    return AlgorithmProblem(
        problem_type="system", parameter_space=ParameterSpace(parameters=list(params), constraints=list(constraints)),
        objective_id="OBJ", objective_direction=Direction.MAXIMIZE, objective_count=objectives,
        baseline_parameters={"beta": baseline}, max_evaluations=budget,
    )


def _result(cid: str, x: float, f) -> EvaluationResult:
    return EvaluationResult(candidate_id=cid, parameters={"beta": x}, objective=f(x),
                            objective_direction=Direction.MAXIMIZE, status=EvaluationStatus.EVALUATED)


def quadratic(x: float) -> float:
    return 240.0 - 400.0 * (x - 0.28) ** 2


def _drive(algorithm: Algorithm, problem: AlgorithmProblem, f=quadratic, hyperparameters=None):
    report = check_compatibility(algorithm, problem, hyperparameters or {}, 12)
    assert report.compatible, report.errors
    calls: list[float] = []

    def evaluate(point, round_):
        calls.append(point["beta"])
        return _result(f"CAND-{len(calls):03d}", point["beta"], f)

    baseline = _result("BASELINE", float(problem.baseline_parameters["beta"]), f)
    driver = AlgorithmDriver(algorithm, problem, report.resolved_hyperparameters, evaluate, lambda r: (0.0,))
    return driver.run([baseline]), calls


# ---------------------------------------------------------------------------
# §83 Algorithm unit tests
# ---------------------------------------------------------------------------


def test_algorithm_metadata():
    grid = GridSearchAlgorithm.metadata()
    assert grid.category is AlgorithmCategory.ENGINEERING_BASELINE and grid.learning_algorithm is False
    demo = ResearchDemoOptimizer.metadata()
    assert demo.algorithm_id == RESEARCH_DEMO_ID
    assert demo.category is AlgorithmCategory.RESEARCH_DEMO
    assert demo.learning_algorithm is False and demo.project_research_deliverable is False
    assert demo.acceptance_algorithm is False
    for text in (demo.name_en, demo.description_en, " ".join(demo.labels)):
        for banned in ("AI Optimizer", "Intelligent Algorithm", "Learning Optimizer", "Advanced AI"):
            assert banned not in text


def test_algorithm_registry():
    registry = default_algorithm_registry()
    assert [m.algorithm_id for m in registry.list()] == ["grid_search", RESEARCH_DEMO_ID]
    first, second = registry.create(RESEARCH_DEMO_ID), registry.create(RESEARCH_DEMO_ID)
    assert first is not second  # 每次运行一个新实例
    with pytest.raises(ValueError):
        registry.register(GridSearchAlgorithm)


def test_unknown_algorithm():
    with pytest.raises(AlgorithmNotFoundError):
        default_algorithm_registry().create("magic_ai")


def test_algorithm_capabilities():
    grid = GridSearchAlgorithm.metadata()
    assert grid.supported_parameter_types == [ParameterType.DISCRETE]
    assert grid.capabilities.supports_iterative_feedback is False
    demo = ResearchDemoOptimizer.metadata()
    assert demo.supported_parameter_types == [ParameterType.CONTINUOUS]
    caps = demo.capabilities
    assert caps.supports_iterative_feedback and caps.supports_batch_suggestions
    assert not (caps.supports_vector or caps.supports_multi_objective or caps.supports_constraints)


def test_algorithm_sdk_version():
    assert ALGORITHM_SDK_VERSION == "0.1"
    assert all(m.sdk_version == ALGORITHM_SDK_VERSION for m in default_algorithm_registry().list())
    assert GridSearchAlgorithm.metadata().model_dump(mode="json")["sdk_version"] == "0.1"


class _Recorder(Algorithm):
    """记录生命周期调用顺序的最小算法。"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._done = False

    @classmethod
    def metadata(cls):
        return ResearchDemoOptimizer.metadata().model_copy(update={"algorithm_id": "recorder",
                                                                   "hyperparameter_schema": []})

    def initialize(self, problem, hyperparameters, incumbents):
        self.calls.append(f"initialize:{len(incumbents)}")

    def suggest(self, max_suggestions):
        self.calls.append("suggest")
        return [{"beta": 0.5}]

    def observe(self, results):
        self.calls.append(f"observe:{results[0].candidate_id}")
        self._done = True

    def should_stop(self):
        return StopReason.COMPLETED if self._done else None

    def finalize(self):
        self.calls.append("finalize")
        return AlgorithmRecommendation(parameters={"beta": 0.5})


def test_algorithm_lifecycle():
    algo = _Recorder()
    trace, calls = _drive(algo, _problem(_continuous()))
    assert algo.calls == ["initialize:1", "suggest", "observe:CAND-001", "finalize"]
    assert calls == [0.5] and trace.stop_reason is StopReason.COMPLETED
    assert [e.sequence for e in trace.evaluations] == [0, 1] and trace.evaluations_used == 1


# ---------------------------------------------------------------------------
# §84 Parameter tests
# ---------------------------------------------------------------------------


def test_continuous_parameter():
    p = _continuous()
    assert p.validate_value(0.734) == 0.734
    with pytest.raises(ValueError):
        p.validate_value(1.2)


def test_discrete_parameter():
    p = _discrete()
    assert p.validate_value(0.6) == 0.6
    with pytest.raises(ValueError):
        p.validate_value(0.5)
    with pytest.raises(ValueError):
        _param(type=ParameterType.DISCRETE)


def test_integer_schema():
    p = _param(id="prb", type=ParameterType.INTEGER, bounds=ParameterBounds(lower=1, upper=273), unit="PRB")
    assert p.validate_value(52) == 52 and isinstance(p.validate_value(52.0), int)
    for bad in (2.5, 0, 300, "10"):
        with pytest.raises(ValueError):
            p.validate_value(bad)


def test_categorical_schema():
    p = _param(id="serving_cell", type=ParameterType.CATEGORICAL, choices=["CELL-A", "CELL-B"])
    assert p.validate_value("CELL-B") == "CELL-B"
    with pytest.raises(ValueError):
        p.validate_value("CELL-C")
    with pytest.raises(ValueError):
        _param(id="c", type=ParameterType.CATEGORICAL)


def test_vector_schema():
    p = _param(id="tx_power_per_cell", type=ParameterType.VECTOR, unit="dBm", shape=[3],
               bounds=ParameterBounds(lower=20, upper=46))
    assert p.element_type is VectorElementType.FLOAT
    assert p.validate_value([40, 42, 44]) == [40.0, 42.0, 44.0]
    for bad in ([40, 42], [40, 42, 50], "x"):
        with pytest.raises(ValueError):
            p.validate_value(bad)
    grid = _param(id="prb_alloc", type=ParameterType.VECTOR, unit="PRB", shape=[2, 2],
                  element_type=VectorElementType.INTEGER, bounds=ParameterBounds(lower=0, upper=273))
    assert grid.validate_value([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]
    with pytest.raises(ValueError):
        grid.validate_value([[1, 2.5], [3, 4]])
    with pytest.raises(ValueError):
        _param(id="v", type=ParameterType.VECTOR)
    with pytest.raises(ValueError):
        _param(id="s", type=ParameterType.CONTINUOUS, bounds=ParameterBounds(lower=0, upper=1), shape=[2])


def test_bounds_validation():
    with pytest.raises(ValueError):
        ParameterBounds(lower=1.0, upper=0.5)
    open_ = _param(type=ParameterType.CONTINUOUS,
                   bounds=ParameterBounds(lower=0, upper=1, lower_inclusive=False, upper_inclusive=False))
    for bad in (0.0, 1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            open_.validate_value(bad)


def test_choices_validation():
    with pytest.raises(ValueError):
        _param(type=ParameterType.DISCRETE, choices=[0.3, 1.5], bounds=ParameterBounds(lower=0, upper=1))


def test_parameter_serialization():
    space = ParameterSpace(parameters=[_continuous(), _param(id="cell", type=ParameterType.CATEGORICAL,
                                                             choices=["A", "B"])],
                           constraints=[ParameterConstraint(id="c1", expression="beta < 0.99")])
    again = ParameterSpace.model_validate_json(space.model_dump_json())
    assert again == space and again.sha256() == space.sha256()
    assert space.validate_point({"beta": 0.5, "cell": "A"}) == {"beta": 0.5, "cell": "A"}
    with pytest.raises(ValueError):
        space.validate_point({"beta": 0.5})
    with pytest.raises(ValueError):
        ParameterSpace(parameters=[_continuous(), _continuous()])
    hyper = _param(id="lr", role=ParameterRole.ALGORITHM_HYPERPARAMETER, type=ParameterType.CONTINUOUS,
                   bounds=ParameterBounds(lower=0, upper=1))
    with pytest.raises(ValueError):
        ParameterSpace(parameters=[hyper])  # 超参数不能进入网络参数空间


# ---------------------------------------------------------------------------
# §85 Compatibility tests
# ---------------------------------------------------------------------------


def _codes(report) -> list[CompatibilityCode]:
    return [e.code for e in report.errors]


def test_grid_search_discrete_supported():
    report = check_compatibility(GridSearchAlgorithm(), _problem(_discrete(), budget=3), {}, 12)
    assert report.compatible and report.resolved_hyperparameters == {}


def test_grid_search_continuous_rejected_without_choices():
    report = check_compatibility(GridSearchAlgorithm(), _problem(_continuous()), {}, 12)
    assert not report.compatible
    assert _codes(report) == [CompatibilityCode.ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED]
    assert "requires discrete candidate values" in report.errors[0].message


def test_demo_continuous_supported():
    report = check_compatibility(ResearchDemoOptimizer(), _problem(_continuous()), {}, 12)
    assert report.compatible
    assert report.resolved_hyperparameters == {"initial_step": 0.2, "min_step": 0.05, "shrink_factor": 0.5,
                                               "max_iterations": 8, "start_point": "baseline"}
    assert _codes(check_compatibility(ResearchDemoOptimizer(), _problem(_discrete()), {}, 12)) == [
        CompatibilityCode.ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED]


def test_unsupported_parameter_type():
    vector = _param(id="beta", type=ParameterType.VECTOR, shape=[1000], bounds=ParameterBounds(lower=0, upper=1))
    for algo in (GridSearchAlgorithm(), ResearchDemoOptimizer()):
        assert CompatibilityCode.ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED in _codes(
            check_compatibility(algo, _problem(vector), {}, 12))
    two = _problem(_continuous(), _continuous().model_copy(update={"id": "gamma"}))
    assert CompatibilityCode.ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED in _codes(
        check_compatibility(ResearchDemoOptimizer(), two, {}, 12))
    constrained = _problem(_continuous(), constraints=[ParameterConstraint(id="c", expression="beta<0.5")])
    assert _codes(check_compatibility(ResearchDemoOptimizer(), constrained, {}, 12)) == [
        CompatibilityCode.ALGORITHM_CONSTRAINTS_NOT_SUPPORTED]
    assert _codes(check_compatibility(ResearchDemoOptimizer(), _problem(_continuous(), objectives=2), {}, 12)) == [
        CompatibilityCode.ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED]
    prop = _problem(_continuous()).model_copy(update={"problem_type": "propagation"})
    assert _codes(check_compatibility(ResearchDemoOptimizer(), prop, {}, 12)) == [
        CompatibilityCode.ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED]


def test_invalid_hyperparameter():
    demo = ResearchDemoOptimizer()
    for bad in ({"initial_step": 0.0}, {"max_iterations": 2.5}, {"max_iterations": True}, {"start_point": "random"},
                {"learning_rate": 0.1}, {"initial_step": 0.05, "min_step": 0.1}, {"shrink_factor": 1.0}):
        report = check_compatibility(demo, _problem(_continuous()), bad, 12)
        assert _codes(report) == [CompatibilityCode.INVALID_HYPERPARAMETER], bad
    for budget in (0, 13):
        assert _codes(check_compatibility(demo, _problem(_continuous(), budget=budget), {}, 12)) == [
            CompatibilityCode.INVALID_EVALUATION_BUDGET]


def test_hyperparameter_types():
    flag = HyperparameterDefinition(id="f", name_zh="f", name_en="f", type=HyperparameterType.BOOLEAN, default=True)
    assert flag.validate_value(False) is False
    with pytest.raises(ValueError):
        flag.validate_value(1)
    with pytest.raises(ValueError):
        HyperparameterDefinition(id="c", name_zh="c", name_en="c", type=HyperparameterType.CATEGORICAL, default="a")


def test_grid_budget_warning():
    report = check_compatibility(GridSearchAlgorithm(), _problem(_discrete(), budget=2), {}, 12)
    assert report.compatible and "budget_exhausted" in report.warnings[0]


# ---------------------------------------------------------------------------
# §86 Research Demo algorithm tests
# ---------------------------------------------------------------------------


def _init_demo(budget=8, **hp):
    demo = ResearchDemoOptimizer()
    problem = _problem(_continuous(), budget=budget)
    resolved = check_compatibility(demo, problem, hp, 12).resolved_hyperparameters
    demo.initialize(problem, resolved, [_result("BASELINE", 0.9, quadratic)])
    return demo


def test_initialize():
    demo = _init_demo()
    state = demo.state_metadata()
    assert state["incumbent"] == 0.9 and state["mode"] == "explore" and state["step"] == 0.2
    assert state["incumbent_objective"] == pytest.approx(quadratic(0.9))


def test_first_suggestion():
    assert _init_demo().suggest(8) == [{"beta": 0.7}, {"beta": 0.99}]  # 0.9 ± 0.2，上界裁剪到 0.99


def test_observe():
    demo = _init_demo()
    demo.suggest(8)
    demo.observe([_result("CAND-001", 0.7, quadratic), _result("CAND-002", 0.99, quadratic)])
    state = demo.state_metadata()
    assert state["incumbent"] == 0.7 and state["direction"] == -1 and state["mode"] == "extend"
    assert state["round"] == 1


def test_next_suggestion_depends_on_observation():
    improving = _init_demo()
    improving.suggest(8)
    improving.observe([_result("A", 0.7, quadratic), _result("B", 0.99, quadratic)])
    worse = _init_demo()
    worse.suggest(8)
    worse.observe([_result("A", 0.7, lambda x: 0.0), _result("B", 0.99, lambda x: 0.0)])
    assert improving.suggest(8) == [{"beta": 0.5}]            # 沿改善方向继续
    assert worse.suggest(8) == [{"beta": 0.8}]  # 无改善 → 步长减半后重新探索（0.99 已评价，不重复建议）


def test_budget():
    trace, calls = _drive(ResearchDemoOptimizer(), _problem(_continuous(), budget=3))
    assert len(calls) == 3 and trace.evaluations_used == 3
    assert trace.stop_reason is StopReason.BUDGET_EXHAUSTED


class _Greedy(_Recorder):
    """每轮建议 5 个点、从不自行停止 —— 用于验证预算由平台执行。"""

    def suggest(self, max_suggestions):
        return [{"beta": round(0.1 * (i + 1), 1)} for i in range(5)]

    def observe(self, results):
        pass

    def should_stop(self):
        return None


def test_budget_enforced_by_platform():
    trace, calls = _drive(_Greedy(), _problem(_continuous(), budget=7))
    assert len(calls) == 7 and trace.rejected_suggestions == 3
    assert trace.stop_reason is StopReason.BUDGET_EXHAUSTED
    assert trace.rounds[-1].rejected_suggestions == [{"beta": 0.3}, {"beta": 0.4}, {"beta": 0.5}]


def test_convergence():
    trace, calls = _drive(ResearchDemoOptimizer(), _problem(_continuous(), budget=12), f=lambda x: 100.0)
    # 平坦目标：从不改善 → 0.2 → 0.1 → 0.05 → 0.025 < min_step
    assert trace.stop_reason is StopReason.CONVERGED
    assert calls == [0.7, 0.99, 0.8, 0.85, 0.95]


def test_stop_reason():
    trace, _ = _drive(ResearchDemoOptimizer(), _problem(_continuous(), budget=12), hyperparameters={
        "max_iterations": 2})
    assert trace.stop_reason is StopReason.MAX_ITERATIONS and len(trace.rounds) == 2
    assert trace.recommendation.parameters == {"beta": 0.5}


def test_determinism():
    a, calls_a = _drive(ResearchDemoOptimizer(), _problem(_continuous()))
    b, calls_b = _drive(ResearchDemoOptimizer(), _problem(_continuous()))
    assert calls_a == calls_b
    assert [r.state_after for r in a.rounds] == [r.state_after for r in b.rounds]


def test_demo_trajectory_and_trace():
    trace, calls = _drive(ResearchDemoOptimizer(), _problem(_continuous()))
    assert calls[:4] == [0.7, 0.99, 0.5, 0.3]
    assert trace.recommendation.parameters == {"beta": 0.3}
    assert trace.rounds[0].state_after["last_decision"] == "move 0.9 → 0.7 (improved)"
    assert json.loads(trace.model_dump_json())["algorithm_id"] == RESEARCH_DEMO_ID


class _OutOfBounds(_Recorder):
    def suggest(self, max_suggestions):
        return [{"beta": 1.5}]


class _Crashes(_Recorder):
    def observe(self, results):
        raise RuntimeError("boom")


def test_invalid_suggestion_and_crash_fail_with_trace():
    for algo in (_OutOfBounds(), _Crashes()):
        report = check_compatibility(algo, _problem(_continuous()), {}, 12)
        driver = AlgorithmDriver(algo, _problem(_continuous()), report.resolved_hyperparameters,
                                 lambda p, r: _result("CAND-001", p["beta"], quadratic), lambda r: (0.0,))
        with pytest.raises(AlgorithmExecutionError):
            driver.run([_result("BASELINE", 0.9, quadratic)])
        assert driver.trace.stop_reason is StopReason.FAILED and driver.trace.error


def test_algorithms_do_not_import_simulator_or_platform_internals():
    banned = ("sionna", "torch", "mitsuba", "system_simulation", "experiments", "evaluation.kpi",
              "system_optimization", "simulation")
    for path in (REPO / "src" / "algorithms").rglob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                module = stripped.split()[1]
                assert not any(module == b or module.startswith(b + ".") for b in banned), (path, line)
