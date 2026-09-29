from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


MetricSource = Literal["SIMULATED", "MEASURED", "DERIVED", "UNKNOWN"]


class MetricProvenance(BaseModel):
    metric_id: str
    value: float | None = None
    unit: str = "UNKNOWN"
    source: MetricSource = "UNKNOWN"
    model_backend: str = "UNKNOWN"
    artifact_id: str = "UNKNOWN"
    run_id: str = "UNKNOWN"


class UETwin(BaseModel):
    """Day 12 contract only; it does not claim dynamic mobility support."""

    ue_id: str
    position: list[float] = Field(min_length=2, max_length=3)
    mobility_state: str = "static"
    serving_cell_id: str | None = None
    neighbor_cell_ids: list[str] = Field(default_factory=list)
    candidate_cells: list[str] = Field(default_factory=list)
    traffic_profile: str = "UNKNOWN"
    radio_metrics: list[MetricProvenance] = Field(default_factory=list)


class TrafficModelAdapter(BaseModel):
    model_id: str
    version: str
    input_requirements: list[str] = Field(default_factory=list)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    supports_time_series: bool = False
    supports_per_ue: bool = False
    supports_per_beam: bool = False
    source_type: str = "PLACEHOLDER"
    semantics_status: str = "MODEL_SEMANTICS_PENDING_RESEARCH_TEAM_INPUT"


FULL_BUFFER_TRAFFIC_ADAPTER = TrafficModelAdapter(
    model_id="full_buffer_profile",
    version="0.1",
    input_requirements=["scenario_instance_id"],
    output_schema={"per_ue": "constant_saturated_demand"},
    supports_per_ue=True,
    source_type="SIMULATION_PROFILE",
    semantics_status="SUPPORTED_PROFILE",
)

BEAM_SPACE_TRAFFIC_ADAPTER = TrafficModelAdapter(
    model_id="beam_space_traffic",
    version="0.1-contract",
    input_requirements=["research_team_model", "beam_artifact"],
    output_schema={"per_beam": "UNKNOWN"},
    supports_per_beam=True,
    source_type="REQUIRES_EXTERNAL_MODEL",
)
