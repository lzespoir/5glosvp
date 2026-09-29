from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from user_association.backend import FrozenMultiCellChannel, MultiCellBackend


class FrozenArtifactService:
    """Read-only access to persisted frozen artifacts; never retraces propagation."""

    def __init__(self, reference_dir: Path) -> None:
        self.reference_dir = Path(reference_dir).resolve()

    def load_day8_channel(self, scenario: Any, backend: MultiCellBackend | None = None) -> FrozenMultiCellChannel:
        source = self.reference_dir / "user_association" / "OPT-9748F677" / "optimization.json"
        if not source.is_file():
            raise FileNotFoundError(f"frozen Day 8 artifact not found: {source}")
        data = json.loads(source.read_text(encoding="utf-8"))
        persisted = data["scenario"]
        current = scenario.model_dump(mode="json")
        if persisted.get("scenario_id") != scenario.scenario_id or persisted.get("cells") != current.get("cells"):
            raise ValueError("Day 8 frozen scenario does not match requested scenario")
        ch = data.get("channel") or {}
        channel_hash = ch.get("sha256")
        if not isinstance(channel_hash, str) or len(channel_hash) != 64:
            raise ValueError("Day 8 frozen channel hash is missing or malformed")
        cell_ids = [c.cell_id for c in scenario.cells]
        ue_ids = [u.ue_id for u in scenario.ues]
        gains = []
        for ue_id in ue_ids:
            links = {x["cell_id"]: x for x in data["candidate_cells"][ue_id]}
            gains.append([10 ** (float(links[cid]["link_gain_db"]) / 10.0) if cid in links else 0.0 for cid in cell_ids])
        gains_array = np.asarray(gains, dtype=float)
        channel = FrozenMultiCellChannel(
            scenario_id=scenario.scenario_id, ue_ids=ue_ids, cell_ids=cell_ids,
            gains_linear=gains_array,
            gains_db=np.where(gains_array > 0, 10 * np.log10(np.maximum(gains_array, 1e-30)), -300.0),
            positions=np.asarray([u.position for u in scenario.ues]),
            channel_hash=channel_hash, runtime_seconds=0.0,
            provider_versions=ch.get("provider_versions", {}), provenance_hash_version="0.1",
        )
        if backend is not None:
            backend.channel = channel
        return channel
