from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from antenna.models import BeamResponse, RadioGeometry
from ue_twin.models import Position


SemanticType = Literal[
    "GEOMETRY",
    "RELATIVE_ANTENNA_RESPONSE",
    "SIMULATION_DERIVED",
    "CALIBRATED_SIMULATION",
    "MEASURED",
    "DERIVED_KPI",
]
CalibrationStatus = Literal[
    "RELATIVE_ONLY",
    "UNCALIBRATED_SIMULATION",
    "CALIBRATED_SIMULATION",
    "MEASURED",
    "UNKNOWN",
]
SourceType = Literal["DAY13_A_MATRIX", "FAST_PROPAGATION", "SCENARIO_DEFINED", "DERIVED"]


class RadioMetricValue(BaseModel):
    metric_name: str
    value: float | None
    unit: str
    semantic_type: SemanticType
    source_type: SourceType
    calibration_status: CalibrationStatus
    model_version: str | None = None
    artifact_id: str | None = None
    artifact_hash: str | None = None
    notes: str = ""


class CellRadioConfig(BaseModel):
    cell_id: str
    site_id: str
    aau_id: str
    position: Position
    coordinate_system: str
    tx_power_dbm: float | None = None
    carrier_frequency_hz: float | None = None
    bandwidth_hz: float | None = None
    antenna_profile_id: str
    a_matrix_library: str
    a_matrix_artifact_id: str
    a_matrix_hash: str
    beam_config: dict[str, Any] = Field(default_factory=dict)
    propagation_backend: str
    radio_config_version: str
    provenance: dict[str, Any] = Field(default_factory=dict)


class ScenarioRadioContext(BaseModel):
    radio_context_id: str
    scenario_id: str
    scenario_version: str
    scenario_definition_hash: str
    scenario_definition: dict[str, Any]
    scenario_instance: dict[str, Any]
    cells: list[CellRadioConfig]
    ue_positions: dict[str, Position]
    declared_serving_cells: dict[str, str]
    declared_neighbors: dict[str, list[str]]
    radio_context_version: str = "D14-RADIO-CONTEXT-0.1"
    provenance: dict[str, Any] = Field(default_factory=dict)


class PropagationObservation(BaseModel):
    backend_id: str
    model_version: str
    distance_m: RadioMetricValue
    path_loss_db: RadioMetricValue
    received_power: RadioMetricValue
    notes: list[str] = Field(default_factory=list)


class ReceivedPowerDecomposition(BaseModel):
    metric_name: str = "SIM_RECEIVED_POWER"
    components: list[RadioMetricValue]
    total: RadioMetricValue
    absolute_kpi_status: str = "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED"


class InterferenceObservation(BaseModel):
    per_interferer: list[RadioMetricValue]
    aggregate_interference: RadioMetricValue
    noise_floor: RadioMetricValue
    sinr: RadioMetricValue
    notes: list[str] = Field(default_factory=list)


class ServingNeighborContext(BaseModel):
    serving_cell_id: str
    serving_selection_source: Literal[
        "SCENARIO_DEFINED", "EXPERIMENT_DEFINED", "STRONGEST_SIMULATED_SIGNAL", "EXTERNAL_DATA", "ALGORITHM_OUTPUT"
    ]
    serving_selection_status: str = "DECLARED_NOT_HANDOVER"
    neighbor_cell_ids: list[str]
    neighbor_ranking_metric: str = "SIM_RECEIVED_POWER"
    neighbor_ranking_source: str = "FAST_PROPAGATION_UNCALIBRATED"
    ranked_neighbors: list[dict[str, Any]] = Field(default_factory=list)


class CellRadioObservation(BaseModel):
    cell: CellRadioConfig
    ue_id: str
    role: Literal["SERVING", "NEIGHBOR", "OTHER"]
    geometry: RadioGeometry
    beam_observations: list[BeamResponse]
    strongest_relative_beam_id: int | None
    strongest_relative_response: RadioMetricValue
    propagation: PropagationObservation
    received_power: ReceivedPowerDecomposition
    interference: InterferenceObservation | None = None


class RadioIdentity(BaseModel):
    scenario_id: str
    scenario_instance_id: str
    scenario_definition_hash: str
    radio_context_id: str
    radio_context_version: str
    cell_config_hash: str
    a_matrix_artifact_hashes: list[str]
    normalization_policy: str
    angular_grid_version: str
    lookup_method: str
    propagation_backend: str
    calibration_status: CalibrationStatus = "UNCALIBRATED_SIMULATION"
    identity_hash: str


class RadioObservationSet(BaseModel):
    observation_set_id: str
    scenario_id: str
    scenario_instance_id: str
    ue: dict[str, Any]
    ue_twin: dict[str, Any]
    radio_context: ScenarioRadioContext
    cells: list[CellRadioObservation]
    serving_neighbor: ServingNeighborContext
    identity: RadioIdentity
    calibration_status: CalibrationStatus = "UNCALIBRATED_SIMULATION"
    absolute_radio_kpi_status: str = "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED"
    provenance: dict[str, Any] = Field(default_factory=dict)
