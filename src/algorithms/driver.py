"""
平台侧算法驱动 / Platform-side algorithm driver.

执行 initialize → (suggest → evaluate → observe)* → finalize；评价预算由平台执行，不依赖算法自觉：
超出剩余预算的建议被拒绝（记录在 trace 中）且不评价，运行以 budget_exhausted 停止。
评价回调由业务层提供（例如在冻结上下文中运行系统级实验），驱动本身不接触仿真器。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from optimization.parameters import ParameterValue

from .errors import AlgorithmExecutionError
from .sdk import (
    ALGORITHM_SDK_VERSION,
    Algorithm,
    AlgorithmProblem,
    EvaluationResult,
    HyperparameterValue,
    StopReason,
)
from .trace import AlgorithmTrace, TraceEvaluation, TraceRound

# evaluate(parameters, round) → EvaluationResult（candidate_id 由平台分配）
Evaluate = Callable[[dict[str, ParameterValue], int], EvaluationResult]
# 目标值相同时的平台 tie-break 键（较大者胜出）
TieBreak = Callable[[EvaluationResult], tuple[float, ...]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AlgorithmDriver:
    def __init__(
        self,
        algorithm: Algorithm,
        problem: AlgorithmProblem,
        hyperparameters: dict[str, HyperparameterValue],
        evaluate: Evaluate,
        tie_break: TieBreak,
        on_update: Callable[[], None] = lambda: None,
    ) -> None:
        meta = algorithm.metadata()
        self._algorithm = algorithm
        self._problem = problem
        self._hyperparameters = hyperparameters
        self._evaluate = evaluate
        self._tie_break = tie_break
        self._on_update = on_update
        self._best: EvaluationResult | None = None
        self.trace = AlgorithmTrace(
            algorithm_id=meta.algorithm_id, algorithm_version=meta.version,
            sdk_version=meta.sdk_version or ALGORITHM_SDK_VERSION, hyperparameters=dict(hyperparameters),
            max_evaluations=problem.max_evaluations,
        )

    def run(self, incumbents: list[EvaluationResult]) -> AlgorithmTrace:
        trace = self.trace
        try:
            self._algorithm.initialize(self._problem, self._hyperparameters, incumbents)
            for r in incumbents:
                self._record(r, round_=0, sequence=0)
            trace.initial_state = self._algorithm.state_metadata()
            self._loop()
            trace.recommendation = self._algorithm.finalize()
            trace.final_state = self._algorithm.state_metadata()
        except AlgorithmExecutionError as e:
            self._failed(str(e))
            raise
        except Exception as e:  # noqa: BLE001 - 算法异常转为 FAILED 并保留已有 trace
            self._failed(f"{type(e).__name__}: {e}")
            raise AlgorithmExecutionError(trace.error or "algorithm failed") from e
        self._on_update()
        return trace

    def _loop(self) -> None:
        trace = self.trace
        round_ = 0
        while True:
            stop = self._algorithm.should_stop()
            if stop is not None:
                trace.stop_reason, trace.stop_detail = stop, "reported by the algorithm"
                return
            remaining = self._problem.max_evaluations - trace.evaluations_used
            if remaining <= 0:
                trace.stop_reason = StopReason.BUDGET_EXHAUSTED
                trace.stop_detail = f"platform budget of {self._problem.max_evaluations} evaluations used"
                return
            state_before = self._algorithm.state_metadata()
            suggestions = self._algorithm.suggest(remaining)
            if not suggestions:
                trace.stop_reason = self._algorithm.should_stop() or StopReason.COMPLETED
                trace.stop_detail = "algorithm returned no further suggestions"
                return
            round_ += 1
            accepted, rejected = suggestions[:remaining], suggestions[remaining:]
            points = []
            for s in accepted:
                try:
                    points.append(self._problem.parameter_space.validate_point(s))
                except ValueError as e:
                    raise AlgorithmExecutionError(f"invalid suggestion {s!r}: {e}") from e
            results = []
            for point in points:
                trace.evaluations_used += 1
                result = self._evaluate(point, round_)
                results.append(result)
                self._record(result, round_=round_, sequence=trace.evaluations_used)
            trace.rejected_suggestions += len(rejected)
            self._algorithm.observe(results)
            trace.rounds.append(TraceRound(
                round=round_, state_before=state_before, suggestions=list(suggestions),
                evaluated_candidate_ids=[r.candidate_id for r in results], rejected_suggestions=list(rejected),
                state_after=self._algorithm.state_metadata(),
            ))
            self._on_update()
            if rejected:
                trace.stop_reason = StopReason.BUDGET_EXHAUSTED
                trace.stop_detail = (f"{len(rejected)} suggestion(s) rejected: platform budget of "
                                     f"{self._problem.max_evaluations} evaluations reached")
                return

    def _record(self, result: EvaluationResult, round_: int, sequence: int) -> None:
        score = result.score()
        if score is not None:
            best = self._best
            best_score = best.score() if best is not None else None
            if best is None or best_score is None or (score, *self._tie_break(result)) > (
                best_score, *self._tie_break(best)
            ):
                self._best = result
        self.trace.evaluations.append(TraceEvaluation(
            sequence=sequence, round=round_, candidate_id=result.candidate_id, parameters=result.parameters,
            objective=result.objective, secondary_metrics=result.secondary_metrics, status=result.status.value,
            cache_hit=result.cache_hit,
            best_so_far_candidate_id=self._best.candidate_id if self._best else None,
            best_so_far_objective=self._best.objective if self._best else None, at=_now(),
        ))

    def _failed(self, message: str) -> None:
        self.trace.stop_reason = StopReason.FAILED
        self.trace.stop_detail = "algorithm raised or violated the integration contract"
        self.trace.error = message
        self._on_update()
