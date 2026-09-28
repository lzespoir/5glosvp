"""平台统一数据模型测试（不依赖 Sionna）/ Canonical model tests (no Sionna required)."""

import json
import re
from pathlib import Path

import numpy as np
import pytest
import yaml

from simulation import (
    ScenarioConfig,
    ScenarioConfigError,
    SimulationResult,
    SimulationStatus,
    new_experiment_id,
)
from simulation.artifacts import export_artifacts
from simulation.models import RadioMapData, layer_statistics, not_available

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_CONFIG = REPO_ROOT / "configs" / "sionna_demo.yaml"


def _make_result(**overrides) -> SimulationResult:
    fields = dict(
        experiment_id="EXP-0000ABCD",
        backend="sionna_rt",
        backend_version="2.1.0",
        scenario_id="SIONNA-DEMO-001",
        status=SimulationStatus.SUCCESS,
        started_at="2026-09-28T00:00:00+00:00",
        finished_at="2026-09-28T00:00:01+00:00",
        runtime_seconds=1.0,
        random_seed=20260927,
        metadata={"source_type": "simulation", "provenance": {"measured": False}},
        metrics={"throughput": not_available("not implemented in Day 1")},
        warnings=["example warning"],
    )
    fields.update(overrides)
    return SimulationResult(**fields)


def _fixture_radio_map() -> RadioMapData:
    # 确定性的测试夹具，仅用于验证导出逻辑，不是仿真结果
    xs, ys = np.meshgrid(np.arange(4.0), np.arange(3.0))
    values = -60.0 - xs - 10.0 * ys
    values[0, 0] = np.nan
    return RadioMapData(
        metric="rss", unit="dBm", values=values, x=xs, y=ys, z=np.full_like(xs, 1.5),
        center=[1.5, 1.0, 1.5], size=[4.0, 3.0], orientation=[0.0, 0.0, 0.0],
        cell_size=[1.0, 1.0], transmitter_positions=np.array([[0.0, 0.0, 10.0]]),
        transmitter_ids=["TX-001"], extra_layers={"rss": values},
    )


def test_load_scenario_config():
    config = ScenarioConfig.from_yaml(DEMO_CONFIG)
    assert config.scenario_id == "SIONNA-DEMO-001"
    assert config.backend == "sionna_rt"
    assert config.scene_name == "etoile"
    assert config.frequency_hz == pytest.approx(3.5e9)
    assert config.bandwidth_hz == pytest.approx(100e6)
    assert config.random_seed == 20260927
    assert len(config.transmitters) == 1
    assert config.transmitters[0].position == [-150.3, 21.63, 42.5]
    assert config.radio_map.metric == "rss"
    assert config.radio_map.cell_size == [5.0, 5.0]
    assert config.name_zh and config.name_en


def test_config_yaml_round_trip():
    config = ScenarioConfig.from_yaml(DEMO_CONFIG)
    assert ScenarioConfig.model_validate(yaml.safe_load(config.to_yaml())) == config


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("scene_name"),
        lambda d: d.update(transmitters=[]),
        lambda d: d["transmitters"][0].update(position=[1.0, 2.0]),
        lambda d: d["radio_map"].update(metric="throughput"),
        lambda d: d["radio_map"].update(cell_size=[0.0, 5.0]),
        lambda d: d.update(frequency_hz=-1),
        lambda d: d.update(unknown_field=1),
    ],
)
def test_invalid_config_raises(tmp_path, mutate):
    data = yaml.safe_load(DEMO_CONFIG.read_text(encoding="utf-8"))
    mutate(data)
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ScenarioConfigError):
        ScenarioConfig.from_yaml(path)


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ScenarioConfigError, match="not found"):
        ScenarioConfig.from_yaml(tmp_path / "missing.yaml")


def test_experiment_id_format():
    ids = {new_experiment_id() for _ in range(100)}
    assert len(ids) == 100
    assert all(re.fullmatch(r"EXP-[0-9A-F]{8}", i) for i in ids)


def test_simulation_result_serialization():
    result = _make_result(radio_map=_fixture_radio_map())
    text = result.to_json()
    data = json.loads(text)
    assert "radio_map" not in data  # 数值矩阵不进入 JSON
    restored = SimulationResult.from_json(text)
    assert restored.model_dump() == result.model_dump()
    assert restored.status is SimulationStatus.SUCCESS
    assert restored.metrics["throughput"]["status"] == "not_available"


def test_layer_statistics_ignores_uncovered_cells():
    values = np.array([[np.nan, -80.0], [-60.0, np.nan]])
    stats = layer_statistics(values, "rss")
    assert stats["num_cells"] == 4
    assert stats["num_covered_cells"] == 2
    assert stats["coverage_ratio"] == pytest.approx(0.5)
    assert stats["min"] == -80.0 and stats["max"] == -60.0 and stats["mean"] == -70.0
    assert stats["unit"] == "dBm"

    empty = layer_statistics(np.full((2, 2), np.nan), "rss")
    assert empty["num_covered_cells"] == 0 and empty["mean"] is None


def test_artifact_export(tmp_path):
    config = ScenarioConfig.from_yaml(DEMO_CONFIG)
    result = _make_result(radio_map=_fixture_radio_map())
    export_artifacts(result, config, tmp_path)

    for name in ["config.yaml", "result.json", "metadata.json", "radio_map.npz", "radio_map.png"]:
        assert (tmp_path / name).is_file(), name
    assert (tmp_path / "radio_map.png").stat().st_size > 0

    saved = SimulationResult.from_json((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert {a.name for a in saved.artifacts} >= {"result.json", "metadata.json", "radio_map.npz"}

    npz = np.load(tmp_path / "radio_map.npz")
    np.testing.assert_array_equal(npz["values"], result.radio_map.values)
    assert str(npz["metric"]) == "rss"
    assert npz["x"].shape == npz["values"].shape

    assert ScenarioConfig.model_validate(
        yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
    ) == config


def test_artifact_export_without_radio_map_warns(tmp_path):
    config = ScenarioConfig.from_yaml(DEMO_CONFIG)
    result = _make_result()
    export_artifacts(result, config, tmp_path)
    assert (tmp_path / "result.json").is_file()
    assert (tmp_path / "metadata.json").is_file()
    assert not (tmp_path / "radio_map.png").exists()
    assert any("No radio map" in w for w in result.warnings)


def test_reproducibility_metadata(tmp_path):
    config = ScenarioConfig.from_yaml(DEMO_CONFIG)
    export_artifacts(_make_result(), config, tmp_path)
    for name in ["result.json", "metadata.json"]:
        data = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        assert data["random_seed"] == 20260927
        assert data["scenario_id"] == "SIONNA-DEMO-001"
        assert data["backend"] == "sionna_rt"
        assert data["backend_version"] == "2.1.0"
