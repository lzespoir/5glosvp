from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from scenarios.models import AcceptanceMapping, AcceptanceScenarioSet, CompatibilityRule, ScenarioCoverage, ScenarioDefinition, ScenarioPreview, ScenarioTaxonomy, ScenarioWorkspace


class ScenarioPreviewRequest(BaseModel):
    selection: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=100, ge=1, le=500)


class ScenarioCatalogResponse(BaseModel):
    items: list[ScenarioDefinition]
    total: int
    offset: int
    limit: int
    catalog_semantics: str = "LEGACY_CANDIDATE_CATALOG"
    acceptance_eligible: bool = False


class ScenarioMaterializeRequest(BaseModel):
    scenario_id: str
    seed: int = 0


class ScenarioSystemResponse(BaseModel):
    taxonomy: ScenarioTaxonomy


class ScenarioRulesResponse(BaseModel):
    items: list[CompatibilityRule]


class AcceptanceResponse(BaseModel):
    items: list[AcceptanceMapping]


class AcceptanceScenarioSetResponse(BaseModel):
    item: AcceptanceScenarioSet


class ScenarioVerifyResponse(BaseModel):
    verified: bool
    verifier_id: str
    verifier_version: str
    unique_semantic_definitions: int
    valid_definitions: int
    family_counts: dict[str, int]
    duplicate_canonical_definitions: list[str]
    seed_only_duplicates: list[str]
    mismatches: list[str]
    counts: dict[str, Any]
