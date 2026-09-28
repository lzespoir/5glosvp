"""
系统级优化服务 / System optimization service.

    GridSearchOptimizer → CandidateEvaluator → SystemOptimizationService → SystemExperimentService → Backend

职责：校验问题 → 冻结评价上下文（一次 RT 信道实现）→ 基线 → 候选（同一上下文）→ KPI → 目标值
→ 选择最优 → 对比（含次要 KPI 负向变化）→ 公平性检查 → 持久化与证据。
Optimizer 与 Objective 都不接触仿真引擎；本服务只通过 SystemExperimentService 运行实验。
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping

import numpy as np

from evaluation.kpi import (
    AVG_UE_THROUGHPUT_V0_1,
    NETWORK_THROUGHPUT_V0_1,
    P5_UE_THROUGHPUT_V0_1,
    UE_THROUGHPUT_V0_1,
)
from optimization.base import CandidateEvaluator, Optimizer
from optimization.errors import InvalidParameterSpaceError
from optimization.models import (
    BASELINE_CANDIDATE_ID,
    CandidateError,
    CandidateStatus,
    Direction,
    ObjectiveSpec,
    OptimizationCandidate,
    OptimizationStatus,
    candidate_id_for,
    new_optimization_id,
)
from optimization.optimizers.grid_search import GRID_SEARCH_VERSION
from optimization.registry import OptimizerRegistry
from system_simulation import MODEL_LABELS, SystemExperimentService
from system_simulation.base import Capability, ChannelRealization
from system_simulation.models import (
    SystemExperimentPurpose,
    SystemExperimentRecord,
    SystemExperimentStatus,
    SystemScenario,
)
from system_simulation.realization import save_channel

from .artifacts import export_evidence
from .context import apply_protocol, build_context, context_link, fairness_evidence, fairness_report
from .errors import (
    SystemOptimizationArtifactNotFoundError,
    SystemOptimizationBusyError,
    SystemOptimizationNotFoundError,
    UnsupportedProblemTypeError,
)
from .models import (
    PROBLEM_TYPE_SYSTEM,
    BenchmarkProtocol,
    KpiChange,
    KpiStatistic,
    SystemComparison,
    SystemOptimizationCandidate,
    SystemOptimizationError,
    SystemOptimizationErrorCode,
    SystemOptimizationRecord,
    SystemOptimizationStage,
    new_channel_realization_id,
    new_context_id,
    utc_now,
)
from .objectives import SystemObjective, SystemObjectiveRegistry
from .parameters import SystemParameter, SystemParameterCatalog
from .protocols import BenchmarkProtocolRegistry
from .store import FileSystemOptimizationStore

logger = logging.getLogger(__name__)

MAX_SYSTEM_CANDIDATES = 8
RELATIVE_EPS = 1e-9
TIE_BREAK_RULE = "Equal objective → baseline parameter value first, then candidate definition order"
SECONDARY_KPIS = (NETWORK_THROUGHPUT_V0_1, AVG_UE_THROUGHPUT_V0_1, P5_UE_THROUGHPUT_V0_1)
KPI_FIELDS = {
    NETWORK_THROUGHPUT_V0_1: "network_throughput_mbps",
    AVG_UE_THROUGHPUT_V0_1: "average_ue_throughput_mbps",
    P5_UE_THROUGHPUT_V0_1: "p5_ue_throughput_mbps",
}

Runner = Callable[[Callable[[], None]], None]


def _thread_runner(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, name="system-optimization", daemon=True).start()


def relative_change(baseline: float, value: float) -> float | None:
    """(value - baseline) / |baseline| × 100；|baseline| 过小时返回 None。"""
    return None if abs(baseline) < RELATIVE_EPS else (value - baseline) / abs(baseline) * 100.0


def kpi_statistic(values: list[float]) -> KpiStatistic:
    arr = np.asarray(values, dtype=float)
    return KpiStatistic(mean=float(arr.mean()), std=float(arr.std()), min=float(arr.min()), max=float(arr.max()),
                        n=int(arr.size))


def build_system_comparison(
    baseline: SystemOptimizationCandidate,
    best: SystemOptimizationCandidate,
    direction: Direction,
    variability_percent: float,
) -> SystemComparison:
    assert baseline.objective and best.objective and baseline.experiment_id and best.experiment_id
    changes = []
    for kpi_id, field in KPI_FIELDS.items():
        b, v = getattr(baseline, field).mean, getattr(best, field).mean
        delta = v - b
        changes.append(KpiChange(
            kpi_id=kpi_id, baseline=b, best=v, absolute_change=delta, relative_change_percent=relative_change(b, v),
            direction="increase" if delta > 0 else ("decrease" if delta < 0 else "unchanged"),
        ))
    base_obj, best_obj = baseline.objective.value, best.objective.value
    absolute = best_obj - base_obj
    relative = relative_change(base_obj, best_obj)
    sign = 1.0 if direction is Direction.MAXIMIZE else -1.0
    improved = sign * absolute > 0
    return SystemComparison(
        baseline_candidate_id=baseline.candidate_id,
        best_candidate_id=best.candidate_id,
        baseline_experiment_id=baseline.experiment_id,
        best_experiment_id=best.experiment_id,
        baseline_parameters=baseline.parameters,
        best_parameters=best.parameters,
        baseline_objective=base_obj,
        best_objective=best_obj,
        absolute_improvement=absolute,
        relative_improvement_percent=relative,
        improved=improved,
        kpi_changes=changes,
        negative_kpi_changes=[c.kpi_id for c in changes if c.direction == "decrease"],
        within_observed_variability=improved and relative is not None and abs(relative) <= variability_percent,
        observed_variability_percent=variability_percent,
        tie_break_rule=TIE_BREAK_RULE,
    )


class _SystemSearchProblem:
    """SearchProblem：候选 = 用户给定的参数值；基线作为现任解参与选择。"""

    def __init__(self, record: SystemOptimizationRecord, direction: Direction) -> None:
        self._record = record
        self._direction = direction
        self._pid = record.parameter.id

    @property
    def direction(self) -> Direction:
        return self._direction

    def candidate_parameters(self) -> list[dict[str, float]]:
        return [{self._pid: float(v)} for v in self._record.candidate_values]  # type: ignore[arg-type]

    def incumbents(self) -> list[OptimizationCandidate]:
        return [self._record.baseline] if self._record.baseline is not None else []

    def tie_break_key(self, candidate: OptimizationCandidate) -> tuple[float, ...]:
        is_baseline_value = candidate.parameters == self._record.baseline_parameters
        return (1.0 if is_baseline_value else 0.0, -float(candidate.iteration))


class _ContextEvaluator(CandidateEvaluator):
    """在同一冻结上下文中运行基线 / 候选；候选失败被记录后继续（不抛出）。"""

    def __init__(
        self,
        service: SystemOptimizationService,
        record: SystemOptimizationRecord,
        scenario: SystemScenario,
        channel: ChannelRealization,
        objective: SystemObjective,
        parameter: SystemParameter,
    ) -> None:
        self._service = service
        self._record = record
        self._scenario = scenario
        self._channel = channel
        self._objective = objective
        self._parameter = parameter
        self.experiments: dict[str, SystemExperimentRecord] = {}

    def evaluate_baseline(self) -> SystemOptimizationCandidate:
        candidate = self._run(BASELINE_CANDIDATE_ID, 0, self._record.baseline_parameters, is_baseline=True)
        self._record.baseline = candidate
        self._service.persist_event(self._record, "baseline_evaluated", candidate)
        return candidate

    def evaluate(self, parameters: Mapping[str, float], iteration: int) -> SystemOptimizationCandidate:
        record = self._record
        candidate_id = candidate_id_for(iteration)
        progress = record.progress
        progress.stage = SystemOptimizationStage.EVALUATING_CANDIDATE
        progress.current_candidate_id = candidate_id
        progress.current_parameter_value = float(parameters[self._parameter.definition.id])
        self._service.persist(record)
        baseline = record.baseline
        reusable = baseline is not None and baseline.status is CandidateStatus.EVALUATED
        if reusable and baseline is not None and dict(parameters) == baseline.parameters:
            # 同一冻结上下文 + 确定性 SYS：与基线参数相同的候选直接复用基线实验
            candidate = baseline.model_copy(update={
                "candidate_id": candidate_id, "iteration": iteration, "is_baseline": False,
                "reused_baseline": True, "runtime_seconds": 0.0,
            })
        else:
            candidate = self._run(candidate_id, iteration, parameters, is_baseline=False)
        record.candidates.append(candidate)
        progress.completed_candidates += 1
        event = "candidate_failed" if candidate.status is CandidateStatus.FAILED else "candidate_evaluated"
        self._service.persist_event(record, event, candidate)
        return candidate

    def _run(self, candidate_id: str, iteration: int, parameters: Mapping[str, float],
             is_baseline: bool) -> SystemOptimizationCandidate:
        record = self._record
        context = record.evaluation_context
        assert context is not None
        pid = self._parameter.definition.id
        value = float(parameters[pid])
        scenario = self._parameter.apply(self._scenario, value)
        protocol = record.benchmark_protocol
        candidate = SystemOptimizationCandidate(
            candidate_id=candidate_id, iteration=iteration, parameters=dict(parameters),
            status=CandidateStatus.EVALUATED, is_baseline=is_baseline, evaluation_context_id=context.context_id,
        )
        t0 = time.perf_counter()
        experiments: list[SystemExperimentRecord] = []
        try:
            for repeat in range(protocol.num_repeats):
                label = "baseline" if is_baseline else candidate_id
                suffix = f" · repeat {repeat + 1}/{protocol.num_repeats}" if protocol.num_repeats > 1 else ""
                exp = self._service.experiments.run_in_context(
                    f"{record.optimization_id} {label} · {pid}={value:g}{suffix}",
                    scenario, record.backend_id, self._channel,
                    purpose=SystemExperimentPurpose.OPTIMIZATION_BASELINE if is_baseline
                    else SystemExperimentPurpose.OPTIMIZATION_CANDIDATE,
                    optimization_id=record.optimization_id, candidate_id=candidate_id, context=context_link(context),
                )
                experiments.append(exp)
                self.experiments[exp.experiment_id] = exp
                candidate.experiment_ids.append(exp.experiment_id)
                candidate.experiment_id = candidate.experiment_ids[0]
                if exp.status is not SystemExperimentStatus.SUCCEEDED:
                    code = exp.error.code.value if exp.error else "SYSTEM_SIMULATION_FAILED"
                    message = exp.error.message if exp.error else "experiment did not succeed"
                    raise _CandidateFailed(code, f"Experiment {exp.experiment_id} failed: {message}")
            self._summarize(candidate, experiments)
        except _CandidateFailed as e:
            candidate.status = CandidateStatus.FAILED
            candidate.error = CandidateError(code=e.code, message=str(e))
        except Exception as e:  # noqa: BLE001 - 候选失败必须保留，不中断优化
            logger.exception("%s candidate %s failed", record.optimization_id, candidate_id)
            candidate.status = CandidateStatus.FAILED
            candidate.error = CandidateError(code="CANDIDATE_EVALUATION_FAILED", message=str(e) or type(e).__name__)
        candidate.runtime_seconds = time.perf_counter() - t0
        return candidate

    def _summarize(self, candidate: SystemOptimizationCandidate, experiments: list[SystemExperimentRecord]) -> None:
        values: dict[str, list[float]] = {k: [] for k in SECONDARY_KPIS}
        per_ue: dict[str, list[float]] = {}
        for exp in experiments:
            kpis = {k.metric_id: k for k in exp.kpis}
            for kpi_id in SECONDARY_KPIS:
                kpi = kpis.get(kpi_id)
                if kpi is None or kpi.value is None:
                    raise _CandidateFailed("KPI_UNAVAILABLE", f"{kpi_id} unavailable in {exp.experiment_id}")
                values[kpi_id].append(float(kpi.value))
            for ue_id, v in (kpis[UE_THROUGHPUT_V0_1].per_ue or {}).items():
                per_ue.setdefault(ue_id, []).append(float(v))
        for kpi_id, field in KPI_FIELDS.items():
            setattr(candidate, field, kpi_statistic(values[kpi_id]))
        candidate.per_ue_throughput_mbps = {u: float(np.mean(v)) for u, v in per_ue.items()}
        evidence = [fairness_evidence(e) for e in experiments]
        if any(e != evidence[0] for e in evidence[1:]):
            raise _CandidateFailed("INCONSISTENT_REPEATS", "Repeats were not evaluated under identical conditions")
        candidate.fairness = evidence[0]
        aggregated = {k: getattr(candidate, KPI_FIELDS[k]).mean for k in SECONDARY_KPIS}
        candidate.objective = self._objective.evaluate(aggregated)


class _CandidateFailed(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SystemOptimizationService:
    def __init__(
        self,
        experiments: SystemExperimentService,
        store: FileSystemOptimizationStore,
        optimizers: OptimizerRegistry,
        objectives: SystemObjectiveRegistry,
        protocols: BenchmarkProtocolRegistry,
        parameters: SystemParameterCatalog,
        git_commit: str | None = None,
        max_candidates: int = MAX_SYSTEM_CANDIDATES,
        runner: Runner = _thread_runner,
    ) -> None:
        self.experiments = experiments
        self._store = store
        self._optimizers = optimizers
        self._objectives = objectives
        self._protocols = protocols
        self._parameters = parameters
        self._git_commit = git_commit
        self._max_candidates = max_candidates
        self._runner = runner
        self._busy = threading.Lock()
        self._recover_interrupted()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def max_candidates(self) -> int:
        return self._max_candidates

    def list_optimizers(self) -> list[Optimizer]:
        return [o for o in self._optimizers.list() if PROBLEM_TYPE_SYSTEM in o.info.supported_problem_types]

    def list_objectives(self) -> list[SystemObjective]:
        return self._objectives.list()

    def list_protocols(self) -> list[BenchmarkProtocol]:
        return self._protocols.list()

    def list_parameters(self) -> list[SystemParameter]:
        return self._parameters.list()

    def get(self, optimization_id: str) -> SystemOptimizationRecord:
        record = self._store.get(optimization_id)
        if record is None:
            raise SystemOptimizationNotFoundError(f"System optimization not found: {optimization_id}")
        return record

    def list(self, limit: int = 50, offset: int = 0) -> tuple[list[SystemOptimizationRecord], int]:
        return self._store.list(limit=limit, offset=offset), self._store.count()

    def resolve_artifact(self, optimization_id: str, name: str):
        record = self.get(optimization_id)
        known = {a.name: a for a in record.artifacts}
        if name not in known:
            raise SystemOptimizationArtifactNotFoundError(f"Artifact not found: {name!r}")
        return known[name], self._store.resolve_artifact(optimization_id, name)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        scenario_id: str,
        optimizer_id: str,
        objective_id: str,
        parameter_id: str,
        candidate_values: list[float],
        benchmark_protocol_id: str,
        backend_id: str | None = None,
    ) -> SystemOptimizationRecord:
        scenario = self.experiments.get_scenario(scenario_id)
        optimizer = self._optimizers.create(optimizer_id)
        if PROBLEM_TYPE_SYSTEM not in optimizer.info.supported_problem_types:
            raise UnsupportedProblemTypeError(f"Optimizer '{optimizer_id}' does not support system problems")
        objective = self._objectives.get(objective_id)
        protocol = self._protocols.get(benchmark_protocol_id)
        parameter = self._parameters.get(parameter_id)
        if parameter.affects_propagation:
            raise InvalidParameterSpaceError(
                f"Parameter '{parameter_id}' changes propagation; it cannot share a frozen channel realization"
            )
        values = self._validate_candidates(parameter, candidate_values)
        backend = backend_id or scenario.backend
        descriptor, _, health = self.experiments.require_backend(
            backend, Capability.CHANNEL_REUSE, Capability.THROUGHPUT
        )
        baseline_value = parameter.read(scenario)
        parameter.definition.validate_value(baseline_value)
        info = optimizer.info
        obj = objective.info

        if not self._busy.acquire(blocking=False):
            raise SystemOptimizationBusyError("Another system optimization is running; retry after it finishes")
        try:
            record = SystemOptimizationRecord(
                optimization_id=self._new_unique_id(),
                name=name,
                status=OptimizationStatus.CREATED,
                scenario_id=scenario.scenario_id,
                scenario_name_zh=scenario.name_zh,
                scenario_name_en=scenario.name_en,
                backend_id=descriptor.id,
                optimizer_id=info.id,
                optimizer_version=GRID_SEARCH_VERSION,
                objective=ObjectiveSpec(id=obj.id, version=obj.version, direction=obj.direction),
                parameter=parameter.definition,
                candidate_values=list(values),
                baseline_parameters={parameter.definition.id: baseline_value},
                benchmark_protocol=protocol,
                seed=scenario.seed,
                created_at=utc_now(),
                provenance={
                    "optimizer": info.id,
                    "optimizer_version": GRID_SEARCH_VERSION,
                    "optimizer_category": info.category,
                    "learning_algorithm": info.learning_algorithm,
                    "objective": obj.id,
                    "objective_version": obj.version,
                    "scenario": scenario.scenario_id,
                    "backend": descriptor.id,
                    "backend_version": health.get("version"),
                    "provider": descriptor.provider,
                    "model_type": descriptor.model_type.value,
                    "model_label": MODEL_LABELS[descriptor.model_type],
                    "source_type": descriptor.source_type,
                    "traffic_model": scenario.traffic.model_dump(mode="json"),
                    "benchmark_protocol": f"{protocol.protocol_id} v{protocol.version}",
                    "seed": scenario.seed,
                    "git_commit": self._git_commit,
                    "measured": False,
                    "huawei_data": False,
                    "acceptance_evidence": False,
                    "evidence_level": "System Optimization Validation (simulation)"
                    if descriptor.source_type == "simulation" else "Software Test Fixture",
                    "search_space_source": parameter.recommended_values_source,
                    "parameter_source": parameter.definition.source,
                },
            )
            record.progress.total_candidates = len(values)
            record.transition(OptimizationStatus.CREATED)
            record.add_event("optimization_created")
            self._store.create(record)
            logger.info("%s CREATED system optimization scenario=%s %s=%s", record.optimization_id, scenario_id,
                        parameter_id, values)
        except BaseException:
            self._busy.release()
            raise

        def job() -> None:
            try:
                self._execute(record, optimizer, objective, parameter, scenario)
            finally:
                self._busy.release()

        self._runner(job)
        return self.get(record.optimization_id)

    def persist(self, record: SystemOptimizationRecord) -> None:
        self._store.update(record)

    def persist_event(self, record: SystemOptimizationRecord, event: str, candidate: OptimizationCandidate) -> None:
        record.add_event(event, candidate_id=candidate.candidate_id, experiment_id=candidate.experiment_id)
        self._store.update(record)

    # ------------------------------------------------------------------

    def _validate_candidates(self, parameter: SystemParameter, values: list[float]) -> list[float]:
        if not values:
            raise InvalidParameterSpaceError("At least one candidate value is required")
        if len(values) > self._max_candidates:
            raise InvalidParameterSpaceError(f"Too many candidates: {len(values)} > {self._max_candidates}")
        if len(set(values)) != len(values):
            raise InvalidParameterSpaceError("Candidate values must be unique")
        try:
            return [float(parameter.definition.validate_value(v)) for v in values]  # type: ignore[arg-type]
        except ValueError as e:
            raise InvalidParameterSpaceError(str(e)) from e

    def _new_unique_id(self) -> str:
        while True:
            optimization_id = new_optimization_id()
            if not self._store.exists(optimization_id):
                return optimization_id

    def _recover_interrupted(self) -> None:
        for record in self._store.list_all():
            if not record.status.is_terminal:
                record.error = SystemOptimizationError(
                    code=SystemOptimizationErrorCode.INTERRUPTED, type="Interrupted",
                    message="Optimization was interrupted (service restarted before completion)")
                record.progress.stage = SystemOptimizationStage.FAILED
                record.finished_at = utc_now()
                record.transition(OptimizationStatus.FAILED)
                record.add_event("optimization_interrupted")
                self._store.update(record)
                logger.warning("%s marked FAILED (interrupted)", record.optimization_id)

    def _stage(self, record: SystemOptimizationRecord, stage: SystemOptimizationStage) -> None:
        record.progress.stage = stage
        record.progress.current_candidate_id = None
        record.progress.current_parameter_value = None
        record.add_event(f"stage_{stage.value}")
        self._store.update(record)

    def _execute(
        self,
        record: SystemOptimizationRecord,
        optimizer: Optimizer,
        objective: SystemObjective,
        parameter: SystemParameter,
        base_scenario: SystemScenario,
    ) -> None:
        t_start = time.perf_counter()
        record.started_at = utc_now()
        record.transition(OptimizationStatus.RUNNING)
        failed_code = SystemOptimizationErrorCode.OPTIMIZATION_FAILED
        evaluator: _ContextEvaluator | None = None
        try:
            failed_code = SystemOptimizationErrorCode.CONTEXT_PREPARATION_FAILED
            self._stage(record, SystemOptimizationStage.PREPARING_CONTEXT)
            t0 = time.perf_counter()
            scenario = apply_protocol(base_scenario, record.benchmark_protocol)
            channel = self.experiments.realize_channel(scenario, record.backend_id)
            channel_path = save_channel(self._store.context_dir(record.optimization_id), channel)
            record.evaluation_context = build_context(
                context_id=new_context_id(), channel_realization_id=new_channel_realization_id(),
                base_scenario=base_scenario, protocol_scenario=scenario, channel=channel, channel_path=channel_path,
                backend_id=record.backend_id, backend_version=record.provenance.get("backend_version"),
                protocol=record.benchmark_protocol,
            )
            ctx = record.evaluation_context
            record.provenance.update({
                "evaluation_context": ctx.context_id,
                "channel_realization": f"{ctx.channel_realization_id} sha256:{ctx.channel_realization.sha256}",
                "ue_population": f"{ctx.ue_population_id} sha256:{ctx.ue_population.sha256}",
                "traffic_realization": ctx.traffic_realization_id,
            })
            record.runtime.context_seconds = time.perf_counter() - t0
            record.add_event("evaluation_context_frozen")

            failed_code = SystemOptimizationErrorCode.BASELINE_FAILED
            self._stage(record, SystemOptimizationStage.RUNNING_BASELINE)
            evaluator = _ContextEvaluator(self, record, scenario, channel, objective, parameter)
            t0 = time.perf_counter()
            baseline = evaluator.evaluate_baseline()
            record.runtime.baseline_seconds = time.perf_counter() - t0
            if baseline.status is CandidateStatus.FAILED:
                raise _OptimizationFailed(baseline.error.message if baseline.error else "baseline failed",
                                          BASELINE_CANDIDATE_ID)

            failed_code = SystemOptimizationErrorCode.OPTIMIZATION_FAILED
            t1 = time.perf_counter()
            problem = _SystemSearchProblem(record, objective.info.direction)
            search = optimizer.optimize(problem, evaluator)
            record.runtime.candidate_evaluation_seconds = time.perf_counter() - t1
            if all(c.status is CandidateStatus.FAILED for c in record.candidates):
                failed_code = SystemOptimizationErrorCode.ALL_CANDIDATES_FAILED
                raise _OptimizationFailed("All candidates failed; no comparison is possible", None)

            self._stage(record, SystemOptimizationStage.SELECTING_BEST)
            best = next(c for c in record.all_evaluations() if c.candidate_id == search.best_candidate_id)
            record.best_candidate_id = best.candidate_id
            record.comparison = build_system_comparison(
                baseline, best, objective.info.direction,
                record.benchmark_protocol.observed_variability.relative_percent,
            )
            record.fairness = fairness_report(ctx, record.all_evaluations(), evaluator.experiments)
            record.warnings = self._warnings(record)
            record.add_event("best_candidate_selected", best.candidate_id, best.experiment_id)

            failed_code = SystemOptimizationErrorCode.EVIDENCE_EXPORT_FAILED
            self._stage(record, SystemOptimizationStage.PERSISTING_EVIDENCE)
            record.runtime.total_seconds = time.perf_counter() - t_start
            record.artifacts = export_evidence(self._store.artifact_dir(record.optimization_id), record)
            record.finished_at = utc_now()
            record.progress.stage = SystemOptimizationStage.COMPLETED
            record.transition(OptimizationStatus.SUCCEEDED)
            record.add_event("optimization_completed")
        except Exception as exc:  # noqa: BLE001 - 任何失败都持久化为 FAILED，保留已有证据
            logger.exception("%s system optimization failed", record.optimization_id)
            self._fail(record, failed_code, exc)
            if evaluator is not None and record.evaluation_context is not None:
                record.fairness = fairness_report(record.evaluation_context, record.all_evaluations(),
                                                  evaluator.experiments)
            try:
                record.artifacts = export_evidence(self._store.artifact_dir(record.optimization_id), record)
            except Exception:  # noqa: BLE001
                logger.exception("%s evidence export after failure failed", record.optimization_id)
        finally:
            record.runtime.total_seconds = time.perf_counter() - t_start
            self._store.update(record)
        logger.info("%s %s total=%.1f s", record.optimization_id, record.status.name, record.runtime.total_seconds)

    @staticmethod
    def _warnings(record: SystemOptimizationRecord) -> list[str]:
        warnings = []
        comparison = record.comparison
        assert comparison is not None
        if not comparison.improved:
            warnings.append("No candidate improved the objective. / 当前候选范围内未发现优于基线的配置。")
        if comparison.within_observed_variability:
            warnings.append(
                "Improvement is within observed simulation variability "
                f"(±{comparison.observed_variability_percent:.2f}%). / 改善幅度处于已观测仿真波动范围内。"
            )
        for change in comparison.kpi_changes:
            if change.direction == "decrease":
                rel = f"{change.relative_change_percent:+.2f}%" if change.relative_change_percent is not None else ""
                warnings.append(f"{change.kpi_id} decreased {rel} ({change.baseline:.3f} → {change.best:.3f} Mbps)")
        failed = [c.candidate_id for c in record.candidates if c.status is CandidateStatus.FAILED]
        if failed:
            warnings.append(f"Failed candidates preserved: {', '.join(failed)}")
        if record.fairness is not None and not record.fairness.fair:
            bad = [c.id for c in record.fairness.checks if not c.passed]
            warnings.append(f"Fair evaluation conditions NOT met: {', '.join(bad)}")
        return warnings

    @staticmethod
    def _fail(record: SystemOptimizationRecord, code: SystemOptimizationErrorCode, exc: Exception) -> None:
        record.error = SystemOptimizationError(
            code=code, message=str(exc) or type(exc).__name__, type=type(exc).__name__,
            failed_candidate_id=exc.candidate_id if isinstance(exc, _OptimizationFailed) else None,
        )
        record.finished_at = utc_now()
        record.progress.stage = SystemOptimizationStage.FAILED
        record.transition(OptimizationStatus.FAILED)
        record.add_event("optimization_failed", record.error.failed_candidate_id)


class _OptimizationFailed(Exception):
    def __init__(self, message: str, candidate_id: str | None) -> None:
        super().__init__(message)
        self.candidate_id = candidate_id

