"""系统级后端接口、注册表与服务测试 / System backend interface, registry and service tests."""

import json
import logging
import re
from pathlib import Path

import numpy as np
import pytest

from evaluation.kpi import NETWORK_THROUGHPUT_V0_1, UE_THROUGHPUT_V0_1, default_kpi_registry
from simulation.backends.system import default_system_registry
from system_simulation import (
    Capability,
    FakeSystemBackend,
    FileSystemExperimentStore,
    ModelType,
    SystemBackendDescriptor,
    SystemBackendNotFoundError,
    SystemBackendRegistry,
    SystemCapabilityNotSupportedError,
    SystemExperimentService,
    SystemExperimentStatus,
    SystemScenarioCatalog,
    SystemSimulationBackend,
)
from system_simulation.base import SystemRunOutput
from system_simulation.fake_backend import FIXTURE_BITS_PER_SLOT
from system_simulation.ue_generation import generate_candidates
from system_helpers import make_scenario, write_scenario

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger("test")


class _NoSystemBackend(SystemSimulationBackend):
    @property
    def name(self) -> str:
        return "radio_only"

    def health_check(self):
        return {"available": True, "version": "1", "errors": [], "warnings": []}

    def run(self, scenario, experiment_id, log, channel=None):  # pragma: no cover - 不应被调用
        raise AssertionError("must not run")


class _EmptyBackend(_NoSystemBackend):
    def run(self, scenario, experiment_id, log, channel=None):
        out = FakeSystemBackend().run(scenario, experiment_id, log)
        return SystemRunOutput(result=out.result.model_copy(update={"ue_results": []}), slot_trace={})


class _CrashBackend(_NoSystemBackend):
    def run(self, scenario, experiment_id, log, channel=None):
        raise RuntimeError("solver exploded")


def _registry() -> SystemBackendRegistry:
    r = default_system_registry(include_testing=True)
    r.register(SystemBackendDescriptor(id="radio_only", name_zh="r", name_en="r", factory=_NoSystemBackend,
                                       capabilities=(Capability.RADIO_MAP,), model_type=ModelType.TEST_FIXTURE,
                                       source_type="test_fixture"))
    for backend_id, factory in (("empty", _EmptyBackend), ("crash", _CrashBackend)):
        r.register(SystemBackendDescriptor(id=backend_id, name_zh=backend_id, name_en=backend_id, factory=factory,
                                           capabilities=(Capability.SYSTEM_SIMULATION,),
                                           model_type=ModelType.TEST_FIXTURE, source_type="test_fixture"))
    return r


@pytest.fixture
def service(tmp_path):
    write_scenario(tmp_path / "configs")
    return SystemExperimentService(FileSystemExperimentStore(tmp_path / "data"), _registry(),
                                   SystemScenarioCatalog(tmp_path / "configs"), default_kpi_registry(), "test", "abc")


def test_fake_system_backend():
    out = FakeSystemBackend().run(make_scenario(), "EXP-00000000", LOG)
    r = out.result
    assert r.backend == "fake_system" and r.backend_version == "fixture"
    assert [u.decoded_bits for u in r.ue_results] == [FIXTURE_BITS_PER_SLOT * (i + 1) * 10 for i in range(4)]
    assert sum(u.allocated_re_share for u in r.ue_results) == pytest.approx(1.0)
    assert out.slot_trace["decoded_bits"].shape == (10, 4)
    # 确定性 / deterministic
    assert FakeSystemBackend().run(make_scenario(), "EXP-00000001", LOG).result.ue_results == r.ue_results


def test_system_backend_interface():
    assert issubclass(FakeSystemBackend, SystemSimulationBackend)
    with pytest.raises(TypeError):
        SystemSimulationBackend()  # type: ignore[abstract]
    health = FakeSystemBackend().health_check()
    assert set(health) >= {"available", "version", "errors", "warnings"}


def test_system_backend_registry():
    r = default_system_registry(include_testing=False)
    assert [d.id for d in r.list()] == ["sionna_system"]
    d = r.get("sionna_system")
    assert d.model_type is ModelType.SIONNA_SYS and d.source_type == "simulation" and d.provider == "sionna_sys"
    with pytest.raises(SystemBackendNotFoundError):
        r.get("matlab")
    with pytest.raises(ValueError, match="already registered"):
        r.register(d)
    testing = default_system_registry(include_testing=True)
    assert testing.get("fake_system").source_type == "test_fixture"


