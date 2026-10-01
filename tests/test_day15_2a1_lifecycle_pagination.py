from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.scenario_candidates import router as candidate_router
from api.routes.workspace import router as workspace_router
from scenarios import candidates as candidate_module
from scenarios.candidates import ScenarioCandidateService
from scenarios.taxonomy import TAXONOMY
from workspace.service import WorkspaceService


pytestmark = pytest.mark.unit


def client_for(tmp_path):
    app = FastAPI()
    app.state.workspace_service = WorkspaceService(tmp_path)
    app.include_router(candidate_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")
    return TestClient(app), app.state.workspace_service


def test_catalog_pages_counts_and_coverage_exclude_archived(tmp_path):
    client, service = client_for(tmp_path)
    with client:
        scenarios = [service.create(f"Scenario {index:02d}") for index in range(53)]
        for scenario in scenarios[:3]:
            client.post(f"/api/v1/workspace/scenarios/{scenario.scenario_id}/archive")

        active = client.get("/api/v1/workspace/scenarios?offset=0&limit=20").json()
        archived = client.get("/api/v1/workspace/scenarios?state=ARCHIVED&offset=0&limit=20").json()
        counts = client.get("/api/v1/workspace/counts").json()
        coverage = client.get("/api/v1/workspace/coverage").json()
        assert active["total"] == 50
        assert archived["total"] == 3
        assert counts["configured_scenario_count"] == coverage["configured_scenario_count"] == 50

        pages = [client.get(f"/api/v1/workspace/scenarios?offset={offset}&limit=20").json()["items"] for offset in (0, 20, 40)]
        ids = [row["scenario_id"] for page in pages for row in page]
        assert [len(page) for page in pages] == [20, 20, 10]
        assert len(ids) == len(set(ids)) == 50
        assert set(ids).isdisjoint({row["scenario_id"] for row in archived["items"]})


def test_archive_restore_returns_previous_state_with_provenance(tmp_path):
    client, service = client_for(tmp_path)
    with client:
        scenario = service.create("Preserve status")
        scenario.state = "VALID"
        service.store.write("scenarios", scenario.scenario_id, scenario.model_dump(mode="json"))
        archived = client.post(f"/api/v1/workspace/scenarios/{scenario.scenario_id}/archive").json()
        assert archived["state"] == "ARCHIVED"
        assert archived["pre_archive_state"] == "VALID"
        assert archived["archived_at"] and archived["archived_source"] == "API"
        assert client.get("/api/v1/workspace/scenarios").json()["total"] == 0

        restored_response = client.post(f"/api/v1/workspace/scenarios/{scenario.scenario_id}/restore")
        assert restored_response.status_code == 200
        restored = restored_response.json()
        assert restored["state"] == "VALID"
        assert restored["restored_at"] and restored["restored_source"] == "API"
        assert client.get("/api/v1/workspace/scenarios").json()["total"] == 1


def test_safe_delete_and_reference_guard_never_cascade(tmp_path):
    client, service = client_for(tmp_path)
    with client:
        removable = service.create("Unreferenced draft")
        deleted = client.delete(f"/api/v1/workspace/scenarios/{removable.scenario_id}")
        assert deleted.status_code == 200
        assert deleted.json()["cascade_deleted"] is False
        assert client.get(f"/api/v1/workspace/scenarios/{removable.scenario_id}").status_code == 404

        referenced = service.create("Referenced draft")
        instance_id = "SCI-FIXTURE"
        service.store.write("instances", instance_id, {"instance_id": instance_id, "scenario_id": referenced.scenario_id})
        refused = client.delete(f"/api/v1/workspace/scenarios/{referenced.scenario_id}")
        assert refused.status_code == 409
        detail = refused.json()["detail"]
        assert detail["code"] == "SCENARIO_REFERENCED"
        assert detail["reference_summary"]["scenario_instances"] == 1
        assert service.get(referenced.scenario_id).scenario_id == referenced.scenario_id
        assert service.store.read("instances", instance_id)["scenario_id"] == referenced.scenario_id


def test_valid_scenario_must_be_archived_before_delete(tmp_path):
    client, service = client_for(tmp_path)
    with client:
        scenario = service.create("Valid scenario")
        scenario.state = "VALID"
        service.store.write("scenarios", scenario.scenario_id, scenario.model_dump(mode="json"))
        response = client.delete(f"/api/v1/workspace/scenarios/{scenario.scenario_id}")
        assert response.status_code == 409
        assert response.json()["detail"] == "SCENARIO_MUST_BE_ARCHIVED"
        assert service.get(scenario.scenario_id).state == "VALID"


def test_delete_archived_definition_does_not_change_active_coverage(tmp_path):
    client, service = client_for(tmp_path)
    with client:
        scenario = service.create("Archived cleanup")
        client.post(f"/api/v1/workspace/scenarios/{scenario.scenario_id}/archive")
        before_counts = client.get("/api/v1/workspace/counts").json()
        before_coverage = client.get("/api/v1/workspace/coverage").json()
        response = client.delete(f"/api/v1/workspace/scenarios/{scenario.scenario_id}")
        assert response.status_code == 200
        assert client.get("/api/v1/workspace/counts").json() == before_counts
        assert client.get("/api/v1/workspace/coverage").json() == before_coverage


def test_candidate_327_items_paginate_without_overlap_or_missing(monkeypatch):
    options = [SimpleNamespace(value=f"v{index:03d}") for index in range(327)]
    dimension = SimpleNamespace(key="synthetic", options=options)
    monkeypatch.setattr(candidate_module, "DIMENSION_KEYS", ("synthetic",))
    monkeypatch.setattr(candidate_module, "TAXONOMY", SimpleNamespace(dimensions=[dimension], taxonomy_version="fixture-1"))

    def fake_candidate(dimensions):
        value = dimensions["synthetic"]
        return SimpleNamespace(
            scenario_definition_hash=value,
            compatibility_status="VALID_EXECUTABLE",
            taxonomy_version="fixture-1",
            name_zh=value,
            name_en=value,
            scenario_family="fixture",
            support_status="SUPPORTED",
            supported_problem_types=["NETWORK_STRUCTURE"],
        )

    monkeypatch.setattr(candidate_module, "scenario_from_dimensions", fake_candidate)
    service = ScenarioCandidateService()
    selection = {"synthetic": [option.value for option in options]}
    first = service.preview(selection, limit=20)
    ids = [item.candidate_id for item in first.items]
    for offset in range(20, first.total, 20):
        page = service.preview(selection, limit=20, offset=offset, query_hash=first.query_hash)
        ids.extend(item.candidate_id for item in page.items)

    assert first.total == first.valid_candidate_count == 327
    assert [len(ids[index:index + 20]) for index in range(0, len(ids), 20)] == [20] * 16 + [7]
    assert len(ids) == len(set(ids)) == 327
    assert service.preview(selection, limit=20).items[0].candidate_id == first.items[0].candidate_id
    beyond = service.preview(selection, limit=20, offset=1000)
    assert beyond.items == [] and beyond.total == 327

    filtered = service.preview(selection, limit=20, filters={"synthetic": [f"v{index:03d}" for index in range(83)]})
    filtered_ids = [item.candidate_id for item in filtered.items]
    for offset in range(20, filtered.total, 20):
        filtered_ids.extend(item.candidate_id for item in service.preview(selection, limit=20, offset=offset, filters={"synthetic": [f"v{index:03d}" for index in range(83)]}, query_hash=filtered.query_hash).items)
    assert filtered.total == 83
    assert len(filtered_ids) == len(set(filtered_ids)) == 83


def test_candidate_invalid_pagination_and_stale_query_are_rejected():
    dimensions = {item.key: [item.options[0].value] for item in TAXONOMY.dimensions}
    service = ScenarioCandidateService()
    with pytest.raises(ValueError, match="CANDIDATE_PAGE_LIMIT_INVALID"):
        service.preview(dimensions, limit=101)
    with pytest.raises(ValueError, match="CANDIDATE_OFFSET_INVALID"):
        service.preview(dimensions, offset=-1)
    first = service.preview(dimensions)
    with pytest.raises(ValueError, match="CANDIDATE_QUERY_STALE"):
        service.preview(dimensions, filters={"environment": dimensions["environment"][0]}, query_hash=first.query_hash)
