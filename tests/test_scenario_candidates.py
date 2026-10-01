from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.scenario_candidates import router as candidate_router
from api.routes.workspace import router as workspace_router
from scenarios.combination import DIMENSION_KEYS
from scenarios.taxonomy import TAXONOMY
from workspace.service import WorkspaceService

import pytest

pytestmark = pytest.mark.unit


def supported_dimensions():
    choices = {dimension.key: dimension.options[0].value for dimension in TAXONOMY.dimensions}
    choices.update({"network_function": "coverage", "optimization_problem": "NETWORK_STRUCTURE"})
    return choices


def selection_for(dimensions):
    return {key: [dimensions[key]] for key in DIMENSION_KEYS}


def client_for(tmp_path):
    app = FastAPI()
    app.state.workspace_service = WorkspaceService(tmp_path)
    app.include_router(candidate_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")
    return TestClient(app)


def test_preview_is_stateless_and_explicit_promotion_persists_one_draft(tmp_path):
    dimensions = supported_dimensions()
    with client_for(tmp_path) as client:
        before = client.get("/api/v1/workspace/counts").json()
        preview = client.post("/api/v1/scenario-candidates/preview", json={"selection": selection_for(dimensions), "limit": 10})
        assert preview.status_code == 200
        body = preview.json()
        assert body["persisted"] is False
        assert body["configured_count_changed"] is False
        assert body["valid_candidate_count"] == 1
        assert body["items"][0]["dimensions"] == dimensions
        assert body["items"][0]["acceptance_eligible"] is False
        assert client.get("/api/v1/workspace/counts").json() == before

        candidate = body["items"][0]
        promoted = client.post(f"/api/v1/scenario-candidates/{candidate['candidate_id']}/promote", json={"dimensions": dimensions})
        assert promoted.status_code == 201
        row = promoted.json()
        assert row["state"] == "DRAFT"
        assert row["source"] == "CANDIDATE_PROMOTED"
        assert row["classification"] == dimensions
        assert row["lineage"]["status"] == "PROMOTED_DRAFT_NOT_NETWORK_CONFIGURATION"
        assert client.get("/api/v1/workspace/counts").json()["configured_scenario_count"] == 1
        assert client.get("/api/v1/workspace/counts").json()["executed_scenario_count"] == 0


def test_preview_rejects_incomplete_or_excessive_selection_without_write(tmp_path):
    with client_for(tmp_path) as client:
        missing = client.post("/api/v1/scenario-candidates/preview", json={"selection": {"environment": ["dense_urban"]}})
        assert missing.status_code == 422
        selection = {dimension.key: [option.value for option in dimension.options] for dimension in TAXONOMY.dimensions}
        too_large = client.post("/api/v1/scenario-candidates/preview", json={"selection": selection})
        assert too_large.status_code == 422
        assert client.get("/api/v1/workspace/counts").json()["configured_scenario_count"] == 0


def test_promotion_recomputes_candidate_identity_and_rejects_duplicate(tmp_path):
    dimensions = supported_dimensions()
    with client_for(tmp_path) as client:
        preview = client.post("/api/v1/scenario-candidates/preview", json={"selection": selection_for(dimensions)}).json()
        candidate = preview["items"][0]
        tampered = client.post("/api/v1/scenario-candidates/CAND-TAMPERED/promote", json={"dimensions": dimensions})
        assert tampered.status_code == 422
        first = client.post(f"/api/v1/scenario-candidates/{candidate['candidate_id']}/promote", json={"dimensions": dimensions})
        assert first.status_code == 201
        duplicate = client.post(f"/api/v1/scenario-candidates/{candidate['candidate_id']}/promote", json={"dimensions": dimensions})
        assert duplicate.status_code == 409


def test_coverage_uses_only_saved_non_archived_definitions(tmp_path):
    with client_for(tmp_path) as client:
        created = client.post("/api/v1/workspace/scenarios", json={"name": "Configured", "family": "coverage_structure"}).json()
        coverage = client.get("/api/v1/workspace/coverage").json()
        assert coverage["source"] == "PERSISTED_CONFIGURED_SCENARIOS"
        assert coverage["configured_scenario_count"] == 1
        assert sum(row["configured_count"] for row in coverage["matrix"]) == 0
        client.post(f"/api/v1/workspace/scenarios/{created['scenario_id']}/archive")
        assert client.get("/api/v1/workspace/coverage").json()["configured_scenario_count"] == 0
