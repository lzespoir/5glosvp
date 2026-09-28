"""
实验产物导出（与后端无关）/ Backend-agnostic artifact export.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import font_manager
from matplotlib.figure import Figure

from .errors import ArtifactExportError
from .models import Artifact, RadioMapData, ScenarioConfig, SimulationResult

logger = logging.getLogger(__name__)

# 优先英文字体，中文字形回退到已安装的 CJK 字体（若系统未安装则仅缺失中文字形）
_CJK_FONT_CANDIDATES = ["Noto Sans CJK SC", "Noto Serif CJK SC", "WenQuanYi Zen Hei", "SimHei"]


def _font_family() -> list[str]:
    installed = {f.name for f in font_manager.fontManager.ttflist}
    return ["DejaVu Sans", *[f for f in _CJK_FONT_CANDIDATES if f in installed]]

CONFIG_FILE = "config.yaml"
RESULT_FILE = "result.json"
METADATA_FILE = "metadata.json"
RADIO_MAP_NPZ = "radio_map.npz"
RADIO_MAP_PNG = "radio_map.png"
RUN_LOG = "run.log"

_MEDIA_TYPES = {
    ".png": "image/png",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".npz": "application/octet-stream",
    ".log": "text/plain",
}


def media_type_for(name: str) -> str:
    return _MEDIA_TYPES.get(Path(name).suffix.lower(), "application/octet-stream")


def ensure_writable_dir(output_dir: Path) -> Path:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        raise ArtifactExportError(f"Output directory is not writable: {output_dir} ({e})") from e
    return output_dir


def save_radio_map_npz(radio_map: RadioMapData, path: Path) -> None:
    arrays: dict[str, np.ndarray] = {
        "values": radio_map.values,
        "x": radio_map.x,
        "y": radio_map.y,
        "z": radio_map.z,
        "metric": np.array(radio_map.metric),
        "unit": np.array(radio_map.unit),
        "center": np.asarray(radio_map.center, dtype=np.float64),
        "size": np.asarray(radio_map.size, dtype=np.float64),
        "orientation": np.asarray(radio_map.orientation, dtype=np.float64),
        "cell_size": np.asarray(radio_map.cell_size, dtype=np.float64),
        "transmitter_positions": radio_map.transmitter_positions,
        "transmitter_ids": np.asarray(radio_map.transmitter_ids),
    }
    for layer_name, layer in radio_map.extra_layers.items():
        arrays[f"layer_{layer_name}"] = layer
    np.savez_compressed(path, **arrays)


def load_radio_map_layers(path: Path) -> dict[str, np.ndarray]:
    """读取 radio_map.npz 中的各层数值（layer_<metric>），key 为 metric 名称。"""
    try:
        with np.load(path) as data:
            return {
                key.removeprefix("layer_"): np.asarray(data[key], dtype=np.float64)
                for key in data.files
                if key.startswith("layer_")
            }
    except (OSError, ValueError) as e:
        raise ArtifactExportError(f"Failed to read radio map layers from {path.name}: {e}") from e


def plot_radio_map(radio_map: RadioMapData, path: Path, subtitle: str) -> None:
    values = radio_map.values
    if not np.isfinite(values).any():
        raise ArtifactExportError("Radio map has no covered cells; refusing to write an empty image")

    with matplotlib.rc_context({"font.family": _font_family(), "axes.unicode_minus": False}):
        _draw_radio_map(radio_map, path, subtitle)


def _draw_radio_map(radio_map: RadioMapData, path: Path, subtitle: str) -> None:
    values = radio_map.values
    fig = Figure(figsize=(9, 7), dpi=120)
    ax = fig.add_subplot()
    finite = values[np.isfinite(values)]
    # 使用分位数裁剪颜色范围，避免极少数极值压缩整体对比度
    vmin, vmax = np.percentile(finite, [1, 99.9])
    mesh = ax.pcolormesh(
        radio_map.x,
        radio_map.y,
        np.ma.masked_invalid(values),
        shading="nearest",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax,
    )
    # 灰色 = 该格点无传播路径（无覆盖或位于建筑内部）
    ax.set_facecolor("#d0d0d0")
    ax.text(
        0.01, 0.01, "gray: no path / 无覆盖", transform=ax.transAxes,
        fontsize=8, color="#404040", va="bottom",
    )
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label(f"{radio_map.metric.upper()} [{radio_map.unit}]")

    tx = radio_map.transmitter_positions
    ax.scatter(tx[:, 0], tx[:, 1], marker="^", c="red", s=80, edgecolors="white", label="TX")
    for tx_id, pos in zip(radio_map.transmitter_ids, tx):
        ax.annotate(tx_id, (pos[0], pos[1]), textcoords="offset points", xytext=(6, 6), color="red")

    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_aspect("equal")
    ax.legend(loc="upper right")
    ax.set_title(f"Sionna RT Radio Map / Sionna RT 无线电地图\n{subtitle}", fontsize=11)
    fig.tight_layout()
    fig.savefig(path)


def export_artifacts(
    result: SimulationResult,
    config: ScenarioConfig,
    output_dir: Path,
    plot_subtitle: str = "",
) -> None:
    """
    导出 config.yaml / radio_map.npz / radio_map.png / metadata.json / result.json。
    result.artifacts 会被原地更新，result.json 最后写入。
    """
    output_dir = ensure_writable_dir(Path(output_dir))

    def _add(name: str, kind: str, description: str) -> None:
        result.artifacts.append(
            Artifact(
                name=name, path=name, kind=kind,
                media_type=media_type_for(name), description=description,
            )
        )
        logger.info("Artifact written: %s", name)

    try:
        (output_dir / CONFIG_FILE).write_text(config.to_yaml(), encoding="utf-8")
        _add(CONFIG_FILE, "config", "Scenario configuration snapshot / 场景配置快照")

        if result.radio_map is not None:
            save_radio_map_npz(result.radio_map, output_dir / RADIO_MAP_NPZ)
            _add(RADIO_MAP_NPZ, "radio_map_data", "Radio map numeric data / 无线电地图数值矩阵")
            plot_radio_map(result.radio_map, output_dir / RADIO_MAP_PNG, plot_subtitle)
            _add(RADIO_MAP_PNG, "radio_map_image", "Radio map visualization / 无线电地图可视化")
        else:
            msg = "No radio map data in result; radio_map.npz / radio_map.png not generated"
            logger.warning(msg)
            result.warnings.append(msg)

        _write_metadata(result, output_dir)
        _add(METADATA_FILE, "metadata", "Experiment metadata and provenance / 元数据与数据来源")

        if (output_dir / RUN_LOG).exists():
            _add(RUN_LOG, "log", "Run log / 运行日志")

        _add(RESULT_FILE, "result", "Canonical simulation result / 平台统一结果")
        (output_dir / RESULT_FILE).write_text(result.to_json(), encoding="utf-8")
    except OSError as e:
        raise ArtifactExportError(f"Failed to write artifacts to {output_dir}: {e}") from e


def finalize_result_files(result: SimulationResult, output_dir: Path) -> None:
    """
    导出完成后重写 result.json / metadata.json，使其包含最终的 runtime
    （artifact_export_seconds / total_seconds 只能在导出结束后得到）。
    """
    output_dir = Path(output_dir)
    try:
        _write_metadata(result, output_dir)
        (output_dir / RESULT_FILE).write_text(result.to_json(), encoding="utf-8")
    except OSError as e:
        raise ArtifactExportError(f"Failed to finalize result files in {output_dir}: {e}") from e


def _write_metadata(result: SimulationResult, output_dir: Path) -> None:
    metadata = {
        "experiment_id": result.experiment_id,
        "scenario_id": result.scenario_id,
        "backend": result.backend,
        "backend_version": result.backend_version,
        "random_seed": result.random_seed,
        **result.metadata,
        "runtime": result.runtime.model_dump(),
    }
    (output_dir / METADATA_FILE).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
