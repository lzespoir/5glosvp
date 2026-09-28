"""
UE 位置生成 / UE position generation.

候选位置由平台以固定种子生成（与仿真器无关）；是否存在传播路径由后端判定。
"""

from __future__ import annotations

import numpy as np

from .models import UeGeneratorConfig


def generate_candidates(config: UeGeneratorConfig) -> np.ndarray:
    """返回 [max_candidates, 3] 的候选位置（x, y 在区域内均匀分布，z = height_m）。"""
    rng = np.random.default_rng(config.seed)
    cx, cy = config.area_center
    sx, sy = config.area_size
    xs = rng.uniform(cx - sx / 2, cx + sx / 2, config.max_candidates)
    ys = rng.uniform(cy - sy / 2, cy + sy / 2, config.max_candidates)
    return np.stack([xs, ys, np.full(config.max_candidates, config.height_m)], axis=1)


def ue_id_for(index: int) -> str:
    return f"UE-{index + 1:03d}"
