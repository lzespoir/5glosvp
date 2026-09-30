from __future__ import annotations

import hashlib
import json
from typing import Any


def verify_radio_observation(payload: dict[str, Any]) -> dict[str, Any]:
    """Verify an observation payload without constructing the production service."""
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    cells = payload.get("cells", [])
    identity = payload.get("identity", {})
    serving = payload.get("serving_neighbor", {})
    identity_fields = {key: identity.get(key) for key in (
        "scenario_id", "scenario_instance_id", "scenario_definition_hash", "radio_context_id",
        "radio_context_version", "cell_config_hash", "a_matrix_artifact_hashes", "normalization_policy",
        "angular_grid_version", "lookup_method", "propagation_backend", "calibration_status",
    )}
    expected_hash = hashlib.sha256(json.dumps(identity_fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    check("identity_hash", expected_hash == identity.get("identity_hash"), "identity hash recomputed from context and model fields")
    check("multi_cell", len(cells) >= 2 and len({item.get("cell", {}).get("site_id") for item in cells}) >= 2, "at least two cells and two sites")
    check("serving_neighbor", sum(item.get("role") == "SERVING" for item in cells) == 1 and serving.get("serving_cell_id") in {item.get("cell", {}).get("cell_id") for item in cells}, "one serving cell is bound to the observation context")
    check("geometry_and_units", all(item.get("geometry", {}).get("coordinate_convention") for item in cells) and all(item.get("propagation", {}).get("distance_m", {}).get("unit") == "m" for item in cells), "geometry and distance units are explicit")
    check("power_semantics", all(item.get("received_power", {}).get("total", {}).get("metric_name") == "SIM_RECEIVED_POWER" for item in cells), "power is simulation-derived and not labelled RSRP")
    check("calibration_boundary", payload.get("calibration_status") == "UNCALIBRATED_SIMULATION" and payload.get("absolute_radio_kpi_status") == "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED", "absolute KPI boundary is explicit")
    check("a_matrix_provenance", bool(identity.get("a_matrix_artifact_hashes")) and identity.get("normalization_policy") == "PEAK_LINEAR_POWER_TO_RELATIVE", "A-Matrix hash and normalization are bound")
    check("ue_twin_attachment", payload.get("ue_twin", {}).get("radio_observations", {}).get("observation_set_id") == payload.get("observation_set_id"), "Day13 UE Twin carries a reference to the RadioObservationSet")
    return {"verified": all(item["passed"] for item in checks), "checks": checks, "independent_of_production_service": True}
