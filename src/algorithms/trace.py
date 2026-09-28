"""
算法轨迹 / Algorithm trace —— 回答“算法为什么最后给出这个参数？”。

只记录输入 / 输出 / 评价与算法自报的 JSON 状态快照，不要求解释算法内部数学，不保存 pickle。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from optimization.parameters import ParameterValue

from .sdk import AlgorithmRecommendation, HyperparameterValue, StopReason


class TraceEvaluation(BaseModel):
    sequence: int = Field(description="0 = platform incumbent (baseline); algorithm evaluations start at 1")
    round: int = Field(description="suggest/observe round; 0 = incumbent")
    candidate_id: str
    parameters: dict[str, ParameterValue]
    objective: float | None
    secondary_metrics: dict[str, float] = Field(default_factory=dict)
    status: str
    cache_hit: bool = False
    best_so_far_candidate_id: str | None
    best_so_far_objective: float | None
    at: str


class TraceRound(BaseModel):
    round: int
    state_before: dict[str, Any]
    suggestions: list[dict[str, ParameterValue]]
    evaluated_candidate_ids: list[str]
    rejected_suggestions: list[dict[str, ParameterValue]] = Field(default_factory=list)
    state_after: dict[str, Any]


class AlgorithmTrace(BaseModel):
    algorithm_id: str
    algorithm_version: str
    sdk_version: str
    hyperparameters: dict[str, HyperparameterValue]
    max_evaluations: int
    initial_state: dict[str, Any] = Field(default_factory=dict)
    evaluations: list[TraceEvaluation] = Field(default_factory=list)
    rounds: list[TraceRound] = Field(default_factory=list)
    evaluations_used: int = 0
    rejected_suggestions: int = 0
    stop_reason: StopReason | None = None
    stop_detail: str = ""
    recommendation: AlgorithmRecommendation | None = None
    final_state: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
