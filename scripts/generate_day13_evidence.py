from __future__ import annotations

import json
from pathlib import Path

from antenna import AMatrixAdapter
from scenarios.service import ScenarioSystemService
from ue_twin.service import UETwinService, nearest_grid_indices
from ue_twin.models import Position


def write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "reference" / "day13" / "SCN-DAY13-AMATRIX-UE-TWIN"
    out.mkdir(parents=True, exist_ok=True)
    adapter = AMatrixAdapter()
    libraries = adapter.libraries()
    profiles = adapter.profiles()
    manifests = adapter.manifest()
    profile = profiles[0]
    entry_key = profile["keys_by_beam"][str(profile["beam_ids"][0])]
    pattern = adapter.pattern(profile["library"], profile["beam_type"], entry_key)
    twin_service = UETwinService(adapter)
    twin = twin_service.query(
        ue_id="UE-D13-EVIDENCE-001",
        aau_id=profile.get("aau_type", "AAU-D13-001"),
        aau_position=Position(x=0, y=0, z=10, source="DAY13_EVIDENCE"),
        ue_position=Position(x=20, y=0, z=1.5, source="DAY13_EVIDENCE"),
        profile_id=profile["id"],
        serving_cell_id="CELL-D13-SERVING",
        neighbor_cell_ids=["CELL-D13-N1", "CELL-D13-N2"],
    )
    scenario = ScenarioSystemService().catalog.definitions()[0]
    write(out / "amatrix-manifest.json", [item.model_dump(mode="json") for item in manifests])
    write(out / "angular-grid.json", pattern.angular_grid.model_dump(mode="json"))
    write(out / "beam-profile-mapping.json", {"mapping_version": "sionnatest-profiles-v1", "status": "PARTIAL_BY_SOURCE_SEMANTICS", "profiles": profiles})
    write(out / "ue-twin-example.json", twin.model_dump(mode="json"))
    write(out / "beam-response-example.json", {"lookup_method": "nearest_grid", "pattern": pattern.model_dump(mode="json"), "observations": [item.model_dump(mode="json") for item in twin.beam_observations]})
    lookup_cases = [
        {"elevation_deg": 0.0, "azimuth_deg": azimuth}
        for azimuth in (0.0, 2.4, 2.5, 2.6, 4.9, 352.4, 352.6, 357.4, 357.6, 359.9, 360.0)
    ]
    write(
        out / "lookup-boundary-checks.json",
        [
            {
                **case,
                "grid_row": nearest_grid_indices(case["elevation_deg"], case["azimuth_deg"])[0],
                "grid_col": nearest_grid_indices(case["elevation_deg"], case["azimuth_deg"])[1],
                "tie_policy": "UPWARD_GRID_VALUE",
            }
            for case in lookup_cases
        ],
    )
    write(out / "scenario-identity-example.json", twin_service.scenario_identity(scenario.model_dump(mode="json"), profile["id"]))
    write(out / "source-libraries.json", [item.model_dump(mode="json") for item in libraries])
    write(out / "README.md", """# DAY13 A-Matrix / UE Twin evidence\n\nThis evidence uses the read-only A-Matrix source configured for `sionnatest`. It records normalized relative beam response and Cartesian UE geometry only. It does not claim calibrated absolute RSRP, SINR, throughput, or handover.\n\n- `amatrix-manifest.json`: source hashes, sizes, entry counts, and normalization contract.\n- `angular-grid.json`: the SionnaTest implementation convention, not an owner-confirmed measurement metadata claim.\n- `beam-profile-mapping.json`: profiles.json mappings and their partial semantic status.\n- `ue-twin-example.json`: serving/neighbor context and geometry.\n- `beam-response-example.json`: nearest-grid per-beam normalized response.\n- `lookup-boundary-checks.json`: periodic azimuth nearest-grid cases and explicit upward half-step tie policy.\n- `scenario-identity-example.json`: A-Matrix binding fields for scientific identity.\n- `verification.json`: independently recomputed source, normalization, geometry, lookup and identity checks.\n\nThe raw `.npy` files remain outside the 5glosvp Git repository and are not copied here.\n""")


if __name__ == "__main__":
    main()
