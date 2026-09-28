"""
FakeBackend —— 仅用于软件单元测试 / FOR SOFTWARE UNIT TESTING ONLY.

输出是确定性的测试夹具（test fixture），不是仿真结果，也不是实测数据。
结果中 source_type = "test_fixture"，不得作为任何无线指标的依据。
只有在 TESTING=true 时才会注册进默认后端列表。

Output is a deterministic test fixture, NOT a simulation result.
"""

from __future__ import annotations

import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import export_artifacts
from .base import SimulationBackend
from .errors import SimulationRunError
from .models import (
    METRIC_UNITS,
    ProvenanceTag,
    RadioMapData,
    RuntimeInfo,
    ScenarioConfig,
    SimulationResult,
    SimulationStatus,
    new_experiment_id,
    not_available,
)

FAKE_BACKEND_ID = "fake"
FAKE_BACKEND_VERSION = "0.0.0-test"

# 夹具常数（非物理参数）/ Fixture constants, not physical parameters
FIXTURE_PATH_GAIN_OFFSET_DB = -120.0
FIXTURE_PATH_GAIN_SLOPE_DB = 4.0
FIXTURE_NOISE_DBM = -90.0
FIXTURE_DEFAULT_POWER_DBM = 44.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeBackend(SimulationBackend):
    """确定性假后端，可配置为运行失败 / Deterministic fake backend."""

    def __init__(self, fail_on_run: bool = False, grid_shape: tuple[int, int] = (8, 10)) -> None:
        self._fail_on_run = fail_on_run
        self._grid_shape = grid_shape
        self._config: ScenarioConfig | None = None

    @property
    def name(self) -> str:
        return FAKE_BACKEND_ID

    def health_check(self) -> dict[str, Any]:
        return {
            "backend": FAKE_BACKEND_ID,
            "available": True,
            "version": FAKE_BACKEND_VERSION,
            "python_version": platform.python_version(),
            "warnings": ["FakeBackend is for software unit testing only"],
            "errors": [],
        }

    def load_scenario(self, config: ScenarioConfig) -> None:
        self._config = config

    def run(self, experiment_id: str | None = None) -> SimulationResult:
        if self._config is None:
            raise SimulationRunError("No scenario loaded; call load_scenario() first")
        if self._fail_on_run:
            raise SimulationRunError("FakeBackend configured to fail (unit test)")
        config = self._config
        started_at = _utc_now()
        t0 = time.perf_counter()
        radio_map = self._fixture_radio_map(config)
        runtime = time.perf_counter() - t0
        return SimulationResult(
            experiment_id=experiment_id or new_experiment_id(),
            backend=FAKE_BACKEND_ID,
            backend_version=FAKE_BACKEND_VERSION,
            scenario_id=config.scenario_id,
            status=SimulationStatus.SUCCESS,
            started_at=started_at,
            finished_at=_utc_now(),
            runtime_seconds=runtime,
            runtime=RuntimeInfo(simulation_seconds=runtime),
            random_seed=config.random_seed,
            metadata={
                "backend": FAKE_BACKEND_ID,
                "scene": config.scene_name,
                "frequency_hz": config.frequency_hz,
                "bandwidth_hz": config.bandwidth_hz,
                "source_type": "test_fixture",
                "provenance": {
                    "tag": ProvenanceTag.ASSUMPTION.value,
                    "description": "Deterministic software test fixture (FakeBackend)",
                    "engine": "FakeBackend (software unit test only)",
                    "generated": True,
                    "measured": False,
                },
            },
            metrics={
                "radio_map": radio_map.statistics(),
                "radio_map_layers": radio_map.layer_statistics(),
                "throughput": not_available("not implemented"),
            },
            warnings=["FakeBackend output is a test fixture, not a simulation result"],
            radio_map=radio_map,
        )

    def _fixture_radio_map(self, config: ScenarioConfig) -> RadioMapData:
        """
        确定性夹具：path_gain 随格点距离线性下降，右上角 2×2 格点无路径（NaN）；
        rss = path_gain + 发射功率，sinr = rss − 夹具噪声底，因此 rss/sinr 随发射功率平移。
        """
        ny, nx = self._grid_shape
        xs, ys = np.meshgrid(np.arange(nx, dtype=np.float64), np.arange(ny, dtype=np.float64))
        path_gain = FIXTURE_PATH_GAIN_OFFSET_DB - FIXTURE_PATH_GAIN_SLOPE_DB * (xs + ys)
        path_gain[(xs >= nx - 2) & (ys >= ny - 2)] = np.nan
        power = config.transmitters[0].power_dbm
        rss = path_gain + (FIXTURE_DEFAULT_POWER_DBM if power is None else power)
        layers = {"rss": rss, "path_gain": path_gain, "sinr": rss - FIXTURE_NOISE_DBM}
        metric = config.radio_map.metric
        return RadioMapData(
            metric=metric, unit=METRIC_UNITS[metric], values=layers[metric],
            x=xs, y=ys, z=np.zeros_like(xs),
            center=[nx / 2, ny / 2, 0.0], size=[float(nx), float(ny)],
            orientation=[0.0, 0.0, 0.0], cell_size=[1.0, 1.0],
            transmitter_positions=np.array([t.position for t in config.transmitters]),
            transmitter_ids=[t.id for t in config.transmitters],
            extra_layers=layers,
        )

    def export(self, result: SimulationResult, output_dir: Path) -> None:
        if self._config is None:
            raise SimulationRunError("No scenario loaded; nothing to export")
        export_artifacts(result, self._config, Path(output_dir), plot_subtitle="FakeBackend test fixture")
