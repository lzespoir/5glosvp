"""
SionnaBackend 适配器测试 / SionnaBackend adapter tests.

测试边界：Platform Config -> Adapter -> Sionna -> Adapter -> Canonical Result。
不测试 Sionna 内部数学正确性。
"""

import json
import re
from pathlib import Path

import numpy as np
import pytest

from simulation import (
    ScenarioConfig,
    ScenarioConfigError,
    SimulationResult,
    SimulationRunError,
    SimulationStatus,
)
from simulation.backends import SionnaBackend, get_backend
from simulation.errors import BackendUnavailableError
from simulation.runner import run_experiment

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_CONFIG = REPO_ROOT / "configs" / "sionna_demo.yaml"

_HEALTH = SionnaBackend().health_check()
requires_sionna = pytest.mark.skipif(
    not _HEALTH["available"],
    reason=f"Sionna RT backend not available: {_HEALTH['errors']}",
)


def _fast_config(**radio_map_overrides) -> ScenarioConfig:
    """降低采样数与分辨率的 demo 配置，用于快速测试适配器。"""
    config = ScenarioConfig.from_yaml(DEMO_CONFIG)
    rm = config.radio_map.model_copy(
        update={"cell_size": [20.0, 20.0], "samples_per_tx": 100_000, **radio_map_overrides}
    )
    return config.model_copy(update={"radio_map": rm})


def test_sionna_backend_health_check():
    report = get_backend("sionna_rt").health_check()
    expected_keys = {
        "backend", "available", "python_version", "sionna_rt_version",
        "mitsuba_available", "drjit_available", "mitsuba_variant",
        "gpu_available", "warnings", "errors",
    }
    assert expected_keys <= set(report)
    assert report["backend"] == "sionna_rt"
    assert isinstance(report["available"], bool)
    json.dumps(report)  # 必须可序列化
    if report["sionna_rt_importable"]:
        assert report["mitsuba_available"] and report["drjit_available"]
        assert report["available"], report["errors"]
    else:
        assert not report["available"]
        assert report["errors"], "unavailable backend must explain why"


def test_unknown_backend_raises():
    with pytest.raises(BackendUnavailableError):
        get_backend("does_not_exist")


def test_run_without_scenario_raises():
    with pytest.raises((SimulationRunError, BackendUnavailableError)):
        SionnaBackend().run()


@requires_sionna
def test_unknown_scene_raises():
    config = ScenarioConfig.from_yaml(DEMO_CONFIG).model_copy(update={"scene_name": "atlantis"})
    with pytest.raises(ScenarioConfigError, match="atlantis"):
        SionnaBackend().load_scenario(config)


@requires_sionna
def test_transmitter_outside_scene_raises():
    config = ScenarioConfig.from_yaml(DEMO_CONFIG)
    tx = config.transmitters[0].model_copy(update={"position": [99999.0, 0.0, 30.0]})
    config = config.model_copy(update={"transmitters": [tx]})
    with pytest.raises(ScenarioConfigError, match="outside scene"):
        SionnaBackend().load_scenario(config)


@requires_sionna
def test_backend_mismatch_raises():
    config = ScenarioConfig.from_yaml(DEMO_CONFIG).model_copy(update={"backend": "fast"})
    with pytest.raises(ScenarioConfigError):
        SionnaBackend().load_scenario(config)


@requires_sionna
def test_run_produces_canonical_result():
    backend = SionnaBackend()
    config = _fast_config()
    backend.load_scenario(config)
    result = backend.run()

    assert isinstance(result, SimulationResult)
    assert result.status is SimulationStatus.SUCCESS
    assert re.fullmatch(r"EXP-[0-9A-F]{8}", result.experiment_id)
    assert result.runtime_seconds > 0
    assert result.backend_version == _HEALTH["sionna_rt_version"]

    rm = result.radio_map
    assert rm is not None and rm.metric == "rss" and rm.unit == "dBm"
    assert rm.values.ndim == 2 and rm.values.shape == rm.x.shape == rm.y.shape
    assert np.isfinite(rm.values).any(), "radio map must not be empty"
    assert set(rm.extra_layers) == {"rss", "path_gain", "sinr"}

    stats = result.metrics["radio_map"]
    assert stats["num_covered_cells"] > 0
    assert stats["min"] <= stats["mean"] <= stats["max"]
    assert result.metrics["throughput"]["status"] == "not_available"

    prov = result.metadata["provenance"]
    assert prov["generated"] is True and prov["measured"] is False
    assert result.metadata["source_type"] == "simulation"


@requires_sionna
def test_same_seed_is_reproducible():
    config = _fast_config()
    values = []
    for _ in range(2):
        backend = SionnaBackend()
        backend.load_scenario(config)
        values.append(backend.run().radio_map.values)
    np.testing.assert_allclose(values[0], values[1], equal_nan=True, rtol=1e-4)


@requires_sionna
def test_end_to_end_experiment_artifacts(tmp_path):
    config = _fast_config()
    outcome = run_experiment(SionnaBackend(), config, tmp_path)
    out = outcome.output_dir
    assert out.parent == tmp_path and out.name == outcome.result.experiment_id

    for name in ["config.yaml", "result.json", "metadata.json", "radio_map.npz", "radio_map.png", "run.log"]:
        assert (out / name).is_file(), name

    log = (out / "run.log").read_text(encoding="utf-8")
    assert outcome.result.experiment_id in log
    assert "Simulation start" in log and "Simulation finish" in log

    result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    metadata = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    for data in (result, metadata):
        assert data["random_seed"] == config.random_seed
        assert data["scenario_id"] == config.scenario_id
        assert data["backend"] == "sionna_rt"
        assert data["backend_version"] == _HEALTH["sionna_rt_version"]
    assert metadata["provenance"]["measured"] is False
    assert metadata["total_runtime_seconds"] >= metadata["simulation_runtime_seconds"] > 0


def test_only_adapter_imports_sionna():
    """架构约束：只有 sionna_backend.py 可以 import Sionna / Mitsuba / Dr.Jit。"""
    pattern = re.compile(r"^\s*(from|import)\s+(sionna|mitsuba|drjit)\b", re.MULTILINE)
    allowed = {REPO_ROOT / "src" / "simulation" / "backends" / "sionna_backend.py"}
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for d in ("src", "scripts")
        for p in (REPO_ROOT / d).rglob("*.py")
        if p not in allowed and pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"Direct Sionna imports outside adapter: {offenders}"
