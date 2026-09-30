"""Day15 configuration objects. No random realization belongs to a definition."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Source = Literal["USER_DEFINED", "IMPORTED", "GENERATED", "MEASURED", "MODEL_DEFAULT", "BACKEND_DEFAULT", "UNKNOWN"]
State = Literal["DRAFT", "VALID", "INVALID", "READY", "ARCHIVED"]
AssetType = Literal["OSM", "GLTF", "GEOJSON", "RASTER_MAP", "TERRAIN", "SIONNA_SCENE", "CUSTOM_MESH"]
Problem = Literal["NETWORK_STRUCTURE", "USER_ACCESS", "SYSTEM_RESOURCE"]


class CoordinateReference(BaseModel):
    coordinate_system: str = "UNKNOWN"
    unit: str = "UNKNOWN"
    origin: str = "UNKNOWN"
    source: Source = "UNKNOWN"
    status: Literal["CONFIRMED", "DECLARED", "UNKNOWN"] = "UNKNOWN"


class Position(BaseModel):
    x: float
    y: float
    z: float
    coordinate: CoordinateReference


class EnvironmentAsset(BaseModel):
    asset_id: str
    name: str
    asset_type: AssetType
    source_path: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    coordinate: CoordinateReference = Field(default_factory=CoordinateReference)
    metadata: dict[str, Any] = Field(default_factory=dict)
    supported_backends: list[str] = Field(default_factory=list)
    conversion_status: str = "NOT_CONVERTED"
    source: Source = "IMPORTED"
    version: int = 1


class MapLayer(BaseModel):
    layer_id: str
    kind: Literal["BASE_MAP", "BUILDINGS", "SITE", "CELL", "UE", "RADIO", "TRAFFIC", "HANDOVER"]
    visible: bool = False
    source_asset_id: str | None = None
    status: str = "AVAILABLE"


class EnvironmentDefinition(BaseModel):
    environment_id: str
    asset_id: str | None = None
    asset_sha256: str | None = None
    coordinate: CoordinateReference = Field(default_factory=CoordinateReference)
    layers: list[MapLayer] = Field(default_factory=list)
    supported_backends: list[str] = Field(default_factory=list)
    version: int = 1


class Parameter(BaseModel):
    value: float | str | None = None
    unit: str = "UNKNOWN"
    source: Source = "UNKNOWN"
    source_version: str | None = None

    @model_validator(mode="after")
    def validate_default(self):
        if self.source in {"MODEL_DEFAULT", "BACKEND_DEFAULT"} and not self.source_version:
            raise ValueError("default parameter requires source_version")
        return self


class SiteDefinition(BaseModel):
    site_id: str
    name: str
    position: Position
    source: Source = "USER_DEFINED"
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class CellCoreConfig(BaseModel):
    carrier_frequency: Parameter = Field(default_factory=Parameter)
    bandwidth: Parameter = Field(default_factory=Parameter)
    tx_power: Parameter = Field(default_factory=Parameter)
    azimuth: Parameter = Field(default_factory=Parameter)
    mechanical_tilt: Parameter = Field(default_factory=Parameter)
    electrical_tilt: Parameter = Field(default_factory=Parameter)
    antenna_height: Parameter = Field(default_factory=Parameter)


class AntennaBinding(BaseModel):
    antenna_definition_id: str | None = None
    aau_definition_id: str | None = None
    source: Source = "UNKNOWN"


class CellDefinition(BaseModel):
    cell_id: str
    site_id: str
    name: str
    position: Position | None = None
    core: CellCoreConfig = Field(default_factory=CellCoreConfig)
    antenna: AntennaBinding = Field(default_factory=AntennaBinding)
    network_parameters: dict[str, Parameter] = Field(default_factory=dict)
    resource_parameters: dict[str, Parameter] = Field(default_factory=dict)
    backend_extensions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    source: Source = "USER_DEFINED"
    version: int = 1


class AntennaDefinition(BaseModel):
    antenna_definition_id: str
    name: str
    provider_type: Literal["A_MATRIX", "SIONNA_BUILTIN", "GAUSSIAN", "CUSTOM", "EXTERNAL"]
    provider_status: Literal["IMPLEMENTED", "CONTRACT_ONLY", "UNAVAILABLE"]
    source: Source
    beam_count: int | None = None
    coordinate: CoordinateReference = Field(default_factory=CoordinateReference)
    normalization: str = "UNKNOWN"
    calibration_status: str = "UNKNOWN"
    supported_backends: list[str] = Field(default_factory=list)
    artifact_id: str | None = None
    artifact_hash: str | None = None
    profile_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    version: int = 1


class UEDefinition(BaseModel):
    ue_id: str
    position: Position | None = None
    mobility: str = "UNKNOWN"
    traffic_profile: str = "UNKNOWN"
    serving_cell_id: str | None = None
    source: Source = "USER_DEFINED"


class TrafficDefinition(BaseModel):
    kind: Literal["UNKNOWN", "FULL_BUFFER", "STATIC_DEMAND", "TIME_SERIES", "BEAM_SPACE_PREDICTION", "MEASURED_TRAFFIC"] = "UNKNOWN"
    availability: Literal["AVAILABLE", "NOT_IMPLEMENTED", "EXTERNAL_DATA_REQUIRED"] = "NOT_IMPLEMENTED"
    source: Source = "UNKNOWN"


class RadioModelDefinition(BaseModel):
    backend: str = "UNKNOWN"
    # AVAILABLE is accepted for records written by the initial Day15 schema;
    # validator treats it as legacy/unregistered, never as execution readiness.
    status: Literal["REGISTERED", "NOT_IMPLEMENTED", "UNAVAILABLE", "AVAILABLE"] = "NOT_IMPLEMENTED"
    version: str = "UNKNOWN"
    calibration_status: str = "UNKNOWN"
    source: Source = "UNKNOWN"


class ValidationIssue(BaseModel):
    severity: Literal["ERROR", "WARNING", "INFO"]
    code: str
    path: str
    message: str


class ValidationResult(BaseModel):
    issues: list[ValidationIssue]
    config_valid: bool
    simulation_ready: bool
    experiment_ready: bool = False
    state: State


class ConfiguredScenario(BaseModel):
    scenario_id: str
    name: str
    family: str = "custom"
    environment: EnvironmentDefinition | None = None
    sites: list[SiteDefinition] = Field(default_factory=list)
    cells: list[CellDefinition] = Field(default_factory=list)
    antennas: list[AntennaDefinition] = Field(default_factory=list)
    ues: list[UEDefinition] = Field(default_factory=list)
    traffic: TrafficDefinition = Field(default_factory=TrafficDefinition)
    radio: RadioModelDefinition = Field(default_factory=RadioModelDefinition)
    network_functions: list[str] = Field(default_factory=list)
    optimization_problems: list[Problem] = Field(default_factory=list)
    candidate_hash: str | None = None
    source: Source = "USER_DEFINED"
    state: State = "DRAFT"
    version: int = 1
    definition_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
    lineage: dict[str, Any] = Field(default_factory=dict)


class ScenarioInstance(BaseModel):
    instance_id: str
    scenario_id: str
    scenario_version: int
    definition_hash: str
    asset_hashes: dict[str, str] = Field(default_factory=dict)
    seed: int
    frozen_definition: ConfiguredScenario
    identity_hash: str
    created_at: str
    run_status: str = "NOT_EXECUTED"


class Capability(BaseModel):
    capability_id: str
    name: str
    status: Literal["NOT_IMPLEMENTED", "FOUNDATION", "IMPLEMENTED", "VERIFIED", "ACCEPTANCE_EVIDENCE"]
    implementation_version: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    last_verified_at: str | None = None


class ProvenanceLink(BaseModel):
    object_type: Literal["ASSET", "DEFINITION", "INSTANCE", "RUN", "OBSERVATION", "EVIDENCE"]
    object_id: str
    status: str
    identity_hash: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class WorkspaceProvenanceChain(BaseModel):
    scenario_id: str
    links: list[ProvenanceLink]
