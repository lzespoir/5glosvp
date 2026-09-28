from __future__ import annotations

import hashlib
import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

INTERFERENCE_MODEL = "APPROXIMATE_COCHANNEL_INTERFERENCE_V0_1"
CANDIDATE_POLICY = "CANDIDATE_CELL_POLICY_V0_1_TOP_K_GAIN"
BASELINE_POLICY = "ASSOCIATION_BASELINE_V0_1_BEST_LINK"
OBJECTIVE_ID = "NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1"

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Cell(Strict):
    cell_id: str
    bs_id: str
    position: list[float] = Field(min_length=3, max_length=3)
    carrier_frequency_hz: float = 3.5e9
    bandwidth_hz: float = 100e6
    tx_power_dbm: float = 44.0
    antenna_rows: int = 2
    antenna_cols: int = 4

class UE(Strict):
    ue_id: str
    position: list[float] = Field(min_length=3, max_length=3)

class CandidateCell(Strict):
    cell_id: str
    link_available: bool
    link_gain_db: float
    rank: int

class MultiCellScenario(Strict):
    scenario_id: str
    name_zh: str
    name_en: str
    scene: str
    seed: int
    cells: list[Cell] = Field(min_length=3)
    ues: list[UE] = Field(min_length=1)
    frequency_hz: float = 3.5e9
    bandwidth_hz: float = 100e6
    num_slots: int = 100
    slot_duration_s: float = 0.0005
    candidate_k: int = Field(default=3, ge=1)
    traffic_model: Literal["full_buffer"] = "full_buffer"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid(self):
        if len({c.cell_id for c in self.cells}) != len(self.cells): raise ValueError("duplicate cell")
        if len({u.ue_id for u in self.ues}) != len(self.ues): raise ValueError("duplicate UE")
        if any(len(c.position) != 3 for c in self.cells): raise ValueError("cell position")
        return self

class Association(Strict):
    assignments: dict[str, str]

    def vector(self, ue_ids: list[str]) -> list[str]:
        return [self.assignments[u] for u in ue_ids]

    def sha256(self, ue_ids: list[str]) -> str:
        raw = json.dumps(self.assignments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

class CellMetrics(Strict):
    cell_id: str
    associated_ue_count: int
    throughput_mbps: float
    average_ue_throughput_mbps: float

class UeMetrics(Strict):
    ue_id: str
    serving_cell_id: str
    throughput_mbps: float
    link_gain_db: float
    sinr_db: float
    resource_share: float

class AssociationEvaluation(Strict):
    association: Association
    association_hash: str
    network_throughput_mbps: float
    average_ue_throughput_mbps: float
    p5_ue_throughput_mbps: float
    cell_metrics: list[CellMetrics]
    ue_metrics: list[UeMetrics]
    p5_floor_mbps: float | None = None
    p5_margin_mbps: float | None = None
    feasible: bool = True
    channel_reused: bool = False
    runtime_seconds: float = 0.0

class AssociationMove(Strict):
    iteration: int
    ue_id: str
    from_cell: str
    to_cell: str
    reason: str
    objective_before: float
    objective_after: float
    p5_before: float
    p5_after: float
    feasible: bool
    accepted: bool
