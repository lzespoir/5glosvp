"""
API 单元测试：使用 FakeBackend（软件测试夹具），不依赖 Sionna / GPU。
API unit tests using FakeBackend (software test fixture); no Sionna, no GPU.
"""

import json
import re
import threading
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.app import create_app
from api.settings import DEV_CORS_ORIGINS
from experiments import (
    ExperimentService,
    ExperimentStatus,
    FileExperimentStore,
    ScenarioCatalog,
)
from experiments.errors import ArtifactNotFoundError
from simulation.backends import default_registry
from simulation.base import SimulationBackend
from simulation.fake_backend import FakeBackend
from simulation.registry import BackendDescriptor, BackendRegistry

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_CONFIG = REPO_ROOT / "configs" / "sionna_demo.yaml"


def _write_scenario(configs_dir: Path, scenario_id: str, backend: str) -> None:
    data = yaml.safe_load(DEMO_CONFIG.read_text(encoding="utf-8"))
    data.update(scenario_id=scenario_id, backend=backend, name_en=f"Test {scenario_id}")
    (configs_dir / f"{scenario_id.lower()}.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
    )


class _BlockingBackend(FakeBackend):
    """run() 阻塞直到事件被设置，用于测试超时。"""

    def __init__(self, release: threading.Event) -> None:
        super().__init__()
        self._release = release

    def run(self, experiment_id=None):
        self._release.wait(timeout=10)
        return super().run(experiment_id)


def _make_service(tmp_path: Path, timeout: float = 30.0, extra: list[BackendDescriptor] = ()):
    configs = tmp_path / "configs"
    configs.mkdir()
    _write_scenario(configs, "FAKE-OK-001", "fake")
    _write_scenario(configs, "FAKE-FAIL-001", "fake_failing")
    _write_scenario(configs, "NO-BACKEND-001", "not_registered")
    (configs / "broken.yaml").write_text("scenario_id: [unterminated", encoding="utf-8")

    registry = BackendRegistry()
    registry.register(
        BackendDescriptor("fake", "假后端", "Fake", FakeBackend, ["radio_map"], source_type="test_fixture")
    )
    registry.register(
        BackendDescriptor("fake_failing", "失败假后端", "Failing fake", lambda: FakeBackend(fail_on_run=True))
    )
    for d in extra:
        registry.register(d)
    store = FileExperimentStore(tmp_path / "data" / "experiments")
    service = ExperimentService(store, registry, ScenarioCatalog(configs), timeout_seconds=timeout)
    return service, store


@pytest.fixture
def ctx(tmp_path):
    service, store = _make_service(tmp_path)
    with TestClient(create_app(service, cors_origins=DEV_CORS_ORIGINS)) as client:
        yield client, store


@pytest.fixture
def client(ctx):
    return ctx[0]


def _create(client, scenario_id="FAKE-OK-001", name="单元测试实验"):
    return client.post("/api/v1/experiments", json={"name": name, "scenario_id": scenario_id})


def _assert_error(resp, status, code):
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert body["error"]["code"] == code
    assert body["error"]["message_zh"] and body["error"]["message_en"]
    assert "Traceback" not in resp.text


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok" and body["service"] == "5glosvp" and body["version"] == "0.5.0"
    assert body["name_zh"] and body["name_en"]
    assert body["testing"] is False


def test_health_reports_testing_mode(tmp_path):
    service, _ = _make_service(tmp_path)
    with TestClient(create_app(service, testing=True)) as c:
        assert c.get("/api/v1/health").json()["testing"] is True


def test_list_backends(client):
    items = {b["id"]: b for b in client.get("/api/v1/backends").json()["items"]}
    assert set(items) == {"fake", "fake_failing"}
    assert items["fake"]["available"] is True
    assert items["fake"]["capabilities"] == ["radio_map"]
    assert items["fake"]["source_type"] == "test_fixture"


def test_default_registry_source_types():
    descriptors = {d.id: d for d in default_registry(include_testing=True).list()}
    assert descriptors["sionna_rt"].source_type == "simulation"
    assert descriptors["fake"].source_type == "test_fixture"


def test_unavailable_backend_is_reported_not_raised(tmp_path):
    class _Down(FakeBackend):
        def health_check(self):
            return {"available": False, "version": None, "errors": ["driver missing"], "warnings": []}

    service, _ = _make_service(tmp_path, extra=[BackendDescriptor("down", "不可用", "Down", _Down)])
    with TestClient(create_app(service)) as c:
        items = {b["id"]: b for b in c.get("/api/v1/backends").json()["items"]}
    assert items["down"]["available"] is False and "driver missing" in items["down"]["reason"]


