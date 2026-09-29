from __future__ import annotations

from pathlib import Path
from typing import Any

from algorithm_benchmark.association_optimization import AssociationOptimizationService
from algorithm_benchmark.service import BenchmarkService
from user_association.backend import MultiCellBackend
from user_association.service import UserAssociationService


class UserAssociationEvaluationAdapter:
    problem_type = "user_association"

    def execute(self, *, repo_root: Path, record: dict[str, Any], package: dict[str, Any], algorithm: type) -> dict[str, Any]:
        scenario = UserAssociationService(repo_root / "configs").load(record["scenario_id"])
        backend = MultiCellBackend(scenario)
        benchmark_service = BenchmarkService(repo_root / "configs", repo_root / "reference" / "benchmarks")
        channel = benchmark_service._load_day8_frozen_channel(scenario, backend)
        params = dict(record["parameters"])
        seed = int(params.get("seed", scenario.seed))
        return {
            "execution": AssociationOptimizationService().run(
                algorithm(), scenario, backend, record["evaluation_budget"], seed, record["run_id"],
                algorithm_hyperparameters=params,
            ),
            "channel": channel,
        }
