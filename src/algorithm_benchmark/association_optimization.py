from __future__ import annotations

import time
import uuid
from typing import Any

from algorithms.compatibility import check_compatibility
from algorithms.driver import AlgorithmDriver
from algorithms.sdk import Algorithm, AlgorithmProblem, ConstraintResult, EvaluationResult, EvaluationStatus
from optimization.models import Direction
from optimization.parameters import ParameterDefinition, ParameterRole, ParameterType, ParameterValue
from algorithms.parameter_space import ParameterSpace
from user_association.backend import MultiCellBackend
from user_association.models import Association, MultiCellScenario

from .algorithms import ASSOCIATION_PARAMETER, PROBLEM_TYPE


class AssociationOptimizationService:
    """OptimizationService adapter for Day 9 association benchmarks.

    The benchmark layer owns orchestration; this service owns the SDK driver and
    the shared frozen-context evaluator. Algorithms never access the backend.
    """

    def run(self, algorithm: Algorithm, scenario: MultiCellScenario, backend: MultiCellBackend,
            budget: int, seed: int, benchmark_run_id: str,
            algorithm_hyperparameters: dict[str, Any] | None = None) -> dict[str, Any]:
        wall_start = time.perf_counter()
        channel = backend.realize_channel()
        candidate_cells = backend.candidate_cells()
        baseline = backend.baseline()
        baseline_eval = backend.evaluate(baseline, p5_floor=None, channel_reused=True)
        ue_ids = list(channel.ue_ids)
        choices: list[list[str]] = [baseline.vector(ue_ids)]
        for ue_id in ue_ids:
            from_cell = baseline.assignments[ue_id]
            for candidate in candidate_cells[ue_id]:
                if candidate.cell_id == from_cell:
                    continue
                vector = baseline.vector(ue_ids)
                vector[ue_ids.index(ue_id)] = candidate.cell_id
                choices.append(vector)
        definition = ParameterDefinition(
            id=ASSOCIATION_PARAMETER, name_zh="用户关联向量", name_en="Association vector",
            role=ParameterRole.OPTIMIZATION_VARIABLE, type=ParameterType.CATEGORICAL,
            unit="cell_id vector", default=choices[0], choices=choices,
            value_generation=[], source="Day 9 frozen candidate neighborhood",
        )
        space = ParameterSpace(parameters=[definition], metadata={"parameter_semantics": "categorical_vector"})
        problem = AlgorithmProblem(
            problem_type=PROBLEM_TYPE, parameter_space=space, objective_id="NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1",
            objective_direction=Direction.MAXIMIZE, baseline_parameters={ASSOCIATION_PARAMETER: choices[0]},
            max_evaluations=budget,
        )
        hyperparameters = algorithm_hyperparameters if algorithm_hyperparameters is not None else (
            {"seed": seed} if algorithm.metadata().algorithm_id == "random_search_v0_1" else {}
        )
        report = check_compatibility(algorithm, problem, hyperparameters, budget)
        if not report.compatible:
            raise ValueError([e.message for e in report.errors])
        actual: dict[str, Any] = {"BASELINE": baseline_eval}
        evaluation_index = 0

        def evaluate(point: dict[str, ParameterValue], _round: int) -> EvaluationResult:
            nonlocal evaluation_index
            evaluation_index += 1
            vector = list(point[ASSOCIATION_PARAMETER])
            association = Association(assignments=dict(zip(ue_ids, vector, strict=True)))
            evaluation = backend.evaluate(association, p5_floor=baseline_eval.p5_ue_throughput_mbps, channel_reused=True)
            candidate_id = f"{benchmark_run_id}-CAND-{evaluation_index:03d}"
            actual[candidate_id] = evaluation
            feasible = evaluation.feasible
            return EvaluationResult(
                candidate_id=candidate_id, parameters=point,
                objective=evaluation.network_throughput_mbps if feasible else None,
                objective_direction=Direction.MAXIMIZE,
                secondary_metrics={
                    "network_throughput_mbps": evaluation.network_throughput_mbps,
                    "average_ue_throughput_mbps": evaluation.average_ue_throughput_mbps,
                    "p5_ue_throughput_mbps": evaluation.p5_ue_throughput_mbps,
                },
                constraint_results=[ConstraintResult(
                    id="P5_FLOOR", satisfied=feasible, value=evaluation.p5_ue_throughput_mbps,
                    detail=f"P5 >= {baseline_eval.p5_ue_throughput_mbps:.12f} Mbps",
                )],
                status=EvaluationStatus.EVALUATED, runtime_seconds=evaluation.runtime_seconds,
            )

        baseline_result = EvaluationResult(
            candidate_id="BASELINE", parameters={ASSOCIATION_PARAMETER: choices[0]},
            objective=baseline_eval.network_throughput_mbps, objective_direction=Direction.MAXIMIZE,
            secondary_metrics={
                "network_throughput_mbps": baseline_eval.network_throughput_mbps,
                "average_ue_throughput_mbps": baseline_eval.average_ue_throughput_mbps,
                "p5_ue_throughput_mbps": baseline_eval.p5_ue_throughput_mbps,
            },
            constraint_results=[ConstraintResult(id="P5_FLOOR", satisfied=True,
                                                 value=baseline_eval.p5_ue_throughput_mbps)],
            status=EvaluationStatus.EVALUATED, runtime_seconds=baseline_eval.runtime_seconds,
        )
        driver = AlgorithmDriver(
            algorithm=algorithm, problem=problem, hyperparameters=report.resolved_hyperparameters or {},
            evaluate=evaluate,
            tie_break=lambda result: (result.secondary_metrics.get("p5_ue_throughput_mbps", 0.0),),
        )
        trace = driver.run([baseline_result])
        elapsed = time.perf_counter() - wall_start
        best_id = trace.evaluations[-1].best_so_far_candidate_id if trace.evaluations else "BASELINE"
        best_id = best_id or "BASELINE"
        best_eval = actual[best_id]
        simulation_time = sum(float(e.runtime_seconds or 0.0) for e in actual.values())
        return {
            "optimization_id": f"OPT-BENCH-{uuid.uuid4().hex[:8].upper()}",
            "trace": trace,
            "actual": actual,
            "baseline": baseline_eval,
            "best": best_eval,
            "best_candidate_id": best_id,
            "candidate_count": len(actual) - 1,
            "runtime": {
                "optimizer_overhead_time": max(0.0, elapsed - simulation_time),
                "simulation_evaluation_time": simulation_time,
                "total_wall_time": elapsed,
            },
            "channel_hash": channel.channel_hash,
            "channel_realization_id": "CH-MULTICELL-" + channel.channel_hash[:8].upper(),
        }