def test_capability_query():
    r = _registry()
    ids = {d.id for d in r.with_capability(Capability.THROUGHPUT)}
    assert {"sionna_system", "fake_system"} <= ids and "radio_only" not in ids
    assert [d.id for d in r.with_capability(Capability.RADIO_MAP)] == ["radio_only"]


def test_result_canonicalization(service):
    record = service.create("t", "SYSTEM-TEST-001", "fake_system")
    assert record.status is SystemExperimentStatus.SUCCEEDED
    kpis = {k.metric_id: k for k in record.kpis}
    duration = record.result.simulated_duration_s
    for ue in record.result.ue_results:
        assert ue.throughput_metric_id == UE_THROUGHPUT_V0_1
        assert ue.throughput_mbps == pytest.approx(ue.decoded_bits / duration / 1e6)
    assert kpis[NETWORK_THROUGHPUT_V0_1].value == pytest.approx(sum(u.throughput_mbps for u in record.result.ue_results))
    assert record.provenance["measured"] is False and record.provenance["source_type"] == "test_fixture"
    assert record.provenance["model_label"] == "TEST FIXTURE"


def test_artifacts_written(service, tmp_path):
    record = service.create("t", "SYSTEM-TEST-001", "fake_system")
    names = {a.name for a in record.artifacts}
    assert names == {"config.yaml", "result.json", "ue_results.json", "kpi.json", "metadata.json",
                     "slot_trace.npz", "system_summary.png", "run.log"}
    art = tmp_path / "data" / record.experiment_id / "artifacts"
    meta = json.loads((art / "metadata.json").read_text())
    for key in ("platform_version", "git_commit", "experiment_id", "experiment_type", "backend", "backend_version",
                "scenario", "seed", "traffic_model", "scheduler", "link_adaptation", "kpi_versions", "source_type",
                "measured", "created_at", "runtime"):
        assert key in meta, key
    assert meta["experiment_type"] == "system" and meta["measured"] is False
    trace = np.load(art / "slot_trace.npz")
    assert trace["decoded_bits"].sum() == sum(u.decoded_bits for u in record.result.ue_results)
    _, path = service.resolve_artifact(record.experiment_id, "kpi.json")
    assert path.name == "kpi.json"


def test_backend_without_system_capability_rejected(service):
    with pytest.raises(SystemCapabilityNotSupportedError):
        service.create("t", "SYSTEM-TEST-001", "radio_only")


def test_failed_run_persisted(service):
    record = service.create("t", "SYSTEM-TEST-001", "crash")
    assert record.status is SystemExperimentStatus.FAILED
    assert record.error.code.value == "SYSTEM_SIMULATION_FAILED" and "exploded" in record.error.message
    assert service.get(record.experiment_id).status is SystemExperimentStatus.FAILED
    assert "run.log" in {a.name for a in record.artifacts}


def test_no_ue_results_fails(service):
    record = service.create("t", "SYSTEM-TEST-001", "empty")
    assert record.status is SystemExperimentStatus.FAILED and record.error.code.value == "NO_UE_RESULTS"


def test_ue_generator_is_seeded():
    s = make_scenario()
    a, b = generate_candidates(s.ue_generator), generate_candidates(s.ue_generator)
    assert np.array_equal(a, b) and a.shape == (60, 3)
    assert np.all(np.abs(a[:, 0]) <= 100) and np.all(np.abs(a[:, 1]) <= 50) and np.all(a[:, 2] == 1.5)


def test_domain_layers_do_not_import_engines():
    """KPI 与系统级领域层不得依赖任何仿真引擎。"""
    pattern = re.compile(r"^\s*(from|import)\s+(sionna|mitsuba|drjit|torch|simulation\.backends)\b", re.MULTILINE)
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for d in ("evaluation", "system_simulation", "system_optimization", "optimization")
        for p in (REPO_ROOT / "src" / d).rglob("*.py")
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders
