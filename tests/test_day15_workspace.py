"""Independent Day15 workspace contract tests; no simulation is claimed or run."""

from __future__ import annotations

from types import SimpleNamespace
import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from api.routes.workspace import router
from workspace.models import (
    AntennaBinding, AntennaDefinition, CellCoreConfig, CellDefinition, CoordinateReference,
    EnvironmentDefinition, SiteDefinition, UEDefinition, Position, Parameter,
    TrafficDefinition, RadioModelDefinition, MapLayer,
)
from workspace.service import CAPABILITIES, NetworkImporter, ScenarioValidator, WorkspaceService

pytestmark = pytest.mark.unit


def test_network_import_is_explicitly_contract_only():
    capability = next(item for item in CAPABILITIES if item.capability_id == "NETWORK_IMPORT")
    assert capability.status == "NOT_IMPLEMENTED"
    assert "no CSV/GeoJSON/vendor parser" in capability.limitations[0]
    assert "import_network" in NetworkImporter.__dict__


class StubAMatrix:
    def profiles(self):
        return [{"id": "PROFILE-TEST", "library": "spread", "beam_ids": list(range(8))}]

    def manifest(self):
        return [SimpleNamespace(source_family="8_BEAM_FAMILY", artifact_id="AMX-TEST", source_hash="HASH-TEST")]


def coordinate():
    return CoordinateReference(coordinate_system="SIONNA_SCENE_CARTESIAN", unit="m", origin="TEST_DECLARED", source="USER_DEFINED", status="DECLARED")


def populated(service: WorkspaceService):
    row = service.create("multi-site smoke", "urban")
    row.environment = EnvironmentDefinition(environment_id="ENV-TEST", coordinate=coordinate())
    row.sites = [SiteDefinition(site_id="SITE-1", name="Site", position=Position(x=0, y=0, z=10, coordinate=coordinate()))]
    row.antennas = [AntennaDefinition(antenna_definition_id="ANT-1", name="test", provider_type="A_MATRIX", provider_status="IMPLEMENTED", source="IMPORTED", beam_count=8, coordinate=coordinate(), normalization="PEAK_LINEAR_POWER_TO_RELATIVE", calibration_status="RELATIVE_ONLY", supported_backends=["FAST_PROPAGATION"], artifact_id="AMX-TEST", artifact_hash="HASH-TEST", profile_id="PROFILE-TEST")]
    row.cells = [CellDefinition(cell_id="CELL-1", site_id="SITE-1", name="Cell", core=CellCoreConfig(carrier_frequency=Parameter(value=3.5e9, unit="Hz", source="USER_DEFINED"), bandwidth=Parameter(value=100e6, unit="Hz", source="USER_DEFINED"), tx_power=Parameter(value=46, unit="dBm", source="USER_DEFINED")), antenna=AntennaBinding(antenna_definition_id="ANT-1", source="USER_DEFINED"))]
    row.ues = [UEDefinition(ue_id="UE-1", position=Position(x=20, y=10, z=1.5, coordinate=coordinate()), mobility="STATIC", traffic_profile="full_buffer", serving_cell_id="CELL-1")]
    row.traffic = TrafficDefinition(kind="FULL_BUFFER", availability="AVAILABLE", source="USER_DEFINED")
    row.radio = RadioModelDefinition(backend="FAST_PROPAGATION", status="REGISTERED", version="D14-FAST-PROPAGATION-0.1", calibration_status="UNCALIBRATED_SIMULATION", source="USER_DEFINED")
    row.optimization_problems = ["USER_ACCESS"]
    return service.save(row)


def test_definition_instance_boundaries(tmp_path):
    service = WorkspaceService(tmp_path)
    service.validator = ScenarioValidator(StubAMatrix())
    row = populated(service)
    check = service.validate(row)
    assert check.config_valid
    assert not check.simulation_ready
    assert not check.experiment_ready
    assert row.state == "VALID"
    assert any(item.code == "EXECUTION_ADAPTER_NOT_IMPLEMENTED" for item in check.issues)
    assert service.counts() == {"configured_scenario_count": 1, "runnable_scenario_count": 0, "executed_scenario_count": 0, "experiment_verified_count": 0, "acceptance_evidence_count": 0}
    frozen = service.materialize(row.scenario_id, seed=7)
    assert frozen.run_status == "NOT_EXECUTED"
    assert frozen.frozen_definition.definition_hash == row.definition_hash
    assert service.save(row).version == row.version  # no-op must not increment
    row.name = "revised"
    revised = service.save(row)
    assert revised.version == row.version + 1
    assert revised.definition_hash != frozen.definition_hash
    assert service.get_instance(frozen.instance_id).frozen_definition.name == "multi-site smoke"
    clone = service.clone(revised.scenario_id)
    assert clone.scenario_id != revised.scenario_id and clone.candidate_hash is None
    assert clone.lineage["source_hash"] == revised.definition_hash
    service.archive(clone.scenario_id)
    assert service.counts()["configured_scenario_count"] == 1


