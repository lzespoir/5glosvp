"""
系统级优化服务 / System optimization service.

    Algorithm (SDK) → AlgorithmDriver → 评价回调 → SystemOptimizationService → SystemExperimentService → Backend

职责：校验问题与算法兼容性 → 冻结评价上下文（一次 RT 信道实现）→ 基线 → 算法迭代
（suggest → 同一上下文评价 → observe，平台执行预算与缓存去重）→ KPI → 目标值 → 选择最优
→ 对比（含次要 KPI 负向变化）→ 公平性检查 → 持久化与证据。
算法与目标函数都不接触仿真引擎；本服务只通过 SystemExperimentService 运行实验。
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np
from pydantic import ValidationError

from algorithms import (
    ALGORITHM_SDK_VERSION,
    Algorithm,
    AlgorithmCompatibilityError,
    AlgorithmDriver,
    AlgorithmMetadata,
    AlgorithmProblem,
    AlgorithmRegistry,
    CompatibilityReport,
    EvaluationResult,
    EvaluationStatus,
    HyperparameterValue,
    ParameterSpace,
    StopReason,
    canonical_sha256,
    check_compatibility,
)
from evaluation.kpi import (
    AVG_UE_THROUGHPUT_V0_1,
    NETWORK_THROUGHPUT_V0_1,
    P5_UE_THROUGHPUT_V0_1,
    UE_THROUGHPUT_V0_1,
)
from evidence import EvidenceDescriptor
from optimization.errors import InvalidParameterSpaceError
from optimization.models import (
    BASELINE_CANDIDATE_ID,
    CandidateError,
    CandidateStatus,
    Direction,
    ObjectiveSpec,
    OptimizationStatus,
    candidate_id_for,
    new_optimization_id,
)
from optimization.parameters import ParameterDefinition, ParameterType, ParameterValue, ValueGeneration
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
from .cache import EvaluationCache, evaluation_cache_key
from .context import apply_protocol, build_context, context_link, fairness_evidence, fairness_report
from .errors import (
    SystemOptimizationArtifactNotFoundError,
    SystemOptimizationBusyError,
    SystemOptimizationNotFoundError,
    UnsupportedProblemTypeError,
)
from .evidence import describe_system_optimization
from .models import (
    PROBLEM_TYPE_SYSTEM,
    AlgorithmRunInfo,
    BenchmarkProtocol,
    EvaluationBudget,
    KpiChange,
    KpiStatistic,
    ParameterSpec,
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
DEFAULT_EVALUATION_BUDGET = 8
MAX_EVALUATION_BUDGET = 12
RELATIVE_EPS = 1e-9
TIE_BREAK_RULE = "Equal objective → baseline parameter value first, then candidate definition order"
SECONDARY_KPIS = (NETWORK_THROUGHPUT_V0_1, AVG_UE_THROUGHPUT_V0_1, P5_UE_THROUGHPUT_V0_1)
KPI_FIELDS = {
    NETWORK_THROUGHPUT_V0_1: "network_throughput_mbps",
    AVG_UE_THROUGHPUT_V0_1: "average_ue_throughput_mbps",
    P5_UE_THROUGHPUT_V0_1: "p5_ue_throughput_mbps",
}
EVIDENCE_API_PREFIX = "/api/v1"

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


def select_best(record: SystemOptimizationRecord, direction: Direction) -> SystemOptimizationCandidate:
    """平台最优选择（与算法无关）：目标值最优；相同时基线参数值优先，其次候选顺序。"""
    scored = [c for c in record.all_evaluations() if c.objective is not None]
    if not scored:
        raise ValueError("No evaluated candidates to select from")
    sign = 1.0 if direction is Direction.MAXIMIZE else -1.0

    def key(c: SystemOptimizationCandidate) -> tuple[float, ...]:
        assert c.objective is not None
        is_baseline_value = c.parameters == record.baseline_parameters
        return (sign * c.objective.value, 1.0 if is_baseline_value else 0.0, -float(c.iteration))

    return max(scored, key=key)


def evaluation_result(c: SystemOptimizationCandidate, direction: Direction) -> EvaluationResult:
    """平台候选 → 算法看到的规范化评价结果（不含实验 / 产物路径）。"""
    secondary = {k: getattr(c, f).mean for k, f in KPI_FIELDS.items() if getattr(c, f) is not None}
    return EvaluationResult(
        candidate_id=c.candidate_id, parameters=dict(c.parameters),
        objective=c.objective.value if c.objective else None, objective_direction=direction,
        secondary_metrics=secondary,
        status=EvaluationStatus.EVALUATED if c.status is CandidateStatus.EVALUATED else EvaluationStatus.FAILED,
        runtime_seconds=c.runtime_seconds, cache_hit=c.cache_hit,
    )


class _ContextEvaluator:
    """在同一冻结上下文中运行基线 / 候选；缓存去重；候选失败被记录后继续（不抛出）。"""

    def __init__(
        self,
        service: SystemOptimizationService,
        record: SystemOptimizationRecord,
        scenario: SystemScenario,
        channel: ChannelRealization,
        objective: SystemObjective,
        parameters: list[SystemParameter],
    ) -> None:
        self._service = service
        self._record = record
        self._scenario = scenario
        self._channel = channel
        self._objective = objective
        self._parameters = {p.definition.id: p for p in parameters}
        self.cache = EvaluationCache()
        self.experiments: dict[str, SystemExperimentRecord] = {}

    def _cache_key(self, parameters: dict[str, ParameterValue]) -> str:
        record = self._record
        assert record.evaluation_context is not None
        return evaluation_cache_key(record.evaluation_context, parameters, record.backend_id,
                                    record.provenance.get("backend_version"))

    def evaluate_baseline(self) -> SystemOptimizationCandidate:
        params = dict(self._record.baseline_parameters)
        candidate = self._run(BASELINE_CANDIDATE_ID, 0, params, is_baseline=True)
        candidate.evaluation_cache_key = self._cache_key(params)
        self.cache.put(candidate.evaluation_cache_key, candidate)
        self._record.baseline = candidate
        self._service.persist_event(self._record, "baseline_evaluated", candidate)
        return candidate

    def evaluate(self, parameters: dict[str, ParameterValue], round_: int) -> SystemOptimizationCandidate:
        record = self._record
        budget = record.evaluation_budget
        assert budget is not None
        iteration = len(record.candidates) + 1
        candidate_id = candidate_id_for(iteration)
        progress = record.progress
        progress.stage = SystemOptimizationStage.EVALUATING_CANDIDATE
        progress.current_candidate_id = candidate_id
        progress.current_parameter_value = float(next(iter(parameters.values())))  # type: ignore[arg-type]
        self._service.persist(record)
        key = self._cache_key(parameters)
        hit = self.cache.get(key)
        if hit is not None:
            # 同一冻结上下文 + 同一参数 + 同一后端配置 + 确定性 SYS → 复用已有评价，不再仿真
            candidate = hit.model_copy(deep=True, update={
                "candidate_id": candidate_id, "iteration": iteration, "is_baseline": False,
                "reused_baseline": hit.is_baseline, "cache_hit": True, "reused_candidate_id": hit.candidate_id,
                "runtime_seconds": 0.0, "algorithm_round": round_, "evaluation_cache_key": key,
            })
            budget.cache_hits += 1
        else:
            candidate = self._run(candidate_id, iteration, parameters, is_baseline=False)
            candidate.algorithm_round = round_
            candidate.evaluation_cache_key = key
            budget.simulations_run += 1
            self.cache.put(key, candidate)
        budget.evaluations_used += 1
        record.candidates.append(candidate)
        progress.completed_candidates += 1
        event = "candidate_failed" if candidate.status is CandidateStatus.FAILED else "candidate_evaluated"
        self._service.persist_event(record, event, candidate)
        return candidate

    def _run(self, candidate_id: str, iteration: int, parameters: dict[str, ParameterValue],
             is_baseline: bool) -> SystemOptimizationCandidate:
        record = self._record
        context = record.evaluation_context
        assert context is not None
        scenario = self._scenario
        for pid, value in parameters.items():
            scenario = self._parameters[pid].apply(scenario, float(value))  # type: ignore[arg-type]
        label_params = ", ".join(f"{k}={float(v):g}" for k, v in parameters.items())  # type: ignore[arg-type]
        protocol = record.benchmark_protocol
        candidate = SystemOptimizationCandidate(
            candidate_id=candidate_id, iteration=iteration,
            parameters={k: float(v) for k, v in parameters.items()},  # type: ignore[arg-type]
            status=CandidateStatus.EVALUATED, is_baseline=is_baseline, evaluation_context_id=context.context_id,
        )
        t0 = time.perf_counter()
        experiments: list[SystemExperimentRecord] = []
        try:
            for repeat in range(protocol.num_repeats):
                label = "baseline" if is_baseline else candidate_id
                suffix = f" · repeat {repeat + 1}/{protocol.num_repeats}" if protocol.num_repeats > 1 else ""
                exp = self._service.experiments.run_in_context(
                    f"{record.optimization_id} {label} · {label_params}{suffix}",
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
        algorithms: AlgorithmRegistry,
        objectives: SystemObjectiveRegistry,
        protocols: BenchmarkProtocolRegistry,
        parameters: SystemParameterCatalog,
        git_commit: str | None = None,
        max_candidates: int = MAX_SYSTEM_CANDIDATES,
        max_evaluations: int = MAX_EVALUATION_BUDGET,
        runner: Runner = _thread_runner,
    ) -> None:
        self.experiments = experiments
        self._store = store
        self._algorithms = algorithms
        self._objectives = objectives
        self._protocols = protocols
        self._parameters = parameters
        self._git_commit = git_commit
        self._max_candidates = max_candidates
        self._max_evaluations = max_evaluations
        self._runner = runner
        self._busy = threading.Lock()
        self._recover_interrupted()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def max_candidates(self) -> int:
        return self._max_candidates

    @property
    def max_evaluations(self) -> int:
        return self._max_evaluations

    @property
    def algorithms(self) -> AlgorithmRegistry:
        return self._algorithms

    def list_optimizers(self) -> list[AlgorithmMetadata]:
        return [m for m in self._algorithms.list() if PROBLEM_TYPE_SYSTEM in m.supported_problem_types]

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

    def list_all(self) -> list[SystemOptimizationRecord]:
        return self._store.list_all()

    def evidence(self, record: SystemOptimizationRecord) -> EvidenceDescriptor:
        return describe_system_optimization(record, EVIDENCE_API_PREFIX)

    def resolve_artifact(self, optimization_id: str, name: str):
        record = self.get(optimization_id)
        known = {a.name: a for a in record.artifacts}
        if name not in known:
            raise SystemOptimizationArtifactNotFoundError(f"Artifact not found: {name!r}")
        return known[name], self._store.resolve_artifact(optimization_id, name)

    # ------------------------------------------------------------------
    # Problem construction / compatibility
    # ------------------------------------------------------------------

    def build_parameter_space(self, specs: list[ParameterSpec]) -> tuple[ParameterSpace, list[SystemParameter]]:
        """请求中的变量 → 平台 ParameterSpace（值域来自参数目录，只允许收窄，不允许放宽）。"""
        if not specs:
            raise InvalidParameterSpaceError("At least one optimization variable is required")
        definitions: list[ParameterDefinition] = []
        parameters: list[SystemParameter] = []
        for spec in specs:
            parameter = self._parameters.get(spec.id)
            if parameter.affects_propagation:
                raise InvalidParameterSpaceError(
                    f"Parameter '{spec.id}' changes propagation; it cannot share a frozen channel realization"
                )
            base = parameter.definition.model_dump()
            if spec.type == "discrete":
                if spec.lower is not None or spec.upper is not None:
                    raise InvalidParameterSpaceError(f"discrete parameter '{spec.id}' takes choices, not bounds")
                values = self._validate_candidates(parameter, spec.choices or [])
                data = {**base, "type": ParameterType.DISCRETE, "choices": values, "default": None,
                        "value_generation": [ValueGeneration.ENUMERATED]}
            else:
                if spec.choices:
                    raise InvalidParameterSpaceError(f"continuous parameter '{spec.id}' takes bounds, not choices")
                lo = spec.lower if spec.lower is not None else parameter.recommended_search_bounds[0]
                hi = spec.upper if spec.upper is not None else parameter.recommended_search_bounds[1]
                try:
                    parameter.definition.validate_value(lo)
                    parameter.definition.validate_value(hi)
                except ValueError as e:
                    raise InvalidParameterSpaceError(f"search bounds must lie inside the parameter domain: {e}") from e
                default = base.get("default")
                data = {**base, "bounds": {"lower": lo, "upper": hi},
                        "default": default if isinstance(default, (int, float)) and lo <= default <= hi else None,
                        "value_generation": [ValueGeneration.ALGORITHM_GENERATED]}
            try:
                definitions.append(ParameterDefinition.model_validate(data))
            except ValidationError as e:
                raise InvalidParameterSpaceError(str(e.errors()[0].get("msg", e))) from e
            parameters.append(parameter)
        try:
            space = ParameterSpace(parameters=definitions, metadata={"source": "system parameter catalog"})
        except ValidationError as e:
            raise InvalidParameterSpaceError(str(e.errors()[0].get("msg", e))) from e
        return space, parameters

    def _default_budget(self, metadata: AlgorithmMetadata, space: ParameterSpace) -> int:
        if not metadata.capabilities.supports_iterative_feedback and all(
            p.type is ParameterType.DISCRETE for p in space.parameters
        ):
            n = 1
            for p in space.parameters:
                n *= len(p.choices or [])
            return n
        return DEFAULT_EVALUATION_BUDGET

    def _problem(
        self,
        space: ParameterSpace,
        objective: SystemObjective,
        baseline_parameters: dict[str, ParameterValue],
        max_evaluations: int,
    ) -> AlgorithmProblem:
        return AlgorithmProblem(
            problem_type=PROBLEM_TYPE_SYSTEM, parameter_space=space, objective_id=objective.info.id,
            objective_direction=objective.info.direction, objective_count=1,
            baseline_parameters=baseline_parameters, max_evaluations=max_evaluations,
        )

    def validate_algorithm(
        self,
        algorithm_id: str,
        parameter_space: list[ParameterSpec],
        objective_id: str,
        algorithm_hyperparameters: dict[str, Any] | None = None,
        max_evaluations: int | None = None,
        scenario_id: str | None = None,
    ) -> CompatibilityReport:
        algorithm = self._algorithms.create(algorithm_id)
        objective = self._objectives.get(objective_id)
        space, parameters = self.build_parameter_space(parameter_space)
        if scenario_id is not None:
            scenario = self.experiments.get_scenario(scenario_id)
            baseline = {p.definition.id: p.read(scenario) for p in parameters}
        else:
            baseline = {p.definition.id: p.definition.default for p in parameters
                        if p.definition.default is not None}
        budget = max_evaluations if max_evaluations is not None else self._default_budget(algorithm.metadata(), space)
        problem = self._problem(space, objective, baseline, budget)  # type: ignore[arg-type]
        return check_compatibility(algorithm, problem, algorithm_hyperparameters or {}, self._max_evaluations)

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
        """Day 6 兼容入口：optimizer_id + 一个参数的离散候选值。"""
        return self.create_run(
            name=name, scenario_id=scenario_id, algorithm_id=optimizer_id, objective_id=objective_id,
            parameter_space=[ParameterSpec(id=parameter_id, type="discrete", choices=list(candidate_values))],
            benchmark_protocol_id=benchmark_protocol_id, backend_id=backend_id,
        )

    def create_run(
        self,
        *,
        name: str,
        scenario_id: str,
        algorithm_id: str,
        objective_id: str,
        parameter_space: list[ParameterSpec],
        benchmark_protocol_id: str,
        algorithm_hyperparameters: dict[str, Any] | None = None,
        max_evaluations: int | None = None,
        backend_id: str | None = None,
    ) -> SystemOptimizationRecord:
        scenario = self.experiments.get_scenario(scenario_id)
        algorithm = self._algorithms.create(algorithm_id)
        meta = algorithm.metadata()
        if PROBLEM_TYPE_SYSTEM not in meta.supported_problem_types:
            raise UnsupportedProblemTypeError(f"Algorithm '{algorithm_id}' does not support system problems")
        objective = self._objectives.get(objective_id)
        protocol = self._protocols.get(benchmark_protocol_id)
        space, parameters = self.build_parameter_space(parameter_space)
        backend = backend_id or scenario.backend
        descriptor, _, health = self.experiments.require_backend(
            backend, Capability.CHANNEL_REUSE, Capability.THROUGHPUT
        )
        baseline_parameters: dict[str, float] = {}
        for p in parameters:
            value = p.read(scenario)
            p.definition.validate_value(value)
            baseline_parameters[p.definition.id] = value
        budget = max_evaluations if max_evaluations is not None else self._default_budget(meta, space)
        problem = self._problem(space, objective, dict(baseline_parameters), budget)
        user_hp = algorithm_hyperparameters or {}
        report = check_compatibility(algorithm, problem, user_hp, self._max_evaluations)
        if not report.compatible:
            raise AlgorithmCompatibilityError(report.errors)
        assert report.resolved_hyperparameters is not None
        hyperparameters = report.resolved_hyperparameters
        run_info = self._run_info(meta, hyperparameters, user_hp, space, budget)
        primary = parameters[0]
        first = space.parameters[0]
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
                optimizer_id=meta.algorithm_id,
                optimizer_version=meta.version,
                objective=ObjectiveSpec(id=obj.id, version=obj.version, direction=obj.direction),
                parameter=primary.definition,
                candidate_values=list(first.choices or []) if first.type is ParameterType.DISCRETE else [],
                algorithm_hyperparameters=hyperparameters,
                baseline_parameters=baseline_parameters,
                benchmark_protocol=protocol,
                seed=scenario.seed,
                created_at=utc_now(),
                algorithm=run_info,
                parameter_space=space,
                evaluation_budget=EvaluationBudget(max_evaluations=budget),
                provenance={
                    "algorithm": meta.algorithm_id,
                    "algorithm_version": meta.version,
                    "algorithm_provider": meta.provider,
                    "algorithm_category": meta.category.value,
                    "sdk_version": meta.sdk_version,
                    "algorithm_config_hash": run_info.algorithm_config_hash,
                    "parameter_space_hash": run_info.parameter_space_hash,
                    "source_revision": run_info.source_revision,
                    "optimizer": meta.algorithm_id,
                    "optimizer_version": meta.version,
                    "optimizer_category": meta.category.value,
                    "learning_algorithm": meta.learning_algorithm,
                    "project_research_deliverable": meta.project_research_deliverable,
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
                    "search_space_source": self._search_space_source(primary, first),
                    "parameter_source": primary.definition.source,
                },
            )
            record.progress.total_candidates = budget
            record.transition(OptimizationStatus.CREATED)
            record.add_event("optimization_created")
            self._store.create(record)
            logger.info("%s CREATED system optimization scenario=%s algorithm=%s budget=%d space=%s",
                        record.optimization_id, scenario_id, meta.algorithm_id, budget, space.ids)
        except BaseException:
            self._busy.release()
            raise

        def job() -> None:
            try:
                self._execute(record, algorithm, problem, objective, parameters, scenario)
            finally:
                self._busy.release()

        self._runner(job)
        return self.get(record.optimization_id)

    def _run_info(
        self,
        meta: AlgorithmMetadata,
        hyperparameters: dict[str, HyperparameterValue],
        user_hyperparameters: dict[str, Any],
        space: ParameterSpace,
        budget: int,
    ) -> AlgorithmRunInfo:
        defaults = {h.id: h.default for h in meta.hyperparameter_schema}
        config = {"algorithm_id": meta.algorithm_id, "algorithm_version": meta.version,
                  "sdk_version": meta.sdk_version, "hyperparameters": hyperparameters, "max_evaluations": budget}
        return AlgorithmRunInfo(
            algorithm_id=meta.algorithm_id, algorithm_version=meta.version, algorithm_name_en=meta.name_en,
            algorithm_name_zh=meta.name_zh, algorithm_provider=meta.provider, algorithm_category=meta.category,
            sdk_version=meta.sdk_version or ALGORITHM_SDK_VERSION, learning_algorithm=meta.learning_algorithm,
            project_research_deliverable=meta.project_research_deliverable, purpose_en=meta.purpose_en,
            purpose_zh=meta.purpose_zh, hyperparameters=hyperparameters,
            auto_configured=not user_hyperparameters or hyperparameters == defaults,
            algorithm_config_hash=canonical_sha256(config), parameter_space_hash=space.sha256(),
            source=meta.source, source_revision={"type": "git_commit", "value": self._git_commit},
        )

    @staticmethod
    def _search_space_source(parameter: SystemParameter, definition: ParameterDefinition) -> str:
        if definition.type is ParameterType.DISCRETE:
            if tuple(definition.choices or []) == parameter.recommended_values:
                return parameter.recommended_values_source
            return "User-specified candidate values in the create request"
        bounds = definition.bounds
        if bounds is not None and (bounds.lower, bounds.upper) == parameter.recommended_search_bounds:
            return parameter.recommended_search_bounds_source
        return "User-specified search bounds in the create request"

    def persist(self, record: SystemOptimizationRecord) -> None:
        self._store.update(record)

    def persist_event(self, record: SystemOptimizationRecord, event: str,
                      candidate: SystemOptimizationCandidate) -> None:
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
                if record.algorithm_trace is not None and record.algorithm_trace.stop_reason is None:
                    record.algorithm_trace.stop_reason = StopReason.CANCELLED
                    record.algorithm_trace.stop_detail = "service restarted before completion"
                    record.stop_reason = StopReason.CANCELLED
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
        algorithm: Algorithm,
        problem: AlgorithmProblem,
        objective: SystemObjective,
        parameters: list[SystemParameter],
        base_scenario: SystemScenario,
    ) -> None:
        t_start = time.perf_counter()
        record.started_at = utc_now()
        record.transition(OptimizationStatus.RUNNING)
        failed_code = SystemOptimizationErrorCode.OPTIMIZATION_FAILED
        evaluator: _ContextEvaluator | None = None
        direction = objective.info.direction
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
            evaluator = _ContextEvaluator(self, record, scenario, channel, objective, parameters)
            t0 = time.perf_counter()
            baseline = evaluator.evaluate_baseline()
            record.runtime.baseline_seconds = time.perf_counter() - t0
            if baseline.status is CandidateStatus.FAILED:
                raise _OptimizationFailed(baseline.error.message if baseline.error else "baseline failed",
                                          BASELINE_CANDIDATE_ID)

            failed_code = SystemOptimizationErrorCode.ALGORITHM_FAILED
            t1 = time.perf_counter()
            ev = evaluator

            def evaluate(point: dict[str, ParameterValue], round_: int) -> EvaluationResult:
                return evaluation_result(ev.evaluate(point, round_), direction)

            def tie_break(result: EvaluationResult) -> tuple[float, ...]:
                iterations = {c.candidate_id: c.iteration for c in record.all_evaluations()}
                is_baseline_value = result.parameters == record.baseline_parameters
                return (1.0 if is_baseline_value else 0.0, -float(iterations.get(result.candidate_id, 0)))

            driver = AlgorithmDriver(algorithm, problem, dict(record.algorithm_hyperparameters), evaluate,
                                     tie_break, on_update=lambda: self.persist(record))
            record.algorithm_trace = driver.trace
            trace = driver.run([evaluation_result(baseline, direction)])
            record.stop_reason = trace.stop_reason
            if record.evaluation_budget is not None:
                record.evaluation_budget.rejected_suggestions = trace.rejected_suggestions
            record.add_event(f"algorithm_stopped_{trace.stop_reason.value if trace.stop_reason else 'unknown'}")
            record.runtime.candidate_evaluation_seconds = time.perf_counter() - t1
            failed_code = SystemOptimizationErrorCode.OPTIMIZATION_FAILED
            if not record.candidates:
                raise _OptimizationFailed("The algorithm produced no candidate evaluations", None)
            if all(c.status is CandidateStatus.FAILED for c in record.candidates):
                failed_code = SystemOptimizationErrorCode.ALL_CANDIDATES_FAILED
                raise _OptimizationFailed("All candidates failed; no comparison is possible", None)

            self._stage(record, SystemOptimizationStage.SELECTING_BEST)
            best = select_best(record, direction)
            record.best_candidate_id = best.candidate_id
            recommended = trace.recommendation.parameters if trace.recommendation else None
            record.recommendation_matches_best = None if recommended is None else recommended == best.parameters
            record.comparison = build_system_comparison(
                baseline, best, direction, record.benchmark_protocol.observed_variability.relative_percent,
            )
            record.fairness = fairness_report(ctx, record.all_evaluations(), evaluator.experiments)
            record.warnings = self._warnings(record)
            record.add_event("best_candidate_selected", best.candidate_id, best.experiment_id)

            failed_code = SystemOptimizationErrorCode.EVIDENCE_EXPORT_FAILED
            self._stage(record, SystemOptimizationStage.PERSISTING_EVIDENCE)
            record.runtime.total_seconds = time.perf_counter() - t_start
            record.finished_at = utc_now()
            record.progress.stage = SystemOptimizationStage.COMPLETED
            record.transition(OptimizationStatus.SUCCEEDED)
            record.artifacts = self._export(record)
            record.add_event("optimization_completed")
        except Exception as exc:  # noqa: BLE001 - 任何失败都持久化为 FAILED，保留已有证据
            logger.exception("%s system optimization failed", record.optimization_id)
            self._fail(record, failed_code, exc)
            if evaluator is not None and record.evaluation_context is not None:
                record.fairness = fairness_report(record.evaluation_context, record.all_evaluations(),
                                                  evaluator.experiments)
            if record.algorithm_trace is not None:
                record.stop_reason = record.algorithm_trace.stop_reason or StopReason.FAILED
            try:
                record.artifacts = self._export(record)
            except Exception:  # noqa: BLE001
                logger.exception("%s evidence export after failure failed", record.optimization_id)
        finally:
            record.runtime.total_seconds = time.perf_counter() - t_start
            self._store.update(record)
        logger.info("%s %s total=%.1f s", record.optimization_id, record.status.name, record.runtime.total_seconds)

    def _export(self, record: SystemOptimizationRecord):
        metadata = self._algorithms.metadata(record.optimizer_id) if record.algorithm is not None else None
        return export_evidence(self._store.artifact_dir(record.optimization_id), record, metadata,
                               self.evidence(record))

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
