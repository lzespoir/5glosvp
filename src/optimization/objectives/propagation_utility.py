"""
PROPAGATION_UTILITY_V0_1 —— 传播效用目标函数（工程目标，不是验收 KPI）。

    J = C_sinr − λ · c_P

    C_sinr = |{cell : SINR(cell) 有限 且 SINR(cell) ≥ τ}| / N_cells
    c_P    = (P − P_min) / (P_max − P_min)，P_max = P_min 时为 0

完整定义见 docs/objectives/propagation-utility-v0.1.md。公式发布后不得在同一 id 下修改。
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ..base import Objective, ObjectiveInputs
from ..models import TX_POWER_PARAMETER, Direction, ObjectiveEvaluation

OBJECTIVE_ID = "PROPAGATION_UTILITY_V0_1"
LAMBDA_POWER = "lambda_power"
SINR_THRESHOLD_DB = 0.0
DEFAULT_LAMBDA_POWER = 0.10


def sinr_coverage(sinr_db: np.ndarray, threshold_db: float) -> tuple[int, int]:
    """(达到阈值的格点数, 格点总数)。NaN（无传播路径）计为未覆盖。"""
    finite = np.isfinite(sinr_db)
    covered = int(np.count_nonzero(finite & (np.where(finite, sinr_db, -np.inf) >= threshold_db)))
    return covered, int(sinr_db.size)


def normalized_power_cost(power: float, power_min: float, power_max: float) -> float:
    if power_max <= power_min:
        return 0.0
    return (power - power_min) / (power_max - power_min)


class PropagationUtilityV01(Objective):
    id = OBJECTIVE_ID
    version = "0.1"
    direction = Direction.MAXIMIZE
    name_zh = "传播效用"
    name_en = "Propagation Utility"
    description_zh = (
        "SINR 覆盖比例减去发射功率成本。传播层工程目标函数，用于验证参数优化闭环，"
        "不是吞吐率、边缘用户速率或优化速度验收指标。"
    )
    description_en = (
        "SINR coverage ratio minus a transmit power cost. A propagation-level engineering objective "
        "for validating the optimization loop; not a throughput, edge-user-rate or acceptance KPI."
    )
    formula = "J = C_sinr − λ · (P − P_min) / (P_max − P_min),  C_sinr = N(SINR ≥ 0 dB) / N_cells"
    required_layers = ("sinr",)
    default_params = {LAMBDA_POWER: DEFAULT_LAMBDA_POWER}
    assumptions = {
        LAMBDA_POWER: "[A] Assumption — engineering demonstration parameter (default 0.10), not a standard value",
        "sinr_threshold_db": "[A] Assumption — SINR ≥ 0 dB counts as covered; fixed in V0.1",
        "power_bounds": "P_min / P_max = min / max TX power over the search space and the baseline",
    }

    def evaluate(self, inputs: ObjectiveInputs, params: Mapping[str, float]) -> ObjectiveEvaluation:
        sinr = inputs.layers.get("sinr")
        if sinr is None:
            raise ValueError("Radio map has no 'sinr' layer; cannot evaluate PROPAGATION_UTILITY_V0_1")
        lam = float(params.get(LAMBDA_POWER, DEFAULT_LAMBDA_POWER))
        power = float(inputs.parameters[TX_POWER_PARAMETER])
        p_min, p_max = inputs.parameter_bounds[TX_POWER_PARAMETER]

        covered, total = sinr_coverage(sinr, SINR_THRESHOLD_DB)
        if total == 0:
            raise ValueError("Radio map has no cells")
        coverage = covered / total
        cost = normalized_power_cost(power, p_min, p_max)
        return ObjectiveEvaluation(
            objective_id=self.id,
            objective_version=self.version,
            value=coverage - lam * cost,
            components={
                "sinr_coverage_ratio": coverage,
                "sinr_threshold_db": SINR_THRESHOLD_DB,
                "covered_cells": float(covered),
                "num_cells": float(total),
                "tx_power_dbm": power,
                "power_min_dbm": p_min,
                "power_max_dbm": p_max,
                "normalized_power_cost": cost,
                "lambda_power": lam,
                "power_cost_term": lam * cost,
            },
        )