def test_provider_provenance_and_coordinate_guard(tmp_path):
    service = WorkspaceService(tmp_path)
    service.validator = ScenarioValidator(StubAMatrix())
    row = populated(service)
    row.antennas[0].artifact_hash = "FORGED"
    check = service.validate(row)
    assert not check.config_valid
    assert "A_MATRIX_PROVENANCE_MISMATCH" in {item.code for item in check.issues}
    row.antennas[0].artifact_hash = "HASH-TEST"
    row.sites[0].position.coordinate.unit = "km"
    check = service.validate(row)
    assert "COORDINATE_MISMATCH" in {item.code for item in check.issues}


def test_unspecified_traffic_ue_and_radio_are_not_silently_valid(tmp_path):
    service = WorkspaceService(tmp_path)
    service.validator = ScenarioValidator(StubAMatrix())
    row = populated(service)
    row.traffic = TrafficDefinition()
    row.ues[0].mobility = "UNKNOWN"
    row.ues[0].traffic_profile = "UNKNOWN"
    row.radio = RadioModelDefinition()
    check = service.validate(row)
    codes = {item.code for item in check.issues}
    assert not check.config_valid
    assert {"TRAFFIC_UNSPECIFIED", "UE_MOBILITY_UNSPECIFIED", "UE_TRAFFIC_PROFILE_UNSPECIFIED", "RADIO_BACKEND_UNSPECIFIED"} <= codes


def test_legacy_radio_available_status_remains_readable_but_not_ready(tmp_path):
    service = WorkspaceService(tmp_path)
    service.validator = ScenarioValidator(StubAMatrix())
    row = populated(service)
    stored = row.model_dump(mode="json")
    stored["radio"]["status"] = "AVAILABLE"
    service.store.write("scenarios", row.scenario_id, stored)
    restored = service.get(row.scenario_id)
    check = service.validate(restored)
    assert restored.radio.status == "AVAILABLE"
    assert not check.simulation_ready
    assert any(issue.code == "RADIO_BACKEND_NOT_REGISTERED" for issue in check.issues)


def test_cell_and_map_layer_coordinate_and_reference_integrity(tmp_path):
    service = WorkspaceService(tmp_path)
    service.validator = ScenarioValidator(StubAMatrix())
    row = populated(service)
    row.cells[0].position = Position(x=0, y=0, z=10, coordinate=coordinate())
    row.cells[0].position.coordinate.unit = "km"
    row.environment.layers = [
        MapLayer(layer_id="dup", kind="BUILDINGS", visible=True, source_asset_id="MISSING", status="DECLARED"),
        MapLayer(layer_id="dup", kind="BUILDINGS", visible=False, source_asset_id="MISSING", status="DECLARED"),
    ]
    check = service.validate(row)
    codes = {item.code for item in check.issues}
    assert "COORDINATE_MISMATCH" in codes
    assert "MAP_LAYER_DUPLICATE" in codes
    assert "MAP_LAYER_ASSET_UNKNOWN" in codes


def test_batch_edit_includes_cell_height_and_updates_version(tmp_path):
    service = WorkspaceService(tmp_path)
    service.validator = ScenarioValidator(StubAMatrix())
    row = populated(service)
    updated = service.batch_edit_cells(
        row.scenario_id,
        ["CELL-1"],
        {"antenna_height": Parameter(value=25, unit="m", source="USER_DEFINED")},
        row.version,
    )
    assert updated.cells[0].core.antenna_height.value == 25
    assert updated.cells[0].version == 2
    assert updated.version == row.version + 1


