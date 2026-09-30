from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SupportState = Literal["SUPPORTED", "PARTIAL", "PLANNED", "DEFINED_NOT_EXECUTABLE", "EXTERNAL_MODEL_REQUIRED", "REQUIRES_EXTERNAL_DATA"]
CompatibilityStatus = Literal["VALID_EXECUTABLE", "VALID_NOT_EXECUTABLE", "INVALID_COMBINATION", "REQUIRES_EXTERNAL_ASSET"]


class TaxonomyOption(BaseModel):
    value: str
    label_zh: str
    label_en: str
    status: SupportState = "SUPPORTED"
    description_zh: str = ""


class TaxonomyDimension(BaseModel):
    key: str
    label_zh: str
    label_en: str
    options: list[TaxonomyOption]


class ScenarioTaxonomy(BaseModel):
    taxonomy_version: str
    dimensions: list[TaxonomyDimension]
    families: list[dict[str, str]]


class CompatibilityRule(BaseModel):
    rule_id: str
    description_zh: str
    input_dimensions: list[str]
    result: CompatibilityStatus
    reason_code: str
    reason_zh: str


class ScenarioDefinition(BaseModel):
    scenario_id: str
    name_zh: str
    name_en: str
    description: str
    taxonomy_version: str
    scenario_family: str
    dimensions: dict[str, str]
    compatibility_status: CompatibilityStatus
    support_status: SupportState
    model_bindings: dict[str, Any] = Field(default_factory=dict)
    dataset_bindings: dict[str, Any] = Field(default_factory=dict)
    artifact_bindings: dict[str, Any] = Field(default_factory=dict)
    supported_problem_types: list[str] = Field(default_factory=list)
    source: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    version: str
    created_at: str
    scenario_definition_hash: str
    experiment_scenario_id: str | None = None


class ScenarioInstance(BaseModel):
    scenario_instance_id: str
    scenario_id: str
    scenario_version: str
    scenario_definition_hash: str
    seed: int
    status: str
    identity: dict[str, Any]


class ScenarioCounts(BaseModel):
    theoretical_count: int
    valid_count: int
    invalid_count: int
    executable_count: int
    requires_external_asset_count: int
    materialized_count: int = 0
    executed_count: int = 0
    definition_verified_count: int = 0
    experiment_verified_count: int = 0
    verified_count: int = 0
    acceptance_evidence_count: int = 0


class AcceptanceScenarioSet(BaseModel):
    set_id: str = "ASC-D13-DRAFT"
    name: str = "Day 13 Acceptance Scenario Set"
    version: str = "0.1"
    selection_policy: str = "COVERAGE_DRIVEN_NOT_SELECTED"
    scenario_ids: list[str] = Field(default_factory=list)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    status: str = "DRAFT"
    evidence_status: str = "NOT_SELECTED"


class ScenarioPreview(BaseModel):
    counts: ScenarioCounts
    combinations: list[ScenarioDefinition]
    truncated: bool = False


class ScenarioCoverageCell(BaseModel):
    row: str
    column: str
    dimensions: dict[str, str]
    counts: ScenarioCounts
    evidence: list[str] = Field(default_factory=list)


class ScenarioCoverage(BaseModel):
    counts: ScenarioCounts
    matrix: list[ScenarioCoverageCell]
    family_counts: dict[str, ScenarioCounts]


class AcceptanceMapping(BaseModel):
    key: str
    title_zh: str
    title_en: str
    status: str
    evidence: list[str]
    note_zh: str


class ScenarioWorkspace(BaseModel):
    workspace_status: str
    scenario: ScenarioDefinition
    scenario_instance: ScenarioInstance
    experiment_identity: dict[str, Any]
    message_zh: str
