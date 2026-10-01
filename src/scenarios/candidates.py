"""Stateless, deterministic candidate preview; candidates are not configured scenarios."""

from __future__ import annotations

import hashlib
import itertools
import json
from math import prod
from typing import Any

from pydantic import BaseModel

from .combination import DIMENSION_KEYS, scenario_from_dimensions
from .taxonomy import TAXONOMY

MAX_PREVIEW_SPACE = 5_000
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


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
    filtered_candidate_count: int
    total: int
    offset: int
    limit: int
    returned_count: int
    has_more: bool
    truncated: bool
    query_hash: str
    taxonomy_version: str
    items: list[ScenarioCandidate]
    persisted: bool = False
    configured_count_changed: bool = False
    acceptance_eligible: bool = False

class ScenarioCandidateService:
    def preview(
        self,
        selection: dict[str, Any],
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        query_hash: str | None = None,
    ) -> ScenarioCandidatePreview:
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError("CANDIDATE_PAGE_LIMIT_INVALID")
        if offset < 0:
            raise ValueError("CANDIDATE_OFFSET_INVALID")
        if set(selection) != set(DIMENSION_KEYS):
            raise ValueError("CANDIDATE_SELECTION_INCOMPLETE")

        normalized: dict[str, list[str]] = {}
        option_orders: dict[str, dict[str, int]] = {}
        for dimension in TAXONOMY.dimensions:
            allowed_order = {option.value: index for index, option in enumerate(dimension.options)}
            raw = selection.get(dimension.key)
            values = [str(value) for value in raw] if isinstance(raw, list) else []
            if not values or len(values) != len(set(values)) or any(value not in allowed_order for value in values):
                raise ValueError("CANDIDATE_SELECTION_INVALID")
            option_orders[dimension.key] = allowed_order
            normalized[dimension.key] = sorted(values, key=allowed_order.__getitem__)

        normalized_filters: dict[str, list[str]] = {}
        for key, raw in (filters or {}).items():
            if key not in normalized:
                raise ValueError("CANDIDATE_FILTER_UNKNOWN")
            values = [str(value) for value in raw] if isinstance(raw, list) else [str(raw)]
            if not values or any(value not in normalized[key] for value in values):
                raise ValueError("CANDIDATE_FILTER_INVALID")
            normalized_filters[key] = sorted(set(values), key=option_orders[key].__getitem__)

        theoretical = prod(len(normalized[key]) for key in DIMENSION_KEYS)
        if theoretical > MAX_PREVIEW_SPACE:
            raise ValueError("CANDIDATE_SPACE_TOO_LARGE")

        taxonomy_version = TAXONOMY.taxonomy_version
        query_payload = {
            "taxonomy_version": taxonomy_version,
            "selection": normalized,
            "filters": normalized_filters,
        }
        current_query_hash = hashlib.sha256(
            json.dumps(query_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if query_hash and query_hash != current_query_hash:
            raise ValueError("CANDIDATE_QUERY_STALE")

        valid = invalid = executable = external = filtered = 0
        items: list[ScenarioCandidate] = []
        page_end = offset + limit
        # Enumerate a bounded search space in taxonomy order, retaining only the requested page.
        for values in itertools.product(*(normalized[key] for key in DIMENSION_KEYS)):
            dimensions = dict(zip(DIMENSION_KEYS, values, strict=True))
            definition = scenario_from_dimensions(dimensions)
            if definition.compatibility_status == "INVALID_COMBINATION":
                invalid += 1
                continue
            valid += 1
            executable += definition.compatibility_status == "VALID_EXECUTABLE"
            external += definition.compatibility_status == "REQUIRES_EXTERNAL_ASSET"
            if any(dimensions[key] not in selected for key, selected in normalized_filters.items()):
                continue
            current_index = filtered
            filtered += 1
            if offset <= current_index < page_end:
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

        has_more = offset + len(items) < filtered
        return ScenarioCandidatePreview(
            theoretical_count=theoretical,
            valid_candidate_count=valid,
            invalid_candidate_count=invalid,
            executable_candidate_count=executable,
            external_dependency_candidate_count=external,
            filtered_candidate_count=filtered,
            total=filtered,
            offset=offset,
            limit=limit,
            returned_count=len(items),
            has_more=has_more,
            truncated=has_more,
            query_hash=current_query_hash,
            taxonomy_version=taxonomy_version,
            items=items,
        )
