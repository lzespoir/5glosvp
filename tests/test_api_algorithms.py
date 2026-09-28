"""Day 7 算法中心 / 算法优化 API 测试（FakeSystemBackend，同步 runner）。"""

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from simulation.backends import default_registry
from system_helpers import TEST_PROTOCOL_ID, make_optimization_service

pytestmark = pytest.mark.unit

API = "/api/v1"
CONTINUOUS = {"parameters": [{"id": "scheduler_beta", "type": "continuous", "lower": 0.05, "upper": 0.99}]}
DISCRETE = {"parameters": [{"id": "scheduler_beta", "type": "discrete", "choices": [0.3, 0.6, 0.99]}]}


@pytest.fixture
def client(tmp_path):
    service = make_optimization_service(tmp_path)
    experiments = ExperimentService(FileExperimentStore(tmp_path / "exp"), default_registry(include_testing=True),
                                    ScenarioCatalog(tmp_path / "configs"))
    app = create_app(experiments, testing=True, system_service=service.experiments,
                     system_optimization_service=service)
    with TestClient(app) as c:
        yield c


def _create(**overrides):
    body = {
        "problem_type": "system", "name": "demo", "scenario_id": "SYSTEM-TEST-001",
        "algorithm_id": "research_demo_optimizer", "algorithm_hyperparameters": {},
        "parameter_space": CONTINUOUS, "evaluation_budget": {"max_evaluations": 6},
        "objective_id": "NETWORK_THROUGHPUT_MAX_V0_1", "benchmark_protocol_id": TEST_PROTOCOL_ID,
    }
    body.update(overrides)
    return body


def _validate(**overrides):
    body = {"problem_type": "system", "scenario_id": "SYSTEM-TEST-001", "objective_id": "NETWORK_THROUGHPUT_MAX_V0_1",
            "parameter_space": CONTINUOUS}
    body.update(overrides)
    return body


def test_list_algorithms(client):
    data = client.get(f"{API}/algorithms").json()
    assert data["sdk_version"] == "0.1"
    assert data["integration_guide"] == "docs/algorithms/how-to-integrate-an-algorithm.md"
    grid, demo = data["items"]
    assert grid["id"] == "grid_search" and grid["category"] == "engineering_baseline"
    assert grid["learning_algorithm"] is False and grid["supported_parameter_types"] == ["discrete"]
    assert grid["notice_zh"] == "Grid Search 为工程基线优化器，不属于项目学习优化算法。"
    assert demo["id"] == "research_demo_optimizer" and demo["category"] == "research_demo"
    assert demo["learning_algorithm"] is False and demo["project_research_deliverable"] is False
    assert demo["supported_parameter_types"] == ["continuous"] and demo["auto_configuration"] is True
    assert demo["capabilities"]["supports_iterative_feedback"] is True
    assert "Not Project Research Deliverable" in demo["labels"]


def test_algorithm_detail(client):
    client.post(f"{API}/system-optimizations", json=_create())
    data = client.get(f"{API}/algorithms/research_demo_optimizer").json()
    meta = data["metadata"]
    assert meta["version"] == "0.1.0" and meta["sdk_version"] == "0.1" and meta["status"] == "experimental"
    assert [h["id"] for h in meta["hyperparameter_schema"]] == ["initial_step", "min_step", "shrink_factor",
                                                                "max_iterations", "start_point"]
    assert data["evidence"]["optimization_runs"] == 1 and data["evidence"]["succeeded_runs"] == 1
    assert data["evidence"]["acceptance_eligible_runs"] == 0
    assert data["notice_zh"].startswith("Research Demo Optimizer 为算法接入验证算法")
    missing = client.get(f"{API}/algorithms/magic_ai")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "ALGORITHM_NOT_FOUND"