def test_asset_registration_metadata_only(tmp_path):
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    source = asset_dir / "scene.gltf"
    source.write_text('{"asset":{"version":"2.0"},"scenes":[{}],"nodes":[{}],"meshes":[]}', encoding="utf-8")
    service = WorkspaceService(tmp_path / "store")
    asset = service.register_asset(name="Scene", asset_type="GLTF", source_path=str(source), coordinate=coordinate())
    assert asset.sha256 and asset.size_bytes
    assert asset.metadata["scene_count"] == 1
    assert asset.conversion_status == "NOT_CONVERTED"
    assert not asset.supported_backends


def test_asset_outside_allowlist_rejected(tmp_path):
    source = tmp_path / "secret.gltf"
    source.write_text('{}', encoding="utf-8")
    service = WorkspaceService(tmp_path / "workspace")
    with pytest.raises(ValueError, match="ASSET_OUTSIDE_ALLOWED_ROOTS"):
        service.register_asset(name="outside", asset_type="GLTF", source_path=str(source))


def test_api_candidate_separation_and_version_conflict(tmp_path):
    service = WorkspaceService(tmp_path)
    app = FastAPI()
    app.state.workspace_service = service
    app.include_router(router, prefix="/api/v1")
    with TestClient(app) as client:
        assert client.get("/api/v1/workspace/scenarios").json()["total"] == 0
        created = client.post("/api/v1/workspace/scenarios", json={"name": "Configured scene"})
        assert created.status_code == 201
        row = created.json()
        assert client.get("/api/v1/workspace/counts").json()["configured_scenario_count"] == 1
        patch = client.patch(f"/api/v1/workspace/scenarios/{row['scenario_id']}/basic", json={"expected_version": 1, "value": {"name": "Renamed"}})
        assert patch.status_code == 200 and patch.json()["version"] == 2
        conflict = client.patch(f"/api/v1/workspace/scenarios/{row['scenario_id']}/basic", json={"expected_version": 1, "value": {"name": "Old writer"}})
        assert conflict.status_code == 409
        models = client.get("/api/v1/workspace/radio/models").json()["items"]
        assert models[0]["source"] == "USER_DEFINED"
        radio_patch = client.patch(f"/api/v1/workspace/scenarios/{row['scenario_id']}/radio", json={"expected_version": 2, "value": {"backend": models[0]["backend"], "status": models[0]["status"], "version": models[0]["version"], "calibration_status": models[0]["calibration_status"], "source": models[0]["source"]}})
        assert radio_patch.status_code == 200
        assert radio_patch.json()["radio"]["source"] == "USER_DEFINED"
        invalid = client.get(f"/api/v1/workspace/scenarios/{row['scenario_id']}/validation").json()
        assert not invalid["config_valid"] and not invalid["simulation_ready"]
        assert client.post(f"/api/v1/workspace/scenarios/{row['scenario_id']}/instances", json={"seed": 1}).status_code == 422


def test_large_configuration_is_not_simulation(tmp_path):
    service = WorkspaceService(tmp_path)
    row = service.create("1000-cell configuration smoke")
    row.environment = EnvironmentDefinition(environment_id="ENV-SCALE", coordinate=coordinate())
    row.sites = [SiteDefinition(site_id="SITE-SCALE", name="scale", position=Position(x=0, y=0, z=10, coordinate=coordinate()))]
    row.cells = [CellDefinition(cell_id=f"CELL-{index:04d}", site_id="SITE-SCALE", name=f"Cell {index}") for index in range(1000)]
    saved = service.save(row)
    assert len(service.get(saved.scenario_id).cells) == 1000
    assert service.counts()["runnable_scenario_count"] == 0


def test_125_configured_definitions_are_paginated_not_executed(tmp_path):
    service = WorkspaceService(tmp_path)
    for index in range(125):
        service.create(f"configured-{index:03d}", "scale-smoke")
    first = service.list(limit=20)
    last = service.list(offset=120, limit=20)
    assert first["total"] == 125 and len(first["items"]) == 20 and len(last["items"]) == 5
    assert service.list(family="scale-smoke")["total"] == 125
    counts = service.counts()
    assert counts["configured_scenario_count"] == 125
    assert counts["runnable_scenario_count"] == counts["executed_scenario_count"] == counts["acceptance_evidence_count"] == 0
    verifier = Path(__file__).resolve().parents[1] / "tools" / "day15_independent_verify.py"
    audit = subprocess.run([sys.executable, str(verifier), str(tmp_path)], capture_output=True, text=True, check=True)
    report = json.loads(audit.stdout)
    assert report["result"] == "PASS" and report["scenario_definition_count"] == 125