def test_list_scenarios(client):
    items = client.get("/api/v1/scenarios").json()["items"]
    ids = {s["scenario_id"] for s in items}
    assert ids == {"FAKE-OK-001", "FAKE-FAIL-001", "NO-BACKEND-001"}  # broken.yaml 被跳过
    assert all(set(s) == {"scenario_id", "name_zh", "name_en", "backend"} for s in items)


def test_get_scenario(client):
    body = client.get("/api/v1/scenarios/FAKE-OK-001").json()
    assert body["scenario_id"] == "FAKE-OK-001"
    assert body["frequency_hz"] == 3.5e9
    assert body["transmitters"][0]["id"] == "TX-001"
    assert body["radio_map"]["metric"] == "rss"


def test_scenario_not_found(client):
    _assert_error(client.get("/api/v1/scenarios/NOPE"), 404, "SCENARIO_NOT_FOUND")
    _assert_error(_create(client, scenario_id="NOPE"), 404, "SCENARIO_NOT_FOUND")


def test_create_experiment(ctx):
    client, store = ctx
    resp = _create(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert re.fullmatch(r"EXP-[0-9A-F]{8}", body["experiment_id"])
    assert body["status"] == "succeeded"
    assert body["name"] == "单元测试实验"
    assert body["scenario"]["scenario_id"] == "FAKE-OK-001"
    assert body["backend"] == {"id": "fake", "version": "0.0.0-test"}
    assert [t["status"] for t in body["status_history"]] == [
        "created", "queued", "running", "succeeded"
    ]
    rt = body["runtime"]
    assert rt["scenario_load_seconds"] is not None
    assert rt["total_seconds"] >= rt["simulation_seconds"]
    assert rt["total_seconds"] >= rt["artifact_export_seconds"]
    assert body["metrics"]["radio_map"]["num_cells"] == 80
    assert body["provenance"]["source_type"] == "test_fixture"
    assert body["provenance"]["measured"] is False

    exp_dir = store.root / body["experiment_id"]
    assert (exp_dir / "experiment.json").is_file()
    assert (exp_dir / "config.yaml").is_file()
    assert (exp_dir / "artifacts" / "result.json").is_file()
    assert not list(exp_dir.glob("*.tmp"))
    persisted = json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8"))
    assert persisted["status"] == "succeeded"
    assert str(store.root) not in json.dumps(persisted)  # 持久化元数据不含绝对路径


def test_client_cannot_set_experiment_id(client):
    resp = client.post(
        "/api/v1/experiments",
        json={"name": "x", "scenario_id": "FAKE-OK-001", "experiment_id": "EXP-00000000"},
    )
    _assert_error(resp, 422, "INVALID_REQUEST")


@pytest.mark.parametrize("body", [{}, {"name": "", "scenario_id": "FAKE-OK-001"}, {"name": "x"}])
def test_invalid_request(client, body):
    _assert_error(client.post("/api/v1/experiments", json=body), 422, "INVALID_REQUEST")


def test_backend_unavailable_on_create(client):
    _assert_error(_create(client, scenario_id="NO-BACKEND-001"), 503, "BACKEND_UNAVAILABLE")


def test_get_experiment(client):
    created = _create(client).json()
    resp = client.get(f"/api/v1/experiments/{created['experiment_id']}")
    assert resp.status_code == 200
    assert resp.json() == created


@pytest.mark.parametrize("experiment_id", ["EXP-DEADBEEF", "nope", "...", "EXP-deadbeef"])
def test_experiment_not_found(client, experiment_id):
    _assert_error(client.get(f"/api/v1/experiments/{experiment_id}"), 404, "EXPERIMENT_NOT_FOUND")


def test_list_experiments(client):
    ids = [_create(client, name=f"exp {i}").json()["experiment_id"] for i in range(3)]
    body = client.get("/api/v1/experiments?limit=2&offset=0").json()
    assert body["total"] == 3 and body["limit"] == 2 and body["offset"] == 0
    assert [e["experiment_id"] for e in body["items"]] == ids[::-1][:2]  # created_at DESC
    rest = client.get("/api/v1/experiments?limit=2&offset=2").json()
    assert [e["experiment_id"] for e in rest["items"]] == [ids[0]]
    _assert_error(client.get("/api/v1/experiments?limit=0"), 422, "INVALID_REQUEST")


def test_artifact_listing(client):
    exp_id = _create(client).json()["experiment_id"]
    items = {a["name"]: a for a in client.get(f"/api/v1/experiments/{exp_id}/artifacts").json()["items"]}
    assert {"result.json", "metadata.json", "radio_map.png", "radio_map.npz", "config.yaml", "run.log"} <= set(items)
    png = items["radio_map.png"]
    assert png["type"] == "image" and png["media_type"] == "image/png"
    assert png["url"] == f"/api/v1/experiments/{exp_id}/artifacts/radio_map.png"

    resp = client.get(png["url"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"

    result = client.get(items["result.json"]["url"])
    assert result.status_code == 200 and result.json()["experiment_id"] == exp_id
    npz = client.get(items["radio_map.npz"]["url"])
    assert npz.status_code == 200 and "attachment" in npz.headers["content-disposition"]


def test_artifact_not_found(client):
    exp_id = _create(client).json()["experiment_id"]
    _assert_error(client.get(f"/api/v1/experiments/{exp_id}/artifacts/missing.png"), 404, "ARTIFACT_NOT_FOUND")
    _assert_error(client.get("/api/v1/experiments/EXP-DEADBEEF/artifacts"), 404, "EXPERIMENT_NOT_FOUND")


@pytest.mark.parametrize(
    "name",
    [
        "../experiment.json",
        "../../../../etc/passwd",
        "..%2F..%2Fexperiment.json",
        "%2e%2e/%2e%2e/etc/passwd",
        "/etc/passwd",
        "artifacts/../../experiment.json",
    ],
)
def test_path_traversal_rejected(client, name):
    exp_id = _create(client).json()["experiment_id"]
    resp = client.get(f"/api/v1/experiments/{exp_id}/artifacts/{name}")
    assert resp.status_code == 404
    assert "root:" not in resp.text and '"experiment_id"' not in resp.text


@pytest.mark.parametrize("name", ["../experiment.json", "../../etc/passwd", "/etc/passwd", ".", ""])
def test_store_resolver_blocks_traversal(ctx, name):
    client, store = ctx
    exp_id = _create(client).json()["experiment_id"]
    with pytest.raises(ArtifactNotFoundError):
        store.resolve_artifact(exp_id, name)


def test_failed_simulation_sets_failed_status(ctx):
    client, store = ctx
    resp = _create(client, scenario_id="FAKE-FAIL-001")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "SIMULATION_FAILED"
    assert body["error"]["type"] == "SimulationRunError"
    assert "Traceback" not in json.dumps(body)
    assert body["status_history"][-1]["status"] == "failed"
    assert body["provenance"] is None
    assert [a["name"] for a in body["artifacts"]] == ["run.log"]

    persisted = store.get(body["experiment_id"])
    assert persisted.status is ExperimentStatus.FAILED and persisted.finished_at


def test_timeout_marks_failed(tmp_path):
    release = threading.Event()
    service, store = _make_service(
        tmp_path, timeout=0.2,
        extra=[BackendDescriptor("blocking", "阻塞", "Blocking", lambda: _BlockingBackend(release))],
    )
    _write_scenario(tmp_path / "configs", "BLOCK-001", "blocking")
    try:
        record = service.create_experiment("timeout", "BLOCK-001")
        assert record.status is ExperimentStatus.FAILED
        assert record.error.code.value == "SIMULATION_TIMEOUT"
    finally:
        release.set()
        service.close()
    # 工作线程之后完成也不能覆盖 FAILED 状态
    service._executor.shutdown(wait=True)
    assert store.get(record.experiment_id).status is ExperimentStatus.FAILED


def test_unknown_route_uses_error_model(client):
    _assert_error(client.get("/api/v1/nope"), 404, "NOT_FOUND")


def test_cors_allows_dev_frontend_only(client):
    ok = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/v1/health", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in bad.headers


def test_openapi_available(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for p in [
        "/api/v1/health", "/api/v1/backends", "/api/v1/scenarios", "/api/v1/scenarios/{scenario_id}",
        "/api/v1/experiments", "/api/v1/experiments/{experiment_id}",
        "/api/v1/experiments/{experiment_id}/artifacts",
        "/api/v1/experiments/{experiment_id}/artifacts/{artifact_name}",
    ]:
        assert p in paths, p


def test_fake_backend_hidden_unless_testing():
    assert "fake" not in default_registry().ids()
    assert "fake" in default_registry(include_testing=True).ids()


def test_api_layer_does_not_import_simulation_engines():
    """架构约束：API / 实验服务层不得直接依赖 Sionna 或具体后端。"""
    pattern = re.compile(r"^\s*(from|import)\s+(sionna|mitsuba|drjit|simulation\.backends)\b", re.M)
    allowed = {REPO_ROOT / "src" / "api" / "main.py"}  # 唯一的装配入口
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for d in ("src/api", "src/experiments")
        for p in (REPO_ROOT / d).rglob("*.py")
        if p not in allowed and pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


def test_backend_interface_unchanged():
    assert {"name", "health_check", "load_scenario", "run", "export"} <= set(
        SimulationBackend.__abstractmethods__
    )
