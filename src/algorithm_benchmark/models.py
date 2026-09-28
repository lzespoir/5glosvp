from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BenchmarkAlgorithmCategory(str, Enum):
    ENGINEERING_BASELINE = "engineering_baseline"
    CLASSICAL_OPTIMIZATION = "classical_optimization"
    RESEARCH = "research"
    INTEGRATION_DEMO = "integration_demo"
    EXTERNAL = "external"
    RESEARCH_DEMO = "research_demo"


class AlgorithmCompatibility(Strict):
    algorithm_id: str
    algorithm_version: str
    parameter_types: list[str]
    constraint_types: list[str]
    objective_directions: list[str]
    batch: bool
    iterative_feedback: bool
    training_required: bool
    gradient_required: bool
    black_box_support: bool
    multi_objective_support: bool
    deterministic: bool
    supports_seed: bool
    sdk_version: str
    status: str = "compatible"
    reason: str = ""


class AlgorithmCatalogEntry(Strict):
    algorithm_id: str
    name: str
    version: str
    category: BenchmarkAlgorithmCategory
    provider: str
    learning_algorithm: bool
    training_required: bool
    gradient_required: bool
    black_box_support: bool
    supported_parameter_types: list[str]
    supported_constraint_types: list[str]
    supported_objective_directions: list[str]
    deterministic: bool
    supports_seed: bool
    sdk_version: str
    runnable: bool
    compatibility: AlgorithmCompatibility


class ResearchAlgorithmReference(Strict):
    reference_id: str
    algorithm_family: str
    paper_title: str
    authors: list[str]
    year: int
    problem_types: list[str]
    parameter_types: list[str]
    requires_training: bool
    black_box: bool
    implementation_status: str
    notes: str
    source: str
    doi: str | None = None


class BenchmarkProtocol(Strict):
    protocol_id: str
    version: str
    problem_type: str
    scenario_ids: list[str]
    evaluation_context_policy: str
    objective: dict[str, Any]
    constraints: list[dict[str, Any]]
    kpi_versions: dict[str, str]
    evaluation_budget: int = Field(ge=1)
    time_budget_seconds: float | None = Field(default=None, ge=0)
    initial_solution_policy: str
    seed_policy: str
    repeat_policy: dict[str, Any]
    channel_realization_policy: str
    traffic_realization_policy: str
    aggregation_policy: str
    runtime_measurement_policy: str
    hardware_environment_policy: str

    def sha256(self) -> str:
        raw = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


class BenchmarkRun(Strict):
    benchmark_run_id: str
    benchmark_id: str
    algorithm_id: str
    algorithm_version: str
    algorithm_config: dict[str, Any]
    seed: int
    optimization_id: str
    status: str
    runtime: dict[str, float | None]
    evaluations_used: int
    best_candidate: dict[str, Any]
    feasible: bool
    stop_reason: str
    convergence: list[dict[str, Any]]
    verification: dict[str, Any]


class BenchmarkResult(Strict):
    benchmark_run_id: str
    algorithm_id: str
    algorithm_version: str
    category: str
    learning_algorithm: bool
    seed: int
    objective: float | None
    network_throughput_mbps: float
    average_ue_throughput_mbps: float
    p5_ue_throughput_mbps: float
    feasible: bool
    evaluations_used: int
    runtime: dict[str, float | None]
    stop_reason: str
    verification: str
    comparison_eligible: bool
    comparison_reason: str


class Benchmark(Strict):
    benchmark_id: str
    name: str
    problem_id: str
    scenario_set: list[str]
    protocol_id: str
    protocol_hash: str
    algorithm_configs: list[dict[str, Any]]
    status: str
    created_at: str
    completed_at: str | None = None
    provenance: dict[str, Any]
    runs: list[BenchmarkRun] = Field(default_factory=list)
    results: list[BenchmarkResult] = Field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
