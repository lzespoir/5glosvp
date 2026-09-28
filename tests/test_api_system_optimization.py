"""系统级优化 API 测试（FakeSystemBackend，同步 runner）/ System optimization API tests."""

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from simulation.backends import default_registry
from system_simulation import Capability
from system_helpers import TEST_PROTOCOL_ID, fake_registry, make_optimization_service

pytestmark = pytest.mark.unit

API = "/api/v1"


def _client(tmp_path, registry=None):
    service = make_optimization_service(tmp_path, registry=registry)
    experiments = ExperimentService(FileExperimentStore(tmp_path / "exp"), default_registry(include_testing=True),
                                    ScenarioCatalog(tmp_path / "configs"))
    app = create_app(experiments, testing=True, system_service=service.experiments,
                     system_optimization_service=service)
    return TestClient(app)


@pytest.fixture
def client(tmp_path):
    with _client(tmp_path) as c:
        yield c


def _body(**overrides):
    body = {
        "problem_type": "system", "name": "api", "scenario_id": "SYSTEM-TEST-001", "optimizer_id": "grid_search",
        "objective_id": "NETWORK_THROUGHPUT_MAX_V0_1",
        "parameter": {"id": "scheduler_beta", "candidate_values": [0.3, 0.6, 0.99]},
        "benchmark_protocol_id": TEST_PROTOCOL_ID,
    }
    body.update(overrides)
    return body


def test_catalog_endpoints(client):
    optimizers = client.get(f"{API}/system-optimizers").json()["items"]
    assert [o["id"] for o in optimizers] == ["grid_search"]
    assert optimizers[0]["learning_algorithm"] is False and optimizers[0]["category"] == "engineering_baseline"
    assert optimizers[0]["hyperparameters"] == []
    objectives = client.get(f"{API}/system-objectives").json()["items"]
    assert objectives[0]["id"] == "NETWORK_THROUGHPUT_MAX_V0_1" and objectives[0]["acceptance_kpi"] is False
    params = client.get(f"{API}/system-parameters").json()["items"]
    beta = params[0]["definition"]
    assert beta["id"] == "scheduler_beta" and beta["role"] == "optimization_variable"
    assert beta["bounds"] == {"lower": 0.0, "upper": 1.0, "lower_inclusive": False, "upper_inclusive": False}
    assert params[0]["affects_propagation"] is False
    protocols = client.get(f"{API}/benchmark-protocols").json()["items"]
    assert protocols[0]["protocol_id"] == TEST_PROTOCOL_ID


def test_create_system_optimization(client):
    r = client.post(f"{API}/system-optimizations", json=_body())
    assert r.status_code == 202
    data = r.json()
    assert data["problem_type"] == "system" and data["status"] == "succeeded"
    assert data["best_candidate_id"] == "CAND-003"
    assert data["fairness"]["fair"] is True
    assert data["scientific_boundary_zh"] == "当前结果来自系统级仿真优化验证，不是华为实测网络优化结果。"
    assert data["optimizer_notice_zh"].startswith("Grid Search 为工程基线优化器")
    assert {a["name"] for a in data["artifact_links"]} >= {"comparison.png", "per-ue-comparison.png"}
    png = client.get(next(a["url"] for a in data["artifact_links"] if a["name"] == "comparison.png"))
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"


def test_get_system_optimization(client):
    opt_id = client.post(f"{API}/system-optimizations", json=_body()).json()["optimization_id"]
    data = client.get(f"{API}/system-optimizations/{opt_id}").json()
    assert data["optimization_id"] == opt_id
    assert data["evaluation_context"]["channel_realization"]["channel_realization_id"].startswith("CH-")
    exp_id = data["candidates"][0]["experiment_id"]
    exp = client.get(f"{API}/system-experiments/{exp_id}").json()
    assert exp["optimization_id"] == opt_id and exp["purpose"] == "optimization_candidate"
    assert exp["evaluation_context"]["evaluation_context_id"] == data["evaluation_context"]["context_id"]
    missing = client.get(f"{API}/system-optimizations/OPT-00000000")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "SYSTEM_OPTIMIZATION_NOT_FOUND"
    bad = client.get(f"{API}/system-optimizations/{opt_id}/artifacts/..%2Foptimization.json")
    assert bad.status_code == 404


def test_list_system_optimizations(client):
    client.post(f"{API}/system-optimizations", json=_body())
    client.post(f"{API}/system-optimizations", json=_body(name="second"))
    data = client.get(f"{API}/system-optimizations").json()
    assert data["total"] == 2 and [i["name"] for i in data["items"]] == ["second", "api"]


def test_invalid_objective(client):
    r = client.post(f"{API}/system-optimizations", json=_body(objective_id="PROPAGATION_UTILITY_V0_1"))
    assert r.status_code == 404 and r.json()["error"]["code"] == "OBJECTIVE_NOT_FOUND"


def test_invalid_parameter(client):
    for parameter in ({"id": "scheduler_beta", "candidate_values": [0.0]},
                      {"id": "scheduler_beta", "candidate_values": [1.2]},
                      {"id": "tx_power_dbm", "candidate_values": [40.0]}):
        r = client.post(f"{API}/system-optimizations", json=_body(parameter=parameter))
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_PARAMETER_SPACE"
    r = client.post(f"{API}/system-optimizations", json=_body(parameter={"id": "scheduler_beta",
                                                                          "candidate_values": []}))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_REQUEST"
    r = client.post(f"{API}/system-optimizations", json=_body(benchmark_protocol_id="NOPE"))
    assert r.status_code == 404 and r.json()["error"]["code"] == "BENCHMARK_PROTOCOL_NOT_FOUND"
    r = client.post(f"{API}/system-optimizations", json=_body(problem_type="propagation"))
    assert r.status_code == 422


def test_backend_missing_capability(tmp_path):
    registry = fake_registry(capabilities=(Capability.SYSTEM_SIMULATION, Capability.THROUGHPUT))
    with _client(tmp_path, registry) as c:
        r = c.post(f"{API}/system-optimizations", json=_body())
    assert r.status_code == 422 and r.json()["error"]["code"] == "SYSTEM_CAPABILITY_NOT_SUPPORTED"


def test_failed_baseline(tmp_path):
    with _client(tmp_path, fake_registry(fail_beta=0.9)) as c:
        data = c.post(f"{API}/system-optimizations", json=_body()).json()
    assert data["status"] == "failed" and data["error"]["code"] == "BASELINE_FAILED"
    assert data["baseline"]["status"] == "failed"


def test_failed_candidate_preserved(tmp_path):
    with _client(tmp_path, fake_registry(fail_beta=0.6)) as c:
        data = c.post(f"{API}/system-optimizations", json=_body()).json()
    assert data["status"] == "succeeded"
    failed = [x for x in data["candidates"] if x["status"] == "failed"]
    assert [x["parameters"]["scheduler_beta"] for x in failed] == [0.6]
    assert failed[0]["error"]["code"] == "SYSTEM_SIMULATION_FAILED" and failed[0]["experiment_id"]
