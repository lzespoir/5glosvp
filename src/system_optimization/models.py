"""
系统级优化领域模型 / System optimization domain models.

OptimizationRun（系统级）= 冻结的 CommonEvaluationContext + 基线 + 多个候选系统实验。
本模块不依赖任何仿真引擎。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from algorithms import (
    AlgorithmCategory,
    AlgorithmTrace,
    HyperparameterValue,
    ParameterSpace,
    StopReason,
)
from optimization.models import ObjectiveSpec, OptimizationCandidate, OptimizationStatus
from optimization.parameters import ParameterDefinition, ParameterValue

SYSTEM_OPTIMIZATION_ID_PATTERN = re.compile(r"^OPT-[0-9A-F]{8}$")
PROBLEM_TYPE_SYSTEM = "system"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def new_context_id() -> str:
    return _short_id("CTX")


def new_channel_realization_id() -> str:
    return _short_id("CH")


def ue_population_id_for(ue_hash: str) -> str:
    """UE population id 由内容哈希派生：相同 UE 集合 → 相同 id。"""
    return f"UEP-{ue_hash[:8].upper()}"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Benchmark protocol
# ---------------------------------------------------------------------------


class AggregationMethod(str, Enum):
    SINGLE_RUN = "single_run"
    MEAN = "mean"


class ObservedVariability(_Strict):
    """已观测的仿真波动（用于提示改善是否处于波动范围内），不是置信区间。"""

    kpi_id: str
    relative_percent: float = Field(ge=0)
    description_zh: str
    description_en: str
    source: str


class BenchmarkProtocol(_Strict):
    """冻结的评价协议；同一 id/version 发布后不得修改，变化必须发布新版本。"""

    protocol_id: str
    version: str
    name_zh: str
    name_en: str
    num_repeats: int = Field(ge=1)
    simulation_slots: int = Field(ge=1)
    warmup_slots: int = Field(ge=0)
    aggregation_method: AggregationMethod
    common_channel: bool
    common_ue_population: bool
    common_traffic: bool
    seed_policy: str
    observed_variability: ObservedVariability
    rationale: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    frozen_at: str
    document: str
    evidence: str


# ---------------------------------------------------------------------------
# Common evaluation context
# ---------------------------------------------------------------------------


class UePopulationEntry(_Strict):
    ue_id: str
    serving_cell_id: str
    position: list[float]


class UePopulation(_Strict):
    ue_population_id: str
    sha256: str
    generator: dict[str, Any] | None = None
    seed: int
    ues: list[UePopulationEntry]


class ChannelRealizationRef(_Strict):
    channel_realization_id: str
    sha256: str
    hash_rule: str
    artifact: str
    arrays: dict[str, dict[str, Any]] = Field(description="key → {shape, dtype}")
    size_bytes: int
    source_scenario_id: str
    seed: int
    provider: str
    provider_versions: dict[str, str | None]
    propagation_fingerprint: str
    mean_channel_gain_db: dict[str, float]
    created_at: str


class TrafficRealization(_Strict):
    traffic_realization_id: str
    sha256: str
    model: dict[str, Any]


class SimulationHorizon(_Strict):
    num_slots: int
    warmup_slots: int
    slot_duration_s: float
    measured_duration_s: float


class CommonEvaluationContext(_Strict):
    """一次优化运行中基线与全部候选共享的冻结评价条件。"""

    context_id: str
    scenario_id: str
    scenario_version: str = Field(description="sha256 of the base scenario definition")
    seed: int
    ue_population: UePopulation
    traffic_realization: TrafficRealization
    channel_realization: ChannelRealizationRef
    simulation_horizon: SimulationHorizon
    backend_id: str
    backend_version: str | None
    scheduler_config: dict[str, Any]
    link_adaptation_config: dict[str, Any]
    power_control_config: dict[str, Any]
    benchmark_protocol_id: str
    benchmark_protocol_version: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def ue_population_id(self) -> str:
        return self.ue_population.ue_population_id

    @property
    def traffic_realization_id(self) -> str:
        return self.traffic_realization.traffic_realization_id

    @property
    def channel_realization_id(self) -> str:
        return self.channel_realization.channel_realization_id


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


class KpiStatistic(BaseModel):
    """重复运行的统计；num_repeats = 1 时 std = 0 且 min = max = mean。"""

    mean: float
    std: float
    min: float
    max: float
    n: int


class FairnessEvidence(BaseModel):
    """从候选实验结果中实际读取（而非从请求复制）的评价条件。"""

    evaluation_context_id: str
    ue_population_sha256: str
    channel_realization_id: str
    channel_sha256: str
    traffic_realization_id: str
    traffic_sha256: str
    num_slots: int
    warmup_slots: int
    backend_id: str
    backend_version: str | None
    channel_reused: bool


class SystemOptimizationCandidate(OptimizationCandidate):
    evaluation_context_id: str | None = None
    experiment_ids: list[str] = Field(default_factory=list)
    network_throughput_mbps: KpiStatistic | None = None
    average_ue_throughput_mbps: KpiStatistic | None = None
    p5_ue_throughput_mbps: KpiStatistic | None = None
    per_ue_throughput_mbps: dict[str, float] = Field(default_factory=dict)
    fairness: FairnessEvidence | None = None
    # Day 7：评价缓存 / 去重（同一上下文 + 同一参数 + 同一后端配置 → 复用已有评价，不再仿真）
    algorithm_round: int | None = None
    evaluation_cache_key: str | None = None
    cache_hit: bool = False
    reused_candidate_id: str | None = None

    @property
    def reused(self) -> bool:
        return self.reused_baseline or self.cache_hit


# ---------------------------------------------------------------------------
# Comparison / fairness
# ---------------------------------------------------------------------------


class KpiChange(BaseModel):
    kpi_id: str
    baseline: float
    best: float
    absolute_change: float
    relative_change_percent: float | None
    direction: Literal["increase", "decrease", "unchanged"]


class SystemComparison(BaseModel):
    """当前目标下最优候选与基线的对比；负向变化原样保留。"""

    baseline_candidate_id: str
    best_candidate_id: str
    baseline_experiment_id: str
    best_experiment_id: str
    baseline_parameters: dict[str, float]
    best_parameters: dict[str, float]
    baseline_objective: float
    best_objective: float
    absolute_improvement: float
    relative_improvement_percent: float | None
    improved: bool
    kpi_changes: list[KpiChange]
    negative_kpi_changes: list[str]
    within_observed_variability: bool
    observed_variability_percent: float
    tie_break_rule: str


class FairnessCheck(BaseModel):
    id: str
    label_zh: str
    label_en: str
    passed: bool
    detail: str


class FairnessReport(BaseModel):
    fair: bool
    checks: list[FairnessCheck]


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


class SystemOptimizationStage(str, Enum):
    CREATED = "created"
    PREPARING_CONTEXT = "preparing_context"
    RUNNING_BASELINE = "running_baseline"
    EVALUATING_CANDIDATE = "evaluating_candidate"
    SELECTING_BEST = "selecting_best"
    PERSISTING_EVIDENCE = "persisting_evidence"
    COMPLETED = "completed"
    FAILED = "failed"


class SystemOptimizationProgress(BaseModel):
    """真实阶段进度（不是百分比估计）。"""

    stage: SystemOptimizationStage = SystemOptimizationStage.CREATED
    completed_candidates: int = 0
    total_candidates: int = 0
    current_candidate_id: str | None = None
    current_parameter_value: float | None = None


class SystemOptimizationErrorCode(str, Enum):
    BASELINE_FAILED = "BASELINE_FAILED"
    ALL_CANDIDATES_FAILED = "ALL_CANDIDATES_FAILED"
    CONTEXT_PREPARATION_FAILED = "CONTEXT_PREPARATION_FAILED"
    EVIDENCE_EXPORT_FAILED = "EVIDENCE_EXPORT_FAILED"
    OPTIMIZATION_FAILED = "OPTIMIZATION_FAILED"
    ALGORITHM_FAILED = "ALGORITHM_FAILED"
    INTERRUPTED = "INTERRUPTED"


class SystemOptimizationError(BaseModel):
    code: SystemOptimizationErrorCode
    message: str
    type: str
    failed_candidate_id: str | None = None


class SystemOptimizationRuntime(BaseModel):
    context_seconds: float | None = None
    baseline_seconds: float | None = None
    candidate_evaluation_seconds: float | None = None
    total_seconds: float | None = None


class SystemOptimizationEvent(BaseModel):
    event: str
    at: str
    candidate_id: str | None = None
    experiment_id: str | None = None


class SystemOptimizationArtifact(BaseModel):
    name: str
    media_type: str
    description: str


class ParameterSpec(_Strict):
    """请求中的一个优化变量：连续（算法生成取值）或离散（枚举候选值）。"""

    id: str
    type: Literal["continuous", "discrete"]
    lower: float | None = None
    upper: float | None = None
    choices: list[float] | None = None


class EvaluationBudget(BaseModel):
    """评价预算由平台执行；每个被接受的算法建议消耗 1 次（包括缓存命中），基线不计入。"""

    max_evaluations: int
    evaluations_used: int = 0
    simulations_run: int = 0
    cache_hits: int = 0
    rejected_suggestions: int = 0


class AlgorithmRunInfo(BaseModel):
    """算法 provenance：一次运行使用的算法身份、配置与源码版本。"""

    algorithm_id: str
    algorithm_version: str
    algorithm_name_en: str
    algorithm_name_zh: str
    algorithm_provider: str
    algorithm_category: AlgorithmCategory
    sdk_version: str
    learning_algorithm: bool
    project_research_deliverable: bool
    purpose_en: str
    purpose_zh: str
    hyperparameters: dict[str, HyperparameterValue]
    auto_configured: bool = Field(description="True when every hyperparameter used its recommended default")
    algorithm_config_hash: str
    parameter_space_hash: str
    source: str
    source_revision: dict[str, str | None]


class SystemOptimizationRecord(BaseModel):
    optimization_id: str
    name: str
    problem_type: Literal["system"] = PROBLEM_TYPE_SYSTEM
    status: OptimizationStatus
    scenario_id: str
    scenario_name_zh: str
    scenario_name_en: str
    backend_id: str
    optimizer_id: str
    optimizer_version: str
    objective: ObjectiveSpec
    parameter: ParameterDefinition
    candidate_values: list[ParameterValue]
    algorithm_hyperparameters: dict[str, ParameterValue] = Field(default_factory=dict)
    baseline_parameters: dict[str, float]
    benchmark_protocol: BenchmarkProtocol
    seed: int
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    evaluation_context: CommonEvaluationContext | None = None
    baseline: SystemOptimizationCandidate | None = None
    candidates: list[SystemOptimizationCandidate] = Field(default_factory=list)
    best_candidate_id: str | None = None
    comparison: SystemComparison | None = None
    fairness: FairnessReport | None = None
    progress: SystemOptimizationProgress = Field(default_factory=SystemOptimizationProgress)
    runtime: SystemOptimizationRuntime = Field(default_factory=SystemOptimizationRuntime)
    provenance: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    artifacts: list[SystemOptimizationArtifact] = Field(default_factory=list)
    error: SystemOptimizationError | None = None
    events: list[SystemOptimizationEvent] = Field(default_factory=list)
    status_history: list[dict[str, str]] = Field(default_factory=list)
    # Day 7 algorithm integration（Day 6 记录中为 None）
    algorithm: AlgorithmRunInfo | None = None
    parameter_space: ParameterSpace | None = None
    evaluation_budget: EvaluationBudget | None = None
    algorithm_trace: AlgorithmTrace | None = None
    stop_reason: StopReason | None = None
    recommendation_matches_best: bool | None = None

    def transition(self, status: OptimizationStatus) -> None:
        self.status = status
        self.status_history.append({"status": status.value, "at": utc_now()})

    def add_event(self, event: str, candidate_id: str | None = None, experiment_id: str | None = None) -> None:
        self.events.append(
            SystemOptimizationEvent(event=event, at=utc_now(), candidate_id=candidate_id, experiment_id=experiment_id)
        )

    def all_evaluations(self) -> list[SystemOptimizationCandidate]:
        return [c for c in [self.baseline, *self.candidates] if c is not None]
