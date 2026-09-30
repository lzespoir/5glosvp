from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AngularGrid(BaseModel):
    version: str = "D13-ANGULAR-GRID-0.1"
    elevation_min_deg: float = -90.0
    elevation_max_deg: float = 90.0
    elevation_step_deg: float = 2.0
    elevation_count: int = 91
    azimuth_min_deg: float = 0.0
    azimuth_max_sample_deg: float = 355.0
    azimuth_period_deg: float = 360.0
    azimuth_step_deg: float = 5.0
    azimuth_count: int = 72
    axis_order: list[str] = Field(default_factory=lambda: ["elevation", "azimuth"])
    convention_source: str = "SIONNATEST_IMPLEMENTATION"


class DataQuality(BaseModel):
    shape: list[int]
    dtype: str
    finite: bool
    nan_count: int
    inf_count: int
    negative_count: int
    min_value: float
    max_value: float
    all_zero: bool
    status: Literal["VALID", "DATA_SEMANTICS_WARNING", "INVALID"]


class AMatrixEntry(BaseModel):
    entry_key: str
    raw_shape: list[int]
    dtype: str
    beam_id: int | None = None
    beam_family: str
    beam_type: str
    aau_type: str | None = None
    coverage: int | None = None
    tilt_deg: int | None = None
    azimuth_deg: int | None = None
    source_file_name: str
    source_hash: str
    mapping_status: Literal["CONFIRMED_BY_PROFILE", "PARTIAL", "UNKNOWN"]
    data_quality: DataQuality


class AMatrixLibrary(BaseModel):
    library_id: str
    family: str
    source_file_name: str
    source_artifact: str
    source_hash: str
    entry_count: int
    beam_types: dict[str, int]
    semantic_status: str = "RELATIVE_RESPONSE_ONLY"


class NormalizationPolicy(BaseModel):
    policy_id: str = "PEAK_LINEAR_POWER_TO_RELATIVE"
    formula: str = "normalized_response = raw_response / max(raw_response)"
    field_amplitude_formula: str = "field_amplitude = sqrt(max(normalized_response, 0))"
    negative_value_policy: str = "WARN_AND_PRESERVE_RAW"
    source_semantic_status: str = "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED"


class BeamPattern(BaseModel):
    entry: AMatrixEntry
    angular_grid: AngularGrid
    normalization: NormalizationPolicy
    lookup_method: str = "nearest_grid"
    normalized_response: list[list[float]]
    field_amplitude: list[list[float]]


class BeamResponse(BaseModel):
    beam_id: int
    entry_key: str
    azimuth_deg: float
    elevation_deg: float
    grid_row: int
    grid_col: int
    normalized_response: float
    rank: int
    lookup_method: str = "nearest_grid"


class RadioGeometry(BaseModel):
    distance_3d_m: float
    azimuth_deg: float
    elevation_deg: float
    coordinate_convention: str


class AMatrixManifest(BaseModel):
    manifest_version: str = "0.1"
    artifact_id: str
    source_family: str
    source_file_name: str
    source_hash: str
    source_size_bytes: int
    source_mtime_ns: int
    entry_count: int
    shape: list[int]
    dtype: str
    angular_grid_version: str
    normalization_policy: str
    profile_mapping_version: str
    semantic_status: str


class AMatrixSourceStatus(BaseModel):
    source_path: str
    files: list[dict[str, Any]]
    modified: bool = False
    committed: bool = False
