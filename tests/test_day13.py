from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from antenna.amatrix_adapter import AMatrixAdapter, AMatrixDataError, normalize_response
from antenna.geometry import GeometryError, compute_radio_geometry
from scenarios.service import ScenarioSystemService
from ue_twin.models import Position
from ue_twin.service import UETwinService, nearest_grid_indices

pytestmark = pytest.mark.unit


KEYS = {
    str(i): f"AAU5270E#16h4vssbcase0_8beam__tilt-2_azimuth0#{i}"
    for i in range(8)
}


def make_source(root: Path) -> Path:
    root.mkdir(parents=True)
    grid = np.full((91, 72), 0.25, dtype=np.float64)
    grid[45, 0] = 4.0
    payload = {"root": {"SSB": {key: grid + i * 0.01 for i, key in enumerate(KEYS.values())}}}
    np.save(root / "a_matrix_spread.npy", payload)
    np.save(root / "a_matrix_phase_power.npy", payload)
    (root / "profiles.json").write_text(json.dumps({"profiles": [{
        "id": "p1", "alias": "test", "library": "spread", "beam_type": "SSB",
        "multi_beam": True, "entry_key": KEYS["0"], "keys_by_beam": KEYS,
        "beam_ids": list(range(8)), "aau_type": "AAU5270E", "coverage": 0,
        "beam_id": 0, "normalize": True,
    }]}), encoding="utf-8")
    return root


def test_geometry_cardinals_and_wrap():
    east = compute_radio_geometry([0, 0, 0], [1, 0, 0])
    west = compute_radio_geometry([0, 0, 0], [-1, 0, 0])
    north = compute_radio_geometry([0, 0, 0], [0, 1, 0])
    above = compute_radio_geometry([0, 0, 0], [0, 0, 1])
    assert east.azimuth_deg == pytest.approx(0)
    assert west.azimuth_deg == pytest.approx(180)
    assert north.azimuth_deg == pytest.approx(90)
    assert above.elevation_deg == pytest.approx(90)
    with pytest.raises(GeometryError, match="SAME_POSITION"):
        compute_radio_geometry([0, 0, 0], [0, 0, 0])


def test_nearest_grid_uses_periodic_azimuth_and_upward_ties():
    cases = {
        0.0: 0,
        2.4: 0,
        2.5: 1,
        2.6: 1,
        4.9: 1,
        352.4: 70,
        352.5: 71,
        352.6: 71,
        357.4: 71,
        357.5: 0,
        357.6: 0,
        359.9: 0,
        360.0: 0,
    }
    for azimuth, expected_col in cases.items():
        row, col = nearest_grid_indices(0.0, azimuth)
        assert row == 45
        assert col == expected_col


def test_nearest_grid_elevation_bounds_and_upward_ties():
    cases = {
        -90.0: 0,
        -89.1: 0,
        -89.0: 1,
        -88.9: 1,
        0.0: 45,
        89.0: 90,
        90.0: 90,
    }
    for elevation, expected_row in cases.items():
        row, col = nearest_grid_indices(elevation, 0.0)
        assert row == expected_row
        assert col == 0


def test_amatrix_raw_normalized_and_zero_guard(tmp_path: Path):
    raw = np.zeros((91, 72), dtype=np.float64)
    raw[0, 1] = 2.0
    raw[1, 0] = 1.0
    raw[1, 1] = 3.0
    before = raw.copy()
    normalized, field, quality = normalize_response(raw)
    assert normalized.max() == pytest.approx(1.0)
    assert field[1, 1] == pytest.approx(1.0)
    assert np.array_equal(raw, before)
    assert quality.status == "VALID"
    with pytest.raises(AMatrixDataError) as zero_error:
        normalize_response(np.zeros((91, 72)))
    assert zero_error.value.code == "INVALID_A_MATRIX_RESPONSE"
    with pytest.raises(AMatrixDataError) as finite_error:
        normalize_response(np.full((91, 72), np.nan))
    assert finite_error.value.code == "INVALID_A_MATRIX_FINITE"
    _, _, warning = normalize_response(np.pad(np.array([[-1.0, 1.0]]), ((0, 90), (0, 70))))
    assert warning.status == "DATA_SEMANTICS_WARNING"


def test_adapter_supports_both_libraries_and_profile_mapping(tmp_path: Path):
    source = make_source(tmp_path / "a_matrix")
    adapter = AMatrixAdapter(source)
    libraries = adapter.libraries()
    assert {item.library_id for item in libraries} == {"spread", "phase_power"}
    pattern = adapter.pattern("phase_power", "SSB", KEYS["0"])
    assert pattern.angular_grid.axis_order == ["elevation", "azimuth"]
    assert max(max(row) for row in pattern.normalized_response) == pytest.approx(1.0)
    assert pattern.entry.mapping_status == "CONFIRMED_BY_PROFILE"


def test_ue_twin_geometry_and_relative_beam_ranking(tmp_path: Path):
    service = UETwinService(AMatrixAdapter(make_source(tmp_path / "a_matrix")))
    result = service.query(
        ue_id="UE-1", aau_id="AAU-1",
        aau_position=Position(x=0, y=0, z=10),
        ue_position=Position(x=20, y=0, z=10),
        profile_id="p1", serving_cell_id="CELL-1", neighbor_cell_ids=["CELL-2"],
    )
    assert result.radio_geometry.azimuth_deg == pytest.approx(0)
    assert result.radio_geometry.distance_3d_m == pytest.approx(20)
    assert len(result.beam_observations) == 8
    assert result.strongest_relative_beam_id == result.beam_observations[0].beam_id
    assert result.calibration_status == "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED"


def test_day12_counts_and_acceptance_set_are_separate():
    service = ScenarioSystemService()
    counts = service.coverage().counts
    assert counts.definition_verified_count == 120
    assert counts.experiment_verified_count == 0
    assert counts.acceptance_evidence_count == 0
    assert counts.verified_count == 0
    assert service.acceptance_scenario_set().status == "DRAFT"
