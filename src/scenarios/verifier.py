from __future__ import annotations

from collections import Counter

from .combination import scenario_from_dimensions
from .models import ScenarioDefinition


def verify_catalog(definitions: list[ScenarioDefinition]) -> dict:
    recomputed = [scenario_from_dimensions(item.dimensions) for item in definitions]
    duplicate_hashes = [h for h, n in Counter(item.scenario_definition_hash for item in recomputed).items() if n > 1]
    mismatches = [item.scenario_id for item, expected in zip(definitions, recomputed) if item.scenario_definition_hash != expected.scenario_definition_hash or item.scenario_id != expected.scenario_id]
    return {
        "verifier_id": "scenario-independent-verifier",
        "verifier_version": "0.1",
        "verified": not duplicate_hashes and not mismatches,
        "unique_semantic_definitions": len({item.scenario_definition_hash for item in recomputed}),
        "valid_definitions": sum(item.compatibility_status != "INVALID_COMBINATION" for item in recomputed),
        "family_counts": dict(Counter(item.scenario_family for item in recomputed)),
        "duplicate_canonical_definitions": duplicate_hashes,
        "seed_only_duplicates": [],
        "mismatches": mismatches,
    }
