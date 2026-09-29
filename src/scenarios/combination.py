from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Iterable, Iterator
from typing import Any

from .models import ScenarioDefinition
from .rules import evaluate
from .taxonomy import TAXONOMY, option_labels

DIMENSION_KEYS = [d.key for d in TAXONOMY.dimensions]
LABELS = option_labels()


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def normalize_selection(selection: dict[str, Any] | None) -> dict[str, list[str]]:
    selection = selection or {}
    result: dict[str, list[str]] = {}
    for dimension in TAXONOMY.dimensions:
        raw = selection.get(dimension.key)
        values = [str(x) for x in raw] if isinstance(raw, list) else ([str(raw)] if raw is not None else [o.value for o in dimension.options])
        allowed = {o.value for o in dimension.options}
        result[dimension.key] = [v for v in values if v in allowed] or [o.value for o in dimension.options]
    return result


def iter_dimension_combinations(selection: dict[str, Any] | None = None) -> Iterator[dict[str, str]]:
    normalized = normalize_selection(selection)
    for values in itertools.product(*(normalized[key] for key in DIMENSION_KEYS)):
        yield dict(zip(DIMENSION_KEYS, values, strict=True))


def scenario_from_dimensions(dimensions: dict[str, str]) -> ScenarioDefinition:
    status, reason_code, reason = evaluate(dimensions)
    family = "mixed"
    if dimensions["network_function"] == "coverage" or dimensions["optimization_problem"] == "NETWORK_STRUCTURE":
        family = "coverage_structure"
    elif dimensions["network_function"] == "user_access":
        family = "user_access_load"
    elif dimensions["network_function"] == "resource_scheduling":
        family = "resource_scheduling"
    elif dimensions["network_function"] == "handover":
        family = "mobility_handover"
    elif dimensions["traffic"] in {"hotspot_traffic", "time_varying", "measured_traffic", "beam_space_traffic"}:
        family = "traffic_hotspot"
    elif dimensions["radio_condition"].startswith("interference"):
        family = "interference"
    elif dimensions["device_antenna"] != "generic_simulation":
        family = "beam_antenna"
    identity = {
        "taxonomy_version": "0.1",
        "dimensions": dimensions,
        "model_bindings": {"channel": "simulation_baseline"},
        "dataset_bindings": {"traffic": dimensions["traffic"]},
        "artifact_bindings": {"device_antenna": dimensions["device_antenna"]},
    }
    digest = canonical_hash(identity)
    labels = {k: LABELS[k][v][0] for k, v in dimensions.items()}
    name_zh = " + ".join([labels["environment"], labels["topology"], labels["ue_population"] + " UE", labels["traffic"], labels["network_function"]])
    name_en = " + ".join([dimensions["environment"], dimensions["topology"], dimensions["ue_population"] + " UE", dimensions["traffic"], dimensions["network_function"]])
    executable = status == "VALID_EXECUTABLE"
    return ScenarioDefinition(
        scenario_id=f"SCN-D12-{digest[:10].upper()}", name_zh=name_zh, name_en=name_en,
        description=f"{name_zh}；规则结果：{reason}", taxonomy_version="0.1", scenario_family=family,
        dimensions=dimensions, compatibility_status=status, support_status="SUPPORTED" if executable else ("PARTIAL" if status == "VALID_NOT_EXECUTABLE" else "EXTERNAL_MODEL_REQUIRED"),
        model_bindings={"channel": "simulation_baseline", "reason_code": reason_code},
        dataset_bindings={"traffic_profile": dimensions["traffic"], "source_type": "simulation_or_pending_external"},
        artifact_bindings={"device_antenna": dimensions["device_antenna"]},
        supported_problem_types=[dimensions["optimization_problem"]], source="day12_taxonomy_v0.1",
        provenance={"rule_id": reason_code, "rule_reason_zh": reason, "seed_is_instance_only": True}, tags=[family, dimensions["environment"]],
        version="0.1", created_at="2026-09-29T00:00:00+00:00", scenario_definition_hash=digest,
        experiment_scenario_id="SIONNA-DEMO-001" if executable else None,
    )


def count_combinations(selection: dict[str, Any] | None = None) -> dict[str, int]:
    counts = {"theoretical_count": 1, "valid_count": 0, "invalid_count": 0, "executable_count": 0, "requires_external_asset_count": 0}
    normalized = normalize_selection(selection)
    for values in normalized.values():
        counts["theoretical_count"] *= len(values)
    for dimensions in iter_dimension_combinations(normalized):
        status, _, _ = evaluate(dimensions)
        if status == "INVALID_COMBINATION": counts["invalid_count"] += 1
        else: counts["valid_count"] += 1
        if status == "VALID_EXECUTABLE": counts["executable_count"] += 1
        if status == "REQUIRES_EXTERNAL_ASSET": counts["requires_external_asset_count"] += 1
    return counts
