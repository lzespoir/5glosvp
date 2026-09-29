from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from user_association.backend import FrozenMultiCellChannel, MultiCellBackend

from .algorithms import RUNNABLE_ALGORITHMS
from .association_optimization import AssociationOptimizationService
from .models import (
    AlgorithmCatalogEntry, AlgorithmCompatibility, Benchmark, BenchmarkAlgorithmCategory,
    BenchmarkProtocol, BenchmarkResult, BenchmarkRun, utc_now,
)
from .research_catalog import RESEARCH_CATALOG
from .provenance import runtime_environment
from user_association.service import UserAssociationService


class BenchmarkService:
    benchmark_id = "BENCH-DAY9-3C12U001"

    def __init__(self, configs_dir: Path, reference_dir: Path, git_commit: str | None = None) -> None:
        self.configs_dir = Path(configs_dir)
        self.reference_dir = Path(reference_dir)
        self.git_commit = git_commit
        self.optimization = AssociationOptimizationService()

    def protocol(self) -> BenchmarkProtocol:
        return BenchmarkProtocol(
            protocol_id="ALGORITHM_BENCHMARK_V0_1", version="0.1",
            problem_type="USER_ASSOCIATION", scenario_ids=["MULTICELL-DEMO-001"],
            evaluation_context_policy="same frozen scenario, channel, traffic and candidate neighborhood",
            objective={"id": "NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1", "direction": "maximize", "version": "0.1"},
            constraints=[{"id": "P5_FLOOR", "operator": ">=", "value": "baseline_p5"}],
            kpi_versions={"network_throughput": "0.1", "average_ue_throughput": "0.1", "p5_ue_throughput": "0.1"},
            evaluation_budget=8, time_budget_seconds=None,
            initial_solution_policy="DAY8_BASELINE_ASSOCIATION",
            seed_policy="fixed scenario seed per repeat; random search records derived seed",
            repeat_policy={"num_repeats": 1, "confidence_intervals": False},
            channel_realization_policy="CH-MULTICELL-FBD449D7 frozen and reused",
            traffic_realization_policy="full_buffer deterministic scenario traffic",
            aggregation_policy="single repeat; no statistical aggregation",
            runtime_measurement_policy="ALGORITHM_RUNTIME_V0_1 split optimizer overhead and simulator evaluation",
            hardware_environment_policy="record current Python/Sionna/Torch/hardware provenance",
        )

    def catalog(self) -> list[AlgorithmCatalogEntry]:
        out: list[AlgorithmCatalogEntry] = []
        for cls in RUNNABLE_ALGORITHMS:
            meta = cls.metadata()
            category = BenchmarkAlgorithmCategory(meta.category.value)
            compatibility = AlgorithmCompatibility(
                algorithm_id=meta.algorithm_id, algorithm_version=meta.version,
                parameter_types=["categorical_vector"], constraint_types=["p5_floor"],
                objective_directions=["maximize"], batch=meta.capabilities.supports_batch_suggestions,
                iterative_feedback=meta.capabilities.supports_iterative_feedback,
                training_required=False, gradient_required=False, black_box_support=True,
                multi_objective_support=meta.capabilities.supports_multi_objective,
                deterministic=meta.algorithm_id != "random_search_v0_1", supports_seed=True,
                sdk_version=meta.sdk_version,
            )
            out.append(AlgorithmCatalogEntry(
                algorithm_id=meta.algorithm_id, name=meta.name_en, version=meta.version,
                category=category, provider=meta.provider, learning_algorithm=meta.learning_algorithm,
                training_required=False, gradient_required=False, black_box_support=True,
                supported_parameter_types=["categorical_vector"], supported_constraint_types=["p5_floor"],
                supported_objective_directions=["maximize"], deterministic=compatibility.deterministic,
                supports_seed=True, sdk_version=meta.sdk_version, runnable=True, compatibility=compatibility,
            ))
        return out

    def research_catalog(self) -> list[dict[str, Any]]:
        return [x.model_dump(mode="json") for x in RESEARCH_CATALOG]

    def run(self, scenario_id: str = "MULTICELL-DEMO-001", budget: int | None = None) -> Benchmark:
        protocol = self.protocol()
        if budget is not None:
            protocol = protocol.model_copy(update={"evaluation_budget": budget})
        scenarios = UserAssociationService(self.configs_dir).load(scenario_id)
        backend = MultiCellBackend(scenarios)
        channel = self._load_day8_frozen_channel(scenarios, backend)
        benchmark_id = self.benchmark_id
        run_records: list[BenchmarkRun] = []
        result_records: list[BenchmarkResult] = []
        algorithm_configs = []
        for cls in RUNNABLE_ALGORITHMS:
            meta = cls.metadata()
            seed = scenarios.seed
            algorithm_configs.append({"algorithm_id": meta.algorithm_id, "version": meta.version,
                                      "category": meta.category.value, "learning_algorithm": meta.learning_algorithm,
                                      "seed": seed, "config": {"seed": seed} if meta.algorithm_id == "random_search_v0_1" else {}})
            run_id = f"BRUN-{meta.algorithm_id.upper().replace('_', '-')}-R01"
            execution = self.optimization.run(cls(), scenarios, backend, protocol.evaluation_budget, seed, run_id)
            trace = execution["trace"]
            actual = execution["actual"]
            convergence = self._convergence(trace, actual)
            best = execution["best"]
            run_records.append(BenchmarkRun(
                benchmark_run_id=run_id, benchmark_id=benchmark_id, algorithm_id=meta.algorithm_id,
                algorithm_version=meta.version, algorithm_config=algorithm_configs[-1]["config"], seed=seed,
                optimization_id=execution["optimization_id"], status="completed",
                runtime=execution["runtime"], evaluations_used=trace.evaluations_used,
                best_candidate={"candidate_id": execution["best_candidate_id"], **best.model_dump(mode="json")},
                feasible=best.feasible, stop_reason=(trace.stop_reason.value if trace.stop_reason else "unknown"),
                convergence=convergence,
                verification={"protocol_hash": protocol.sha256(), "channel_hash": channel.channel_hash,
                              "independent_verified": False},
            ))
            result_records.append(BenchmarkResult(
                benchmark_run_id=run_id, algorithm_id=meta.algorithm_id, algorithm_version=meta.version,
                category=meta.category.value, learning_algorithm=meta.learning_algorithm, seed=seed,
                objective=best.network_throughput_mbps if best.feasible else None,
                network_throughput_mbps=best.network_throughput_mbps,
                average_ue_throughput_mbps=best.average_ue_throughput_mbps,
                p5_ue_throughput_mbps=best.p5_ue_throughput_mbps, feasible=best.feasible,
                evaluations_used=trace.evaluations_used, runtime=execution["runtime"],
                stop_reason=(trace.stop_reason.value if trace.stop_reason else "unknown"),
                verification="pending independent verifier", comparison_eligible=True,
                comparison_reason="same protocol/scenario/baseline/channel/objective/constraint/KPI/budget",
            ))
        benchmark = Benchmark(
            benchmark_id=benchmark_id, name="Day 9 User Association Algorithm Benchmark",
            problem_id="USER_ASSOCIATION", scenario_set=[scenario_id], protocol_id=protocol.protocol_id,
            protocol_hash=protocol.sha256(), algorithm_configs=algorithm_configs, status="completed",
            created_at=utc_now(), completed_at=utc_now(),
            provenance={"data_source": "simulation", "provider": "nvidia_sionna", "verification": "pending",
                        "evidence_level": "simulation_evidence", "channel_hash": channel.channel_hash,
                        "channel_realization_id": "CH-MULTICELL-" + channel.channel_hash[:8].upper(),
                        "git_commit": self.git_commit, "repeats": 1, "comparison_eligible": True,
                        "runtime_environment": runtime_environment(),
                        "runtime_semantics": {
                            "measured_fields": ["total_wall_time", "simulation_evaluation_time", "optimizer_overhead_time"],
                            "total_wall_time_includes": "simulator evaluations and optimizer overhead",
                            "algorithm_compute_only": False,
                        }},
            runs=run_records, results=result_records,
        )
        self._export(benchmark, protocol, channel.provider_versions)
        return benchmark

    def _load_day8_frozen_channel(self, scenario: Any, backend: MultiCellBackend) -> FrozenMultiCellChannel:
        """Restore Day 8's persisted link artifact; never retrace for a benchmark run."""
        source = self.reference_dir.parent / "user_association" / "OPT-9748F677" / "optimization.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        persisted = data["scenario"]
        if persisted["scenario_id"] != scenario.scenario_id or persisted["cells"] != scenario.model_dump(mode="json")["cells"]:
            raise ValueError("Day 8 frozen scenario does not match benchmark scenario")
        cell_ids = [c.cell_id for c in scenario.cells]
        ue_ids = [u.ue_id for u in scenario.ues]
        gains = []
        for ue_id in ue_ids:
            links = {x["cell_id"]: x for x in data["candidate_cells"][ue_id]}
            gains.append([10 ** (float(links[cid]["link_gain_db"]) / 10.0) if cid in links else 0.0 for cid in cell_ids])
        ch = data["channel"]
        channel = FrozenMultiCellChannel(
            scenario_id=scenario.scenario_id, ue_ids=ue_ids, cell_ids=cell_ids,
            gains_linear=__import__("numpy").asarray(gains, dtype=float),
            gains_db=__import__("numpy").where(__import__("numpy").asarray(gains) > 0, 10 * __import__("numpy").log10(__import__("numpy").maximum(gains, 1e-30)), -300.0),
            positions=__import__("numpy").asarray([u.position for u in scenario.ues]),
            channel_hash=ch["sha256"], runtime_seconds=0.0, provider_versions=ch["provider_versions"],
            provenance_hash_version="0.1",
        )
        backend.channel = channel
        return channel

    @staticmethod
    def _convergence(trace: Any, actual: dict[str, Any]) -> list[dict[str, Any]]:
        elapsed = 0.0
        best: float | None = None
        rows = []
        for item in trace.evaluations:
            evaluation = actual.get(item.candidate_id)
            elapsed += float(evaluation.runtime_seconds if evaluation else 0.0)
            feasible = bool(evaluation and evaluation.feasible)
            if feasible and item.objective is not None:
                best = item.objective if best is None else max(best, item.objective)
            rows.append({"evaluation_index": item.sequence, "elapsed_time": elapsed,
                         "current_objective": item.objective, "best_feasible_objective": best,
                         "current_feasible": feasible, "best_candidate_id": item.best_so_far_candidate_id})
        return rows

    def _export(self, benchmark: Benchmark, protocol: BenchmarkProtocol, provider_versions: dict[str, str | None]) -> None:
        root = self.reference_dir / benchmark.benchmark_id
        root.mkdir(parents=True, exist_ok=True)
        files = {
            "benchmark.json": benchmark.model_dump(mode="json"), "protocol.json": protocol.model_dump(mode="json"),
            "algorithms.json": {"runnable": [x.model_dump(mode="json") for x in self.catalog()], "research": self.research_catalog()},
            "runs.json": [x.model_dump(mode="json") for x in benchmark.runs],
            "comparison.json": [x.model_dump(mode="json") for x in benchmark.results],
            "convergence.json": {x.benchmark_run_id: x.convergence for x in benchmark.runs},
            "verification.json": {"status": "pending_independent_verifier", "comparable": True},
            "evidence-descriptor.json": {"evidence_type": "algorithm_benchmark", "benchmark_id": benchmark.benchmark_id,
                "protocol_id": protocol.protocol_id, "protocol_hash": benchmark.protocol_hash, "run_ids": [x.benchmark_run_id for x in benchmark.runs],
                "verified": False, "verification_status": "pending", "verifier_id": None,
                "verified_at": None, "verification_hash": None,
                "comparison_eligible": True, "comparison_reason": "same frozen protocol",
                "acceptance_eligible": False, "data_source": "simulation", "provider": "nvidia_sionna",
                "verification": "pending", "evidence_level": "simulation_evidence"},
            "provenance.json": {**benchmark.provenance, "provider_versions": provider_versions},
        }
        for name, value in files.items():
            (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "README.md").write_text(
            "# Day 9 Algorithm Benchmark\n\nPurpose: Algorithm Benchmark and Comparative Validation\n\n"
            "Problem: User Association\nData Source: Simulation\nVerification: Independent\n"
            "Comparison Eligible: YES\nAcceptance Eligible: NO\n\n"
            "This reference compares compatible algorithms under one frozen protocol. It does not declare an overall winner.\n",
            encoding="utf-8",
        )
        (root / "convergence.svg").write_text(self._svg(benchmark), encoding="utf-8")

    @staticmethod
    def _svg(benchmark: Benchmark) -> str:
        width, height = 720, 300
        lines = []
        for index, run in enumerate(benchmark.runs):
            points = []
            for row in run.convergence:
                y_value = row["best_feasible_objective"] or 0.0
                points.append(f"{50 + row['evaluation_index'] * 70},{260 - min(220, y_value / 10)}")
            lines.append(f'<polyline fill="none" stroke="hsl({index * 110},65%,40%)" stroke-width="3" points="{" ".join(points)}"/>')
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="white"/><text x="20" y="24">Best feasible objective vs evaluations</text>{"".join(lines)}</svg>'
