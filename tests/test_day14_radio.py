from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from api.main import build_app
from radio import RadioObservabilityService, verify_radio_observation


pytestmark = pytest.mark.unit


def test_day14_context_is_multi_site_and_multi_ue():
    service = RadioObservabilityService()
    context = service.context("SCN-DAY14-MULTISITE-001")
    assert len(context.cells) == 3
    assert len({cell.site_id for cell in context.cells}) == 2
    assert len(context.ue_positions) == 3
    assert all(cell.tx_power_dbm is not None for cell in context.cells)
    assert all(cell.a_matrix_hash for cell in context.cells)


def test_day14_observation_reuses_geometry_and_exposes_honest_radio_status():
    service = RadioObservabilityService()
    result = service.observe("SCN-DAY14-MULTISITE-001", "UE-D14-001")
    assert len(result.cells) == 3
    assert result.serving_neighbor.serving_cell_id == "CELL-D14-A1"
    assert len(result.serving_neighbor.neighbor_cell_ids) == 2
    assert result.identity.lookup_method == "nearest_grid"
    assert result.calibration_status == "UNCALIBRATED_SIMULATION"
    assert result.absolute_radio_kpi_status == "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED"
    serving = next(item for item in result.cells if item.role == "SERVING")
    assert serving.received_power.total.metric_name == "SIM_RECEIVED_POWER"
    assert serving.interference is not None
    assert serving.interference.sinr.metric_name == "SIM_SINR"
    assert result.provenance["a_matrix_raw_npy_modified"] is False
    assert result.ue_twin["radio_observations"]["observation_set_id"] == result.observation_set_id
    assert verify_radio_observation(result.model_dump(mode="json"))["verified"] is True


def test_day14_api_serving_neighbor_and_interference_are_context_bound():
    with TestClient(build_app()) as client:
        base = "/api/v1/radio/scenarios/SCN-DAY14-MULTISITE-001/ues/UE-D14-002"
        observations = client.get(f"{base}/observations")
        serving = client.get(f"{base}/serving-neighbor")
        interference = client.get(f"{base}/interference")
    assert observations.status_code == 200
    assert serving.status_code == 200
    assert interference.status_code == 200
    assert observations.json()["identity"]["radio_context_id"] == "RC-D14-MULTISITE-001"
    assert serving.json()["serving_selection_source"] == "SCENARIO_DEFINED"
    assert interference.json()["sinr"]["calibration_status"] == "UNCALIBRATED_SIMULATION"
