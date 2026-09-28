"""系统级仿真 API 测试（FakeSystemBackend）/ System simulation API tests."""

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from evaluation.kpi import default_kpi_registry
from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from simulation.backends import default_registry
from system_simulation import FileSystemExperimentStore, SystemExperimentService, SystemScenarioCatalog
from test_system_backends import _registry
from system_helpers import write_scenario

pytestmark = pytest.mark.unit

API = "/api/v1"


@pytest.fixture
def client(tmp_path):
    write_scenario(tmp_path / "configs" / "system")
    write_scenario(tmp_path / "configs" / "system", scenario_id="SYSTEM-TEST-SIONNA", backend="sionna_system")
    experiments = ExperimentService(FileExperimentStore(tmp_path / "exp"), default_registry(include_testing=True),
                                    ScenarioCatalog(tmp_path / "configs"))
    system = SystemExperimentService(FileSystemExperimentStore(tmp_path / "sys"), _registry(),
                                     SystemScenarioCatalog(tmp_path / "configs" / "system"), default_kpi_registry(),
                                     "0.3.0", "abc")
    with TestClient(create_app(experiments, testing=True, system_service=system)) as c:
        yield c


def _create(client, backend_id="fake_system", scenario_id="SYSTEM-TEST-001"):
    return client.post(f"{API}/system-experiments",
                       json={"name": "api test", "scenario_id": scenario_id, "backend_id": backend_id})


def test_list_system_backends(client):
    items = {b["id"]: b for b in client.get(f"{API}/system-backends").json()["items"]}
    fake = items["fake_system"]
    assert fake["category"] == "system" and fake["source_type"] == "test_fixture"
    assert fake["model_type"] == "test_fixture" and "throughput" in fake["capabilities"]
    assert items["sionna_system"]["model_label"] == "Sionna Simulation Generated"
    only = client.get(f"{API}/system-backends", params={"capability": "radio_map"}).json()["items"]
    assert [b["id"] for b in only] == ["radio_only"]
    assert client.get(f"{API}/system-backends", params={"capability": "bogus"}).status_code == 422


def test_list_system_scenarios(client):
    items = client.get(f"{API}/system-scenarios").json()["items"]
    s = next(i for i in items if i["scenario_id"] == "SYSTEM-TEST-001")
    assert s["bs_count"] == 1 and s["cell_count"] == 1 and s["ue_count"] == 4
    assert s["traffic_model"] == "full_buffer" and s["ue_placement"] == "generator:uniform_area_with_path"
    detail = client.get(f"{API}/system-scenarios/SYSTEM-TEST-001").json()
    assert detail["scenario"]["cells"][0]["cell_id"] == "CELL-001"
    assert client.get(f"{API}/system-scenarios/NOPE").json()["error"]["code"] == "SYSTEM_SCENARIO_NOT_FOUND"


def test_list_kpis(client):
    items = client.get(f"{API}/kpis").json()["items"]
    assert [k["id"] for k in items] == ["UE_THROUGHPUT_V0_1", "NETWORK_THROUGHPUT_V0_1", "AVG_UE_THROUGHPUT_V0_1",
                                        "P5_UE_THROUGHPUT_V0_1"]
    assert all(k["acceptance_kpi"] is False for k in items)


def test_create_system_experiment(client):
    resp = _create(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "succeeded" and body["experiment_type"] == "system"
    assert body["backend"] == {"id": "fake_system", "version": "fixture", "model_type": "test_fixture",
                               "model_label": "TEST FIXTURE", "source_type": "test_fixture"}
    assert body["scientific_boundary_zh"] == "当前结果来自系统级仿真，不是华为实测网络数据。"
    kpis = {k["metric_id"]: k for k in body["kpis"]}
    ues = body["result"]["ue_results"]
    assert kpis["NETWORK_THROUGHPUT_V0_1"]["value"] == pytest.approx(sum(u["throughput_mbps"] for u in ues))
    assert kpis["NETWORK_THROUGHPUT_V0_1"]["source_experiment"] == body["experiment_id"]
    assert body["provenance"]["measured"] is False and body["provenance"]["acceptance_evidence"] is False
    art = next(a for a in body["artifacts"] if a["name"] == "kpi.json")
    assert client.get(art["url"]).json()[1]["metric_id"] == "NETWORK_THROUGHPUT_V0_1"
    png = client.get(f"{API}/system-experiments/{body['experiment_id']}/artifacts/system_summary.png")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"


def test_get_system_experiment(client):
    exp_id = _create(client).json()["experiment_id"]
    body = client.get(f"{API}/system-experiments/{exp_id}").json()
    assert body["experiment_id"] == exp_id and len(body["result"]["ue_results"]) == 4


def test_list_system_experiments(client):
    ids = [_create(client).json()["experiment_id"] for _ in range(2)]
    body = client.get(f"{API}/system-experiments", params={"limit": 1}).json()
    assert body["total"] == 2 and len(body["items"]) == 1 and body["items"][0]["experiment_id"] == ids[-1]


def test_system_experiment_not_found(client):
    for exp_id in ("EXP-DEADBEEF", "not-an-id"):
        resp = client.get(f"{API}/system-experiments/{exp_id}")
        assert resp.status_code == 404 and resp.json()["error"]["code"] == "SYSTEM_EXPERIMENT_NOT_FOUND"
    exp_id = _create(client).json()["experiment_id"]
    for name in ("nope.json", "..%2Fsystem_experiment.json"):
        resp = client.get(f"{API}/system-experiments/{exp_id}/artifacts/{name}")
        assert resp.status_code == 404


def test_invalid_system_backend(client):
    resp = _create(client, backend_id="ns3")
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "SYSTEM_BACKEND_NOT_FOUND"


def test_backend_without_system_capability(client):
    resp = _create(client, backend_id="radio_only")
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "SYSTEM_CAPABILITY_NOT_SUPPORTED"


def test_failed_system_experiment_persisted(client):
    resp = _create(client, backend_id="crash")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed" and body["error"]["code"] == "SYSTEM_SIMULATION_FAILED"
    again = client.get(f"{API}/system-experiments/{body['experiment_id']}").json()
    assert again["status"] == "failed" and again["kpis"] == []


def test_invalid_request(client):
    resp = client.post(f"{API}/system-experiments", json={"name": "", "scenario_id": "x"})
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "INVALID_REQUEST"


def test_propagation_routes_unaffected(client):
    assert client.get(f"{API}/health").json()["version"] == "0.4.0"
    assert client.get(f"{API}/experiments").status_code == 200
