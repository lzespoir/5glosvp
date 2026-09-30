from __future__ import annotations

from typing import Any

from typing import Any

from pydantic import BaseModel, Field

from ue_twin.models import Position


class UETwinQueryRequest(BaseModel):
    ue_id: str = Field(min_length=1)
    aau_id: str = Field(min_length=1)
    aau_position: Position
    ue_position: Position
    profile_id: str | None = None
    serving_cell_id: str | None = None
    neighbor_cell_ids: list[str] = Field(default_factory=list)
    traffic_profile: str = "full_buffer"


class ScenarioAMatrixIdentityRequest(BaseModel):
    scenario: dict[str, Any]
    profile_id: str | None = None
