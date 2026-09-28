"""
冻结信道 / UE / 业务实现的标识与哈希 / Identity and hashing of frozen realizations.

哈希只依赖规范化内容（数组字节 + dtype + shape、排序后的 JSON），与文件格式无关，
独立复核脚本可按 docs/benchmark/system-benchmark-v0.1.md 中的同一规则重新计算。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .base import ChannelRealization
from .models import SystemScenario, TrafficDemand

CHANNEL_FILE = "channel.npz"
_ARRAY_PREFIX = "array__"


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def propagation_fingerprint(scenario: SystemScenario) -> str:
    """
    决定信道实现的场景字段（几何、天线、载频、资源网格、RT 参数、UE 放置、种子）。
    不含发射功率与调度/链路自适应/功控参数：CFR 与功率无关，这些参数只在 SYS 中生效。
    """
    sim = scenario.simulation
    return _sha256_json({
        "scene": scenario.scene,
        "base_stations": [{"bs_id": b.bs_id, "position": b.position} for b in scenario.base_stations],
        "cells": [
            {"cell_id": c.cell_id, "bs_id": c.bs_id, "position": scenario.cell_position(c),
             "carrier_frequency_hz": c.carrier_frequency_hz, "bandwidth_hz": c.bandwidth_hz,
             "antenna": c.antenna.model_dump(mode="json", exclude={"source"})}
            for c in scenario.cells
        ],
        "ues": [{"ue_id": u.ue_id, "position": u.position, "serving_cell_id": u.serving_cell_id}
                for u in scenario.ues],
        "ue_generator": scenario.ue_generator.model_dump(mode="json", exclude={"source"})
        if scenario.ue_generator else None,
        "seed": scenario.seed,
        "grid": {"subcarrier_spacing_hz": sim.subcarrier_spacing_hz, "num_prb": sim.num_prb,
                 "num_data_symbols_per_slot": sim.num_data_symbols_per_slot},
        "rt": {"max_depth": sim.max_depth, "samples_per_src": sim.samples_per_src},
    })


def hash_arrays(arrays: dict[str, np.ndarray]) -> str:
    """SHA-256 over sorted keys; each entry = key, dtype, shape, C-order bytes."""
    h = hashlib.sha256()
    for key in sorted(arrays):
        a = np.ascontiguousarray(arrays[key])
        h.update(key.encode())
        h.update(str(a.dtype).encode())
        h.update(json.dumps(list(a.shape)).encode())
        h.update(a.tobytes())
    return h.hexdigest()


def ue_population_hash(ue_ids: list[str], serving_cell_ids: list[str], positions: list[list[float]]) -> str:
    return _sha256_json({"ue_ids": list(ue_ids), "serving_cell_ids": list(serving_cell_ids),
                         "positions": [[float(v) for v in p] for p in positions]})


def traffic_hash(traffic: TrafficDemand) -> str:
    return _sha256_json(traffic.model_dump(mode="json"))


def save_channel(directory: Path, channel: ChannelRealization) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / CHANNEL_FILE
    np.savez_compressed(
        path,
        ue_ids=np.array(channel.ue_ids),
        serving_cell_ids=np.array(channel.serving_cell_ids),
        positions=channel.positions,
        mean_channel_gain_db=channel.mean_channel_gain_db,
        **{f"{_ARRAY_PREFIX}{k}": v for k, v in channel.arrays.items()},
    )
    return path


def load_channel(path: Path, provider: str, provider_versions: dict[str, str | None],
                 propagation_fingerprint_: str, metadata: dict[str, Any]) -> ChannelRealization:
    with np.load(path, allow_pickle=False) as data:
        return ChannelRealization(
            ue_ids=tuple(str(v) for v in data["ue_ids"]),
            serving_cell_ids=tuple(str(v) for v in data["serving_cell_ids"]),
            positions=data["positions"],
            mean_channel_gain_db=data["mean_channel_gain_db"],
            arrays={k[len(_ARRAY_PREFIX):]: data[k] for k in data.files if k.startswith(_ARRAY_PREFIX)},
            provider=provider,
            provider_versions=provider_versions,
            propagation_fingerprint=propagation_fingerprint_,
            metadata=metadata,
        )
