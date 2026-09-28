"""
Sionna RT 仿真适配器 / Sionna RT simulation backend adapter.

架构约束：整个平台中只有本模块允许 import Sionna / Mitsuba / Dr.Jit。
Architecture rule: only this module may import Sionna / Mitsuba / Dr.Jit.

Platform Config -> Sionna API -> Sionna Result -> Canonical Result
"""

from __future__ import annotations

import importlib.metadata
import logging
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from ..artifacts import export_artifacts
from ..base import SimulationBackend
from ..errors import (
    BackendUnavailableError,
    ScenarioConfigError,
    SimulationRunError,
)
from ..models import (
    METRIC_UNITS,
    ProvenanceTag,
    RadioMapData,
    ScenarioConfig,
    SimulationResult,
    SimulationStatus,
    new_experiment_id,
    not_available,
)

# 导入 Sionna 会自动选择 Mitsuba variant（优先 CUDA，否则 LLVM）。
# 导入失败时不抛出，以便 health_check 返回诊断信息。
try:
    import drjit as dr
    import mitsuba as mi
    import sionna.rt as srt
    from sionna.rt import PlanarArray, RadioMapSolver, Transmitter, load_scene

    _SIONNA_IMPORT_ERROR: str | None = None
except Exception as _e:  # noqa: BLE001 - 需要捕获 Mitsuba/Dr.Jit 初始化时的任意错误并用于诊断
    _SIONNA_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

logger = logging.getLogger(__name__)

BACKEND_NAME = "sionna_rt"
MIN_PYTHON = (3, 10)

# Day 1 采用 Sionna 官方教程中已验证的天线配置
TX_ARRAY_SPEC: dict[str, Any] = {
    "num_rows": 1,
    "num_cols": 1,
    "vertical_spacing": 0.5,
    "horizontal_spacing": 0.5,
    "pattern": "tr38901",
    "polarization": "V",
}
RX_ARRAY_SPEC: dict[str, Any] = {
    "num_rows": 1,
    "num_cols": 1,
    "vertical_spacing": 0.5,
    "horizontal_spacing": 0.5,
    "pattern": "iso",
    "polarization": "V",
}


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_db(linear: np.ndarray, offset_db: float = 0.0) -> np.ndarray:
    """线性值转 dB，0 或负值（无覆盖）转为 NaN。"""
    out = np.full(linear.shape, np.nan, dtype=np.float64)
    positive = linear > 0
    out[positive] = 10.0 * np.log10(linear[positive].astype(np.float64)) + offset_db
    return out


