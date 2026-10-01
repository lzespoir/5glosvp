"""Stateless candidate preview DTOs; candidates are not configured scenarios."""

from __future__ import annotations

import itertools
from math import prod
from typing import Any

from pydantic import BaseModel

from .combination import DIMENSION_KEYS, scenario_from_dimensions
from .taxonomy import TAXONOMY

MAX_PREVIEW_SPACE = 5_000
MAX_RETURNED_CANDIDATES = 100


class ScenarioCandidate(BaseModel):
    candidate_id: str
    candidate_hash: str
    taxonomy_version: str
    name_zh: str
    name_en: str
    scenario_family: str
    dimensions: dict[str, str]
    compatibility_status: str
    support_status: str
    supported_problem_types: list[str]
    source: str = "CANDIDATE_ASSISTANT"
    acceptance_eligible: bool = False


class ScenarioCandidatePreview(BaseModel):
    theoretical_count: int
    valid_candidate_count: int
    invalid_candidate_count: int
    executable_candidate_count: int
    external_dependency_candidate_count: int
    returned_count: int
    truncated: bool
    items: list[ScenarioCandidate]
    persisted: bool = False
    configured_count_changed: bool = False


class ScenarioCandidateService:
    def preview(self, selection: dict[str, Any], limit: int = 50) -> ScenarioCandidatePreview:
        if not 1 <= limit <= MAX_RETURNED_CANDIDATES:
            raise ValueError("CANDIDATE_PREVIEW_LIMIT_INVALID")
        if set(selection) != set(DIMENSION_KEYS):
            raise ValueError("CANDIDATE_SELECTION_INCOMPLETE")

        normalized: dict[str, list[str]] = {}
        for dimension in TAXONOMY.dimensions:
            raw = selection.get(dimension.key)
            values = [str(value) for value in raw] if isinstance(raw, list) else []
            allowed = {option.value for option in dimension.options}
            if not values or len(values) != len(set(values)) or any(value not in allowed for value in values):
                raise ValueError("CANDIDATE_SELECTION_INVALID")
            normalized[dimension.key] = values

        theoretical = prod(len(normalized[key]) for key in DIMENSION_KEYS)
        if theoretical > MAX_PREVIEW_SPACE:
            raise ValueError("CANDIDATE_SPACE_TOO_LARGE")

        total = invalid = executable = external = 0
        items: list[ScenarioCandidate] = []
        # The bounded product is intentionally enumerated in memory only; no catalog write occurs.
        for values in itertools.product(*(normalized[key] for key in DIMENSION_KEYS)):
            dimensions = dict(zip(DIMENSION_KEYS, values, strict=True))
            definition = scenario_from_dimensions(dimensions)
            if definition.compatibility_status == "INVALID_COMBINATION":
                invalid += 1
                continue
            total += 1
            executable += definition.compatibility_status == "VALID_EXECUTABLE"
            external += definition.compatibility_status == "REQUIRES_EXTERNAL_ASSET"
            if len(items) < limit:
                items.append(ScenarioCandidate(
                    candidate_id="CAND-" + definition.scenario_definition_hash[:16].upper(),
                    candidate_hash=definition.scenario_definition_hash,
                    taxonomy_version=definition.taxonomy_version,
                    name_zh=definition.name_zh,
                    name_en=definition.name_en,
                    scenario_family=definition.scenario_family,
                    dimensions=dimensions,
                    compatibility_status=definition.compatibility_status,
                    support_status=definition.support_status,
                    supported_problem_types=definition.supported_problem_types,
                ))

        return ScenarioCandidatePreview(
            theoretical_count=theoretical,
            valid_candidate_count=total,
            invalid_candidate_count=invalid,
            executable_candidate_count=executable,
            external_dependency_candidate_count=external,
            returned_count=len(items),
            truncated=total > len(items),
            items=items,
        )
