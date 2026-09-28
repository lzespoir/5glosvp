"""
优化服务 / Optimization service.

只负责编排：解析场景/优化器/目标函数 → 运行基线 → 交给 Optimizer 搜索 → 选择最优 → 构建对比 → 持久化。
参数枚举属于 Optimizer，目标值计算属于 Objective，仿真属于 ExperimentService / SimulationBackend。
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Mapping

from experiments import (
    ArtifactNotFoundError,
    ExperimentPurpose,
    ExperimentRecord,
    ExperimentService,
    ExperimentStatus,
)
from simulation import ArtifactExportError, ScenarioConfig

from .base import CandidateEvaluator, Objective, ObjectiveInputs, Optimizer
from .errors import CandidateEvaluationError, InvalidParameterSpaceError, OptimizationNotFoundError
from .models import (
    BASELINE_CANDIDATE_ID,
    TX_POWER_PARAMETER,
    CandidateError,
    CandidateStatus,
    ObjectiveEvaluation,
    ObjectiveSpec,
    OptimizationCandidate,
    OptimizationComparison,
    OptimizationError,
    OptimizationErrorCode,
    OptimizationProblem,
    OptimizationRecord,
    OptimizationStatus,
    ParameterSpace,
    candidate_id_for,
    new_optimization_id,
    utc_now,
)
from .registry import ObjectiveRegistry, OptimizerRegistry
from .store import OptimizationStore

logger = logging.getLogger(__name__)

MAX_CANDIDATES = 10
TX_POWER_BOUNDS_DBM = (-10.0, 70.0)
# |baseline objective| 小于该值时不计算相对改善，避免除零
RELATIVE_IMPROVEMENT_EPS = 1e-9


def derive_candidate_config(base: ScenarioConfig, parameters: Mapping[str, float]) -> ScenarioConfig:
    """基础场景 + 候选参数 → 派生场景（深拷贝，原场景不变；随机种子保持不变）。"""
    power = float(parameters[TX_POWER_PARAMETER])
    derived = base.model_copy(deep=True)
    return derived.model_copy(
        update={"transmitters": [t.model_copy(update={"power_dbm": power}) for t in derived.transmitters]}
    )


def baseline_parameters(config: ScenarioConfig) -> dict[str, float]:
    powers = {t.power_dbm for t in config.transmitters}
    if None in powers or len(powers) != 1:
        raise InvalidParameterSpaceError(
            f"Scenario {config.scenario_id} must set one explicit power_dbm for all transmitters to define a baseline"
        )
    (power,) = powers
    assert power is not None
    return {TX_POWER_PARAMETER: float(power)}


def build_comparison(baseline: OptimizationCandidate, best: OptimizationCandidate) -> OptimizationComparison:
    assert baseline.objective and best.objective and baseline.experiment_id and best.experiment_id
    base_value, best_value = baseline.objective.value, best.objective.value
    absolute = best_value - base_value
    relative = None if abs(base_value) < RELATIVE_IMPROVEMENT_EPS else absolute / abs(base_value) * 100.0
    return OptimizationComparison(
        baseline_experiment_id=baseline.experiment_id,
        optimized_experiment_id=best.experiment_id,
        optimized_candidate_id=best.candidate_id,
        baseline_parameters=baseline.parameters,
        optimized_parameters=best.parameters,
        baseline_objective=base_value,
        optimized_objective=best_value,
        absolute_improvement=absolute,
        relative_improvement_percent=relative,
    )


class _RecordingEvaluator(CandidateEvaluator):
    """运行候选实验、计算目标值，并把每个候选（含失败者）立即持久化到优化记录。"""

    def __init__(
        self,
        service: OptimizationService,
        record: OptimizationRecord,
        base_config: ScenarioConfig,
        objective: Objective,
    ) -> None:
        self._service = service
        self._record = record
        self._base_config = base_config
        self._objective = objective
        powers = [*record.parameter_space.tx_power_dbm, record.baseline_parameters[TX_POWER_PARAMETER]]
        self._bounds = {TX_POWER_PARAMETER: (min(powers), max(powers))}

    def evaluate_baseline(self) -> OptimizationCandidate:
        candidate = self._run(BASELINE_CANDIDATE_ID, 0, self._record.baseline_parameters, is_baseline=True)
        self._record.baseline = candidate
        self._service.persist_event(self._record, "baseline_evaluated", candidate)
        return candidate

    def evaluate(self, parameters: Mapping[str, float], iteration: int) -> OptimizationCandidate:
        candidate_id = candidate_id_for(iteration)
        baseline = self._record.baseline
        if baseline is not None and dict(parameters) == baseline.parameters:
            candidate = baseline.model_copy(
                update={
                    "candidate_id": candidate_id, "iteration": iteration,
                    "is_baseline": False, "reused_baseline": True, "runtime_seconds": 0.0,
                }
            )
        else:
            candidate = self._run(candidate_id, iteration, parameters, is_baseline=False)
        self._record.candidates.append(candidate)
        self._service.persist_event(self._record, "candidate_evaluated", candidate)
        return candidate

    def _run(
        self, candidate_id: str, iteration: int, parameters: Mapping[str, float], is_baseline: bool
    ) -> OptimizationCandidate:
        record = self._record
        config = derive_candidate_config(self._base_config, parameters)
        label = "baseline" if is_baseline else candidate_id
        t0 = time.perf_counter()
        experiment = self._service.experiments.run_experiment(
            name=f"{record.optimization_id} {label} · TX {parameters[TX_POWER_PARAMETER]:g} dBm",
            config=config,
            purpose=ExperimentPurpose.OPTIMIZATION_BASELINE if is_baseline else ExperimentPurpose.OPTIMIZATION_CANDIDATE,
            optimization_id=record.optimization_id,
        )
        candidate = OptimizationCandidate(
            candidate_id=candidate_id, iteration=iteration, parameters=dict(parameters),
            status=CandidateStatus.EVALUATED, experiment_id=experiment.experiment_id, is_baseline=is_baseline,
        )
        try:
            candidate.objective = self._evaluate_objective(experiment, parameters)
        except CandidateEvaluationError as e:
            candidate.status = CandidateStatus.FAILED
            candidate.error = CandidateError(code=e.code, message=str(e))
            candidate.runtime_seconds = time.perf_counter() - t0
            if is_baseline:
                record.baseline = candidate
            else:
                record.candidates.append(candidate)
            self._service.persist_event(record, "candidate_failed", candidate)
            raise CandidateEvaluationError(candidate_id, str(e), experiment.experiment_id, e.code) from e
        candidate.runtime_seconds = time.perf_counter() - t0
        return candidate

    def _evaluate_objective(
        self, experiment: ExperimentRecord, parameters: Mapping[str, float]
    ) -> ObjectiveEvaluation:
        exp_id = experiment.experiment_id
        if experiment.status is not ExperimentStatus.SUCCEEDED:
            code = experiment.error.code.value if experiment.error else "SIMULATION_FAILED"
            message = experiment.error.message if experiment.error else "experiment did not succeed"
            raise CandidateEvaluationError("", f"Experiment {exp_id} failed: {message}", exp_id, code)
        try:
            layers = self._service.experiments.radio_map_layers(exp_id)
            return self._objective.evaluate(
                ObjectiveInputs(layers=layers, parameters=parameters, parameter_bounds=self._bounds),
                self._record.objective.params,
            )
        except (ArtifactNotFoundError, ArtifactExportError, ValueError, KeyError) as e:
            raise CandidateEvaluationError(
                "", f"Objective evaluation failed for {exp_id}: {e}", exp_id, "OBJECTIVE_EVALUATION_FAILED"
            ) from e


class OptimizationService:
    """Day 4 同步执行：请求在所有候选评价完成后返回。"""

    def __init__(
        self,
        experiments: ExperimentService,
        store: OptimizationStore,
        optimizers: OptimizerRegistry,
        objectives: ObjectiveRegistry,
        max_candidates: int = MAX_CANDIDATES,
    ) -> None:
        self.experiments = experiments
        self._store = store
        self._optimizers = optimizers
        self._objectives = objectives
        self._max_candidates = max_candidates

    @property
    def max_candidates(self) -> int:
        return self._max_candidates

    def list_optimizers(self) -> list[Optimizer]:
        return self._optimizers.list()

    def list_objectives(self) -> list[Objective]:
        return self._objectives.list()

    def get(self, optimization_id: str) -> OptimizationRecord:
        record = self._store.get(optimization_id)
        if record is None:
            raise OptimizationNotFoundError(f"Optimization not found: {optimization_id}")
        return record

    def list(self, limit: int = 50, offset: int = 0) -> tuple[list[OptimizationRecord], int]:
        return self._store.list(limit=limit, offset=offset), self._store.count()

    def create_optimization(
        self,
        name: str,
        scenario_id: str,
        optimizer_id: str,
        objective_id: str,
        parameter_space: ParameterSpace,
        objective_params: Mapping[str, float] | None = None,
    ) -> OptimizationRecord:
        config = self.experiments.get_scenario(scenario_id)
        optimizer = self._optimizers.create(optimizer_id)
        objective = self._objectives.get(objective_id)
        self._validate_parameter_space(parameter_space)
        params = {**objective.default_params, **(objective_params or {})}
        base_params = baseline_parameters(config)
        self.experiments.ensure_backend_available(config.backend)
        descriptor = self.experiments.backend_descriptor(config.backend)
        info = optimizer.info

        record = OptimizationRecord(
            optimization_id=self._new_unique_id(),
            name=name,
            status=OptimizationStatus.CREATED,
            scenario_id=config.scenario_id,
            scenario_name_zh=config.name_zh,
            scenario_name_en=config.name_en,
            simulation_backend=config.backend,
            optimizer_id=info.id,
            objective=ObjectiveSpec(
                id=objective.id, version=objective.version, direction=objective.direction, params=params
            ),
            parameter_space=parameter_space,
            baseline_parameters=base_params,
            seed=config.random_seed,
            created_at=utc_now(),
            provenance={
                "optimizer": info.id,
                "optimizer_category": info.category,
                "learning_algorithm": info.learning_algorithm,
                "simulation_backend": config.backend,
                "source_type": descriptor.source_type,
                "measured": False,
                "objective_id": objective.id,
                "objective_version": objective.version,
                "scenario_id": config.scenario_id,
                "seed": config.random_seed,
                "evidence_level": (
                    "Synthetic / Simulation Validation" if descriptor.source_type == "simulation"
                    else "Software Test Fixture"
                ),
                "common_random_numbers": "Baseline and all candidates use the same scenario seed",
                "search_space_source": "[A] Assumption — engineering demonstration search space",
                "objective_assumptions": dict(objective.assumptions),
            },
        )
        record.transition(OptimizationStatus.CREATED)
        record.add_event("optimization_created")
        self._store.create(record)
        logger.info("%s CREATED scenario=%s optimizer=%s", record.optimization_id, scenario_id, info.id)

        self._execute(record, optimizer, objective, config)
        return self.get(record.optimization_id)

    def persist_event(self, record: OptimizationRecord, event: str, candidate: OptimizationCandidate) -> None:
        record.add_event(event, candidate_id=candidate.candidate_id, experiment_id=candidate.experiment_id)
        self._store.update(record)

    # ------------------------------------------------------------------

    def _validate_parameter_space(self, space: ParameterSpace) -> None:
        values = space.tx_power_dbm
        if len(values) > self._max_candidates:
            raise InvalidParameterSpaceError(
                f"Too many candidates: {len(values)} > {self._max_candidates} (synchronous API limit)"
            )
        lo, hi = TX_POWER_BOUNDS_DBM
        bad = [v for v in values if not math.isfinite(v) or not lo <= v <= hi]
        if bad:
            raise InvalidParameterSpaceError(f"tx_power_dbm values out of range [{lo}, {hi}] dBm: {bad}")

    def _new_unique_id(self) -> str:
        while True:
            optimization_id = new_optimization_id()
            if self._store.get(optimization_id) is None:
                return optimization_id

    def _execute(
        self, record: OptimizationRecord, optimizer: Optimizer, objective: Objective, config: ScenarioConfig
    ) -> None:
        t_start = time.perf_counter()
        record.started_at = utc_now()
        record.transition(OptimizationStatus.RUNNING)
        self._store.update(record)

        evaluator = _RecordingEvaluator(self, record, config, objective)
        problem = OptimizationProblem(
            scenario_id=record.scenario_id,
            parameter_space=record.parameter_space,
            objective=record.objective,
            baseline_parameters=record.baseline_parameters,
            seed=record.seed,
        )
        try:
            t0 = time.perf_counter()
            baseline = evaluator.evaluate_baseline()
            record.runtime.baseline_seconds = time.perf_counter() - t0

            t1 = time.perf_counter()
            search = optimizer.optimize(problem, evaluator)
            record.runtime.candidate_evaluation_seconds = time.perf_counter() - t1

            best = next(c for c in record.candidates if c.candidate_id == search.best_candidate_id)
            record.best_candidate_id = best.candidate_id
            record.comparison = build_comparison(baseline, best)
            record.add_event("best_candidate_selected", best.candidate_id, best.experiment_id)
            record.finished_at = utc_now()
            record.transition(OptimizationStatus.SUCCEEDED)
            record.add_event("optimization_completed")
        except CandidateEvaluationError as e:
            self._mark_failed(record, e, e.candidate_id, e.experiment_id)
        except Exception as e:  # noqa: BLE001 - 任何失败都落为 FAILED，traceback 只写日志
            logger.exception("%s optimization failed", record.optimization_id)
            self._mark_failed(record, e, None, None)
        finally:
            record.runtime.total_seconds = time.perf_counter() - t_start
            self._store.update(record)
        logger.info("%s %s total=%.3f s", record.optimization_id, record.status.name, record.runtime.total_seconds)

    @staticmethod
    def _mark_failed(
        record: OptimizationRecord, exc: Exception, candidate_id: str | None, experiment_id: str | None
    ) -> None:
        record.error = OptimizationError(
            code=OptimizationErrorCode.OPTIMIZATION_FAILED, message=str(exc), type=type(exc).__name__,
            failed_candidate_id=candidate_id, experiment_id=experiment_id,
        )
        record.finished_at = utc_now()
        record.transition(OptimizationStatus.FAILED)
        record.add_event("optimization_failed", candidate_id, experiment_id)
        logger.error("%s FAILED candidate=%s: %s", record.optimization_id, candidate_id, exc)