class SionnaBackend(SimulationBackend):
    """Sionna RT 仿真后端 / Sionna RT simulation backend."""

    def __init__(self) -> None:
        self._config: ScenarioConfig | None = None
        self._scene: Any = None
        self._scene_path: str | None = None
        self._tx_power_dbm: dict[str, float] = {}
        self._warnings: list[str] = []

    # ------------------------------------------------------------------
    # 基本信息 / Basic info
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return BACKEND_NAME

    @property
    def version(self) -> str | None:
        return _package_version("sionna-rt")

    # ------------------------------------------------------------------
    # 环境检查 / Health check
    # ------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        warnings: list[str] = []
        errors: list[str] = []
        py_ok = sys.version_info[:2] >= MIN_PYTHON
        if not py_ok:
            errors.append(f"Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} required")

        report: dict[str, Any] = {
            "backend": BACKEND_NAME,
            "available": False,
            "python_version": platform.python_version(),
            "python_ok": py_ok,
            "platform": platform.platform(),
            "sionna_rt_installed": _package_version("sionna-rt") is not None,
            "sionna_rt_version": _package_version("sionna-rt"),
            "sionna_rt_importable": _SIONNA_IMPORT_ERROR is None,
            "mitsuba_available": False,
            "mitsuba_version": _package_version("mitsuba"),
            "drjit_available": False,
            "drjit_version": _package_version("drjit"),
            "mitsuba_variant": None,
            "gpu_available": False,
            "llvm_available": False,
            "scene_smoke_test": False,
            "warnings": warnings,
            "errors": errors,
        }

        if _SIONNA_IMPORT_ERROR is not None:
            if not report["sionna_rt_installed"]:
                errors.append("sionna-rt is not installed (pip install sionna-rt)")
            errors.append(f"Failed to import sionna.rt: {_SIONNA_IMPORT_ERROR}")
            return report

        report["mitsuba_available"] = True
        report["drjit_available"] = True
        report["mitsuba_variant"] = mi.variant()
        report["gpu_available"] = bool(dr.has_backend(dr.JitBackend.CUDA))
        report["llvm_available"] = bool(dr.has_backend(dr.JitBackend.LLVM))

        variant = mi.variant() or ""
        if not variant:
            errors.append("No Mitsuba variant selected (neither CUDA nor LLVM backend usable)")
        elif not variant.startswith("cuda"):
            warnings.append(f"Running on CPU variant '{variant}'; GPU not used (slower but valid)")
        if not report["gpu_available"]:
            warnings.append("CUDA GPU not found (optional)")

        try:
            load_scene()  # 空场景冒烟测试 / empty-scene smoke test
            report["scene_smoke_test"] = True
        except Exception as e:  # noqa: BLE001 - 诊断用途，错误写入报告
            errors.append(f"Empty scene smoke test failed: {type(e).__name__}: {e}")

        report["available"] = py_ok and bool(variant) and report["scene_smoke_test"]
        return report

    # ------------------------------------------------------------------
    # 场景加载 / Scenario loading
    # ------------------------------------------------------------------

    def _require_sionna(self) -> None:
        if _SIONNA_IMPORT_ERROR is not None:
            raise BackendUnavailableError(
                f"Sionna RT backend unavailable: {_SIONNA_IMPORT_ERROR}. "
                "Run scripts/check_environment.py for diagnostics."
            )

    @staticmethod
    def available_builtin_scenes() -> list[str]:
        if _SIONNA_IMPORT_ERROR is not None:
            return []
        return sorted(
            n for n in dir(srt.scene)
            if not n.startswith("_") and isinstance(getattr(srt.scene, n), str)
            and getattr(srt.scene, n).endswith(".xml")
        )

    def _resolve_scene(self, scene_name: str) -> str:
        builtin = getattr(srt.scene, scene_name, None)
        if isinstance(builtin, str) and builtin.endswith(".xml"):
            return builtin
        if Path(scene_name).is_file():
            return str(Path(scene_name).resolve())
        raise ScenarioConfigError(
            f"Scene '{scene_name}' not found. Built-in scenes: "
            f"{', '.join(self.available_builtin_scenes())}"
        )

    def _validate_transmitters(self, config: ScenarioConfig) -> None:
        bbox = self._scene.mi_scene.bbox()
        lo = [float(bbox.min.x), float(bbox.min.y), float(bbox.min.z)]
        hi = [float(bbox.max.x), float(bbox.max.y), float(bbox.max.z)]
        ids = [t.id for t in config.transmitters]
        if len(set(ids)) != len(ids):
            raise ScenarioConfigError(f"Duplicate transmitter ids: {ids}")
        for tx in config.transmitters:
            x, y, z = tx.position
            if not all(np.isfinite(tx.position)):
                raise ScenarioConfigError(f"Transmitter {tx.id}: position must be finite")
            if not (lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1]):
                raise ScenarioConfigError(
                    f"Transmitter {tx.id}: position ({x}, {y}) outside scene x/y bounds "
                    f"x=[{lo[0]:.1f}, {hi[0]:.1f}], y=[{lo[1]:.1f}, {hi[1]:.1f}]"
                )
            if z < lo[2]:
                raise ScenarioConfigError(
                    f"Transmitter {tx.id}: height z={z} below scene ground z={lo[2]:.1f}"
                )
            if z > hi[2]:
                self._warnings.append(
                    f"Transmitter {tx.id}: z={z} above highest scene geometry ({hi[2]:.1f} m)"
                )

    def load_scenario(self, config: ScenarioConfig) -> None:
        self._require_sionna()
        if config.backend != BACKEND_NAME:
            raise ScenarioConfigError(
                f"Scenario backend '{config.backend}' does not match '{BACKEND_NAME}'"
            )
        self._warnings = []
        self._scene_path = self._resolve_scene(config.scene_name)
        logger.info("Loading scene '%s' from %s", config.scene_name, self._scene_path)
        try:
            scene = load_scene(self._scene_path)
        except Exception as e:  # noqa: BLE001 - 转换为平台异常
            raise ScenarioConfigError(f"Failed to load scene '{config.scene_name}': {e}") from e

        scene.frequency = config.frequency_hz
        scene.bandwidth = config.bandwidth_hz
        scene.tx_array = PlanarArray(**TX_ARRAY_SPEC)
        scene.rx_array = PlanarArray(**RX_ARRAY_SPEC)
        self._scene = scene
        self._config = config

        self._validate_transmitters(config)
        self._tx_power_dbm = {}
        for tx_cfg in config.transmitters:
            kwargs: dict[str, Any] = {
                "name": tx_cfg.id,
                "position": mi.Point3f(*tx_cfg.position),
            }
            if tx_cfg.orientation is not None:
                kwargs["orientation"] = mi.Point3f(*tx_cfg.orientation)
            if tx_cfg.power_dbm is not None:
                kwargs["power_dbm"] = tx_cfg.power_dbm
            try:
                tx = Transmitter(**kwargs)
                scene.add(tx)
            except Exception as e:  # noqa: BLE001 - 转换为平台异常
                raise ScenarioConfigError(f"Failed to add transmitter {tx_cfg.id}: {e}") from e
            actual_power = float(np.asarray(tx.power_dbm).ravel()[0])
            self._tx_power_dbm[tx_cfg.id] = actual_power
            if tx_cfg.power_dbm is None:
                self._warnings.append(
                    f"Transmitter {tx_cfg.id}: power_dbm not set, using Sionna default "
                    f"{actual_power:.1f} dBm"
                )
            logger.info(
                "Transmitter added: id=%s position=%s power_dbm=%.1f",
                tx_cfg.id, tx_cfg.position, actual_power,
            )
        for w in self._warnings:
            logger.warning(w)

    # ------------------------------------------------------------------
    # 仿真执行 / Run
    # ------------------------------------------------------------------

    def _solver_kwargs(self, config: ScenarioConfig) -> dict[str, Any]:
        rm_cfg = config.radio_map
        kwargs: dict[str, Any] = {
            "cell_size": mi.Point2f(*rm_cfg.cell_size),
            "max_depth": rm_cfg.max_depth,
            "samples_per_tx": rm_cfg.samples_per_tx,
            "seed": config.random_seed,
        }
        if rm_cfg.measurement_area is not None:
            area = rm_cfg.measurement_area
            kwargs["center"] = mi.Point3f(*area.center)
            kwargs["size"] = mi.Point2f(*area.size)
            kwargs["orientation"] = mi.Point3f(*area.orientation)
        return kwargs

    def run(self, experiment_id: str | None = None) -> SimulationResult:
        self._require_sionna()
        if self._scene is None or self._config is None:
            raise SimulationRunError("No scenario loaded; call load_scenario() first")
        config = self._config
        experiment_id = experiment_id or new_experiment_id()
        solver_kwargs = self._solver_kwargs(config)

        logger.info(
            "Simulation start: experiment_id=%s backend=%s scene=%s",
            experiment_id, BACKEND_NAME, config.scene_name,
        )
        started_at = _utc_now()
        t0 = time.perf_counter()
        try:
            rm = RadioMapSolver()(self._scene, **solver_kwargs)
            # Dr.Jit 为惰性求值，转换为 numpy 才会真正完成计算，因此计入仿真耗时
            path_gain = rm.path_gain.numpy()
            rss_w = rm.rss.numpy()
            sinr = rm.sinr.numpy()
            cell_centers = rm.cell_centers.numpy()
        except Exception as e:  # noqa: BLE001 - 转换为平台异常
            raise SimulationRunError(f"Sionna RT radio map computation failed: {e}") from e
        runtime = time.perf_counter() - t0
        finished_at = _utc_now()
        logger.info("Simulation finish: runtime=%.3f s", runtime)

        radio_map = self._to_radio_map_data(rm, config, path_gain, rss_w, sinr, cell_centers)
        stats = radio_map.statistics()
        if stats["num_covered_cells"] == 0:
            raise SimulationRunError(
                "Radio map is empty (no covered cells); check transmitter position "
                "and measurement area"
            )

        metrics: dict[str, Any] = {
            "radio_map": stats,
            "radio_map_layers": radio_map.layer_statistics(),
            "rsrp": not_available("RSRP (per resource element) not implemented in Day 1"),
            "throughput": not_available("not implemented in Day 1"),
            "bler": not_available("not implemented in Day 1"),
        }

        return SimulationResult(
            experiment_id=experiment_id,
            backend=BACKEND_NAME,
            backend_version=self.version,
            scenario_id=config.scenario_id,
            status=SimulationStatus.SUCCESS,
            started_at=started_at,
            finished_at=finished_at,
            runtime_seconds=runtime,
            random_seed=config.random_seed,
            metadata=self._build_metadata(config, solver_kwargs),
            metrics=metrics,
            warnings=list(self._warnings),
            radio_map=radio_map,
        )

    def _to_radio_map_data(
        self,
        rm: Any,
        config: ScenarioConfig,
        path_gain: np.ndarray,
        rss_w: np.ndarray,
        sinr: np.ndarray,
        cell_centers: np.ndarray,
    ) -> RadioMapData:
        # 多发射端时取最佳服务小区（max over TX），形状 (num_tx, ny, nx) -> (ny, nx)
        layers = {
            "rss": _to_db(rss_w.max(axis=0), offset_db=30.0),  # W -> dBm
            "path_gain": _to_db(path_gain.max(axis=0)),
            "sinr": _to_db(sinr.max(axis=0)),
        }
        metric = config.radio_map.metric
        return RadioMapData(
            metric=metric,
            unit=METRIC_UNITS[metric],
            values=layers[metric],
            x=cell_centers[..., 0].astype(np.float64),
            y=cell_centers[..., 1].astype(np.float64),
            z=cell_centers[..., 2].astype(np.float64),
            center=[float(v) for v in np.asarray(rm.center).ravel()],
            size=[float(v) for v in np.asarray(rm.size).ravel()],
            orientation=[float(v) for v in np.asarray(rm.orientation).ravel()],
            cell_size=[float(v) for v in np.asarray(rm.cell_size).ravel()],
            transmitter_positions=np.array(
                [t.position for t in config.transmitters], dtype=np.float64
            ),
            transmitter_ids=[t.id for t in config.transmitters],
            extra_layers=layers,
        )

    def _build_metadata(self, config: ScenarioConfig, solver_kwargs: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": BACKEND_NAME,
            "backend_version": self.version,
            "engine_versions": {
                "sionna_rt": self.version,
                "mitsuba": _package_version("mitsuba"),
                "drjit": _package_version("drjit"),
                "mitsuba_variant": mi.variant(),
                "python": platform.python_version(),
            },
            "scene": config.scene_name,
            "scene_path": self._scene_path,
            "scenario_name_zh": config.name_zh,
            "scenario_name_en": config.name_en,
            "frequency_hz": config.frequency_hz,
            "bandwidth_hz": config.bandwidth_hz,
            "random_seed": config.random_seed,
            "radio_map_api": "sionna.rt.RadioMapSolver (PlanarRadioMap)",
            "radio_map_solver_params": {
                "cell_size": list(config.radio_map.cell_size),
                "max_depth": solver_kwargs["max_depth"],
                "samples_per_tx": solver_kwargs["samples_per_tx"],
                "seed": solver_kwargs["seed"],
                "measurement_area": (
                    config.radio_map.measurement_area.model_dump()
                    if config.radio_map.measurement_area else "auto (scene bounding box)"
                ),
            },
            "multi_tx_aggregation": "max over transmitters (best server)",
            "transmitters": [
                {
                    "id": t.id,
                    "position": t.position,
                    "orientation": t.orientation,
                    "power_dbm": self._tx_power_dbm.get(t.id),
                }
                for t in config.transmitters
            ],
            "antenna": {
                "tx_array": {**TX_ARRAY_SPEC, "provenance": ProvenanceTag.STANDARD.value,
                             "note": "3GPP TR 38.901 antenna pattern (Sionna built-in)"},
                "rx_array": {**RX_ARRAY_SPEC, "provenance": ProvenanceTag.ASSUMPTION.value,
                             "note": "Isotropic receiver (engineering assumption)"},
            },
            "source_type": "simulation",
            "provenance": {
                "tag": ProvenanceTag.GENERATED.value,
                "description": "[G] Generated by Sionna RT",
                "engine": "Sionna RT",
                "generated": True,
                "measured": False,
            },
        }

    # ------------------------------------------------------------------
    # 导出 / Export
    # ------------------------------------------------------------------

    def export(self, result: SimulationResult, output_dir: Path) -> None:
        if self._config is None:
            raise SimulationRunError("No scenario loaded; nothing to export")
        subtitle = (
            f"scene={self._config.scene_name}  f={self._config.frequency_hz / 1e9:.2f} GHz  "
            f"{result.experiment_id}"
        )
        export_artifacts(result, self._config, Path(output_dir), plot_subtitle=subtitle)
