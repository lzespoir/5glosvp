from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from antenna.models import BeamResponse, RadioGeometry


class Position(BaseModel):
    x: float
    y: float
    z: float
    coordinate_system: str = "SIONNA_SCENE_CARTESIAN"
    source: str = "DAY13_QUERY"


class UETwin(BaseModel):
    ue_id: str
    position: Position
    orientation: list[float] | None = None
    mobility_state: str = "STATIC_DAY13_GEOMETRY"
    serving_cell_id: str | None = None
    neighbor_cell_ids: list[str] = Field(default_factory=list)
    traffic_profile: str = "full_buffer"
    aau_id: str
    aau_position: Position
    radio_geometry: RadioGeometry
    beam_observations: list[BeamResponse]
    strongest_relative_beam_id: int | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    calibration_status: str = "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED"
