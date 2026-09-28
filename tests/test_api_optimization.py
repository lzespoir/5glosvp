"""
优化 API 单元测试：FakeBackend（软件测试夹具），不依赖 Sionna / GPU。
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.app import create_app
from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from optimization import (
    FileOptimizationStore,
    OptimizationService,
    default_objective_registry,
    default_optimizer_registry,
)
from simulation.fake_backend import FakeBackend
from simulation.registry import BackendDescriptor, BackendRegistry

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_CONFIG = REPO_ROOT / "configs" / "sionna_demo.yaml"
OPT = "/api/v1/optimizations"


def _write_scenario(configs: Path, scenario_id: str, backend: str) -> None:
    data = yaml.safe_load(DEMO_CONFIG.read_text(encoding="utf-8"))
    data.update(scenario_id=scenario_id, backend=backend)
    (configs / f"{scenario_id.lower()}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


@pytest.fixture
def client(tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    _write_scenario(configs, "FAKE-OK-001", "fake")
    _write_scenario(configs, "FAKE-FAIL-001", "fake_failing")
    registry = BackendRegistry()
    registry.register(BackendDescriptor("fake", "假后端", "Fake", FakeBackend, source_type="test_fixture"))
    registry.register(
        BackendDescriptor("fake_failing", "失败", "Failing", lambda: FakeBackend(fail_on_run=True), source_type="test_fixture")
    )
    experiments = ExperimentService(FileExperimentStore(tmp_path / "experiments"), registry, ScenarioCatalog(configs))
    optimizations = OptimizationService(
        experiments, FileOptimizationStore(tmp_path / "optimizations"),
        default_optimizer_registry(), default_objective_registry(),
    )
    with TestClient(create_app(experiments, optimization_service=optimizations)) as c:
        yield c


def _body(**overrides):
    body = {
        "name": "TX Power Grid Search",
        "scenario_id": "FAKE-OK-001",
        "optimizer_id": "grid_search",
        "objective_id": "PROPAGATION_UTILITY_V0_1",
        "parameter_space": {"tx_power_dbm": [38, 40, 42, 44, 46]},
    }
    body.update(overrides)
    return body


def _create(client, **overrides):
    return client.post(OPT, json=_body(**overrides))


def _assert_error(resp, status, code):
    assert resp.status_code == status, resp.text
    err = resp.json()["error"]
    assert err["code"] == code and err["message_zh"] and err["message_en"]
    assert "Traceback" not in resp.text


def test_list_optimizers(client):
    items = client.get("/api/v1/optimizers").json()["items"]
    assert len(items) == 1
    gs = items[0]
    assert gs["id"] == "grid_search" and gs["name_zh"] == "网格搜索" and gs["name_en"] == "Grid Search"
    assert gs["category"] == "engineering_baseline" and gs["learning_algorithm"] is False
    assert gs["available"] is True and gs["max_candidates"] == 10
    assert gs["recommended_parameter_space"] == {"tx_power_dbm": [38.0, 40.0, 42.0, 44.0, 46.0]}
    assert "Assumption" in gs["recommended_parameter_space_source"]
    assert gs["supported_parameters"] == [{"id": "tx_power_dbm", "name_zh": "发射功率", "name_en": "TX Power", "unit": "dBm"}]


def test_list_objectives(client):
    items = client.get("/api/v1/objectives").json()["items"]
    assert [o["id"] for o in items] == ["PROPAGATION_UTILITY_V0_1"]
    obj = items[0]
    assert obj["version"] == "0.1" and obj["direction"] == "maximize"
    assert obj["required_metrics"] == ["sinr"] and obj["default_params"] == {"lambda_power": 0.1}
    assert "[A]" in obj["assumptions"]["lambda_power"] and obj["formula"]


def test_create_optimization(client):
    resp = _create(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["optimizer"]["learning_algorithm"] is False and body["optimizer"]["name_en"] == "Grid Search"
    assert body["objective"]["id"] == "PROPAGATION_UTILITY_V0_1" and body["objective"]["params"] == {"lambda_power": 0.1}
    assert body["baseline"]["is_baseline"] is True and body["baseline"]["candidate_id"] == "BASELINE"
    assert len(body["candidates"]) == 5
    assert sum(c["reused_baseline"] for c in body["candidates"]) == 1
    best = body["best_candidate"]
    assert best["candidate_id"] == body["comparison"]["optimized_candidate_id"]
    assert body["comparison"]["baseline_experiment_id"] == body["baseline"]["experiment_id"]
    assert body["improvement_status"] in {"improved", "no_improvement", "worse"}
    assert body["provenance"]["source_type"] == "test_fixture"

    # 每个候选都可追溯到真实实验记录
    for c in body["candidates"]:
        exp = client.get(f"/api/v1/experiments/{c['experiment_id']}").json()
        assert exp["optimization_id"] == body["optimization_id"]
        assert exp["purpose"] in {"optimization_baseline", "optimization_candidate"}


def test_objective_params_override_and_validation(client):
    body = _create(client, objective_params={"lambda_power": 0.0}, parameter_space={"tx_power_dbm": [38, 46]}).json()
    assert body["objective"]["params"] == {"lambda_power": 0.0}
    _assert_error(_create(client, objective_params={"lambda_power": -1}), 422, "INVALID_REQUEST")
    _assert_error(_create(client, objective_params={"threshold": 3}), 422, "INVALID_REQUEST")


def test_get_optimization(client):
    created = _create(client).json()
    resp = client.get(f"{OPT}/{created['optimization_id']}")
    assert resp.status_code == 200 and resp.json() == created


def test_list_optimizations(client):
    ids = [_create(client, name=f"run {i}", parameter_space={"tx_power_dbm": [40]}).json()["optimization_id"] for i in range(3)]
    body = client.get(f"{OPT}?limit=2&offset=0").json()
    assert body["total"] == 3 and [o["optimization_id"] for o in body["items"]] == ids[::-1][:2]
    rest = client.get(f"{OPT}?limit=2&offset=2").json()
    assert [o["optimization_id"] for o in rest["items"]] == [ids[0]]


@pytest.mark.parametrize("optimization_id", ["OPT-DEADBEEF", "nope", "OPT-deadbeef"])
def test_optimization_not_found(client, optimization_id):
    _assert_error(client.get(f"{OPT}/{optimization_id}"), 404, "OPTIMIZATION_NOT_FOUND")


def test_invalid_optimizer(client):
    _assert_error(_create(client, optimizer_id="deep_rl"), 404, "OPTIMIZER_NOT_FOUND")


def test_invalid_objective(client):
    _assert_error(_create(client, objective_id="MAX_RSS"), 404, "OBJECTIVE_NOT_FOUND")


def test_invalid_scenario(client):
    _assert_error(_create(client, scenario_id="NOPE"), 404, "SCENARIO_NOT_FOUND")


def test_too_many_candidates(client):
    resp = _create(client, parameter_space={"tx_power_dbm": list(range(20, 31))})
    _assert_error(resp, 422, "INVALID_PARAMETER_SPACE")
    assert client.get(OPT).json()["total"] == 0


@pytest.mark.parametrize(
    "space", [{"tx_power_dbm": []}, {"tx_power_dbm": [40, 40]}, {"tx_power_dbm": [40], "tilt": [1]}, {}]
)
def test_invalid_parameter_space_shape(client, space):
    _assert_error(_create(client, parameter_space=space), 422, "INVALID_REQUEST")


def test_client_cannot_set_optimization_id(client):
    _assert_error(_create(client, optimization_id="OPT-00000000"), 422, "INVALID_REQUEST")


def test_failed_optimization(client):
    resp = _create(client, scenario_id="FAKE-FAIL-001")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "OPTIMIZATION_FAILED" and body["error"]["failed_candidate_id"] == "BASELINE"
    assert body["baseline"]["status"] == "failed" and body["baseline"]["experiment_id"]
    assert body["comparison"] is None and body["improvement_status"] is None
    assert "Traceback" not in resp.text
    assert client.get(f"{OPT}/{body['optimization_id']}").json()["status"] == "failed"


def test_openapi_lists_optimization_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/api/v1/optimizers", "/api/v1/objectives", "/api/v1/optimizations", "/api/v1/optimizations/{optimization_id}"]:
        assert p in paths, p