def test_validate_algorithm(client):
    ok = client.post(f"{API}/algorithms/research_demo_optimizer/validate", json=_validate()).json()
    assert ok["compatible"] is True and ok["errors"] == [] and ok["resolved_hyperparameters"]["initial_step"] == 0.2
    bad = client.post(f"{API}/algorithms/grid_search/validate", json=_validate()).json()
    assert bad["compatible"] is False
    assert bad["errors"][0]["code"] == "ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED"
    assert "requires discrete candidate values" in bad["errors"][0]["message"]
    grid = client.post(f"{API}/algorithms/grid_search/validate", json=_validate(parameter_space=DISCRETE)).json()
    assert grid["compatible"] is True
    r = client.post(f"{API}/algorithms/research_demo_optimizer/validate", json=_validate(
        parameter_space={"parameters": [{"id": "scheduler_beta", "type": "continuous", "lower": 0.0}]}))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_PARAMETER_SPACE"


def test_create_optimization_with_algorithm(client):
    r = client.post(f"{API}/system-optimizations", json=_create())
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "succeeded" and data["optimizer_id"] == "research_demo_optimizer"
    assert data["algorithm"]["algorithm_category"] == "research_demo"
    assert data["algorithm"]["learning_algorithm"] is False
    assert data["evaluation_budget"]["max_evaluations"] == 6 and data["evaluation_budget"]["evaluations_used"] == 4
    assert data["stop_reason"] == "converged" and data["algorithm_trace"]["rounds"]
    assert data["optimizer_notice_zh"].startswith("Research Demo Optimizer 为算法接入验证算法")
    assert data["evidence_descriptor"]["acceptance_eligible"] is False
    assert data["evidence_descriptor"]["verification_status"] == "platform_checks_passed"
    names = {a["name"] for a in data["artifact_links"]}
    assert {"algorithm-trace.json", "algorithm-metadata.json", "parameter-space.json", "algorithm-config.json",
            "evidence-descriptor.json"} <= names
    evidence = client.get(f"{API}/evidence").json()
    assert evidence["total"] == 1 and evidence["items"][0]["acceptance_eligible"] is False
    assert evidence["items"][0]["verified"] is False


def test_legacy_day6_request_still_supported(client):
    body = {"problem_type": "system", "name": "legacy", "scenario_id": "SYSTEM-TEST-001", "optimizer_id": "grid_search",
            "objective_id": "NETWORK_THROUGHPUT_MAX_V0_1",
            "parameter": {"id": "scheduler_beta", "candidate_values": [0.3, 0.6, 0.99]},
            "benchmark_protocol_id": TEST_PROTOCOL_ID}
    data = client.post(f"{API}/system-optimizations", json=body).json()
    assert data["status"] == "succeeded" and data["candidate_values"] == [0.3, 0.6, 0.99]
    assert data["optimizer_notice_zh"].startswith("Grid Search 为工程基线优化器")
    both = client.post(f"{API}/system-optimizations", json={**body, "parameter_space": DISCRETE})
    assert both.status_code == 422


def test_invalid_algorithm(client):
    r = client.post(f"{API}/system-optimizations", json=_create(algorithm_id="magic_ai"))
    assert r.status_code == 404 and r.json()["error"]["code"] == "ALGORITHM_NOT_FOUND"
    r = client.post(f"{API}/system-optimizations", json=_create(algorithm_id="grid_search"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED"
    assert client.get(f"{API}/system-optimizations").json()["total"] == 0


def test_invalid_hyperparameters(client):
    for hp in ({"initial_step": -1}, {"unknown": 1}, {"max_iterations": "many"}):
        r = client.post(f"{API}/system-optimizations", json=_create(algorithm_hyperparameters=hp))
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_HYPERPARAMETER", hp
        assert r.json()["error"]["detail"]["errors"][0]["code"] == "INVALID_HYPERPARAMETER"


def test_budget_enforced(client):
    for budget in (0, 13):
        r = client.post(f"{API}/system-optimizations", json=_create(evaluation_budget={"max_evaluations": budget}))
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_EVALUATION_BUDGET"
    data = client.post(f"{API}/system-optimizations", json=_create(evaluation_budget={"max_evaluations": 2})).json()
    assert len(data["candidates"]) == 2 and data["stop_reason"] == "budget_exhausted"
    assert data["evaluation_budget"]["evaluations_used"] == 2
