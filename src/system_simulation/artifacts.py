"""
系统级实验产物导出（与仿真器无关）/ Simulator-agnostic system artifact export.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from matplotlib.figure import Figure

from evaluation.kpi import KpiResult

from .models import ArtifactRef, SystemScenario, SystemSimulationResult

CONFIG = ArtifactRef(name="config.yaml", type="config", media_type="application/x-yaml",
                     description="System scenario snapshot / 系统场景配置快照")
RESULT = ArtifactRef(name="result.json", type="json", media_type="application/json",
                     description="Canonical system simulation result + KPIs / 统一系统级结果与 KPI")
UE_RESULTS = ArtifactRef(name="ue_results.json", type="json", media_type="application/json",
                         description="Per-UE results / 单 UE 结果")
KPI = ArtifactRef(name="kpi.json", type="json", media_type="application/json",
                  description="KPI results with provenance / KPI 结果与溯源")
METADATA = ArtifactRef(name="metadata.json", type="json", media_type="application/json",
                       description="Metadata and provenance / 元数据与数据来源")
SLOT_TRACE = ArtifactRef(name="slot_trace.npz", type="binary", media_type="application/octet-stream",
                         description="Per-slot per-UE trace for independent verification / 每时隙原始记录")
SUMMARY = ArtifactRef(name="system_summary.png", type="image", media_type="image/png",
                      description="Network view and UE throughput / 网络视图与 UE 吞吐率")
RUN_LOG = ArtifactRef(name="run.log", type="log", media_type="text/plain", description="Run log / 运行日志")


def _json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _summary_png(path: Path, scenario: SystemScenario, result: SystemSimulationResult, source_label: str) -> None:
    fig = Figure(figsize=(13, 5.2), layout="constrained")
    ax_map, ax_bar = fig.subplots(1, 2, width_ratios=[1.1, 1])
    ues = result.ue_results
    tput = np.array([u.throughput_mbps or 0.0 for u in ues])
    xs = [u.position[0] for u in ues]
    ys = [u.position[1] for u in ues]
    for cell in scenario.cells:
        p = scenario.cell_position(cell)
        ax_map.scatter([p[0]], [p[1]], marker="^", s=180, c="red", zorder=3, label=f"BS / {cell.cell_id}")
    sc = ax_map.scatter(xs, ys, c=tput, cmap="viridis", s=90, edgecolors="black", zorder=3)
    for u, x, y in zip(ues, xs, ys):
        ax_map.annotate(u.ue_id, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=8)
    fig.colorbar(sc, ax=ax_map, label="UE throughput [Mbps]")
    ax_map.set_xlabel("x [m]")
    ax_map.set_ylabel("y [m]")
    ax_map.set_aspect("equal", adjustable="datalim")
    ax_map.grid(alpha=0.3)
    ax_map.legend(loc="best", fontsize=8)
    ax_map.set_title("Network view (no map background)")
    ax_bar.bar([u.ue_id for u in ues], tput, color="#1d4ed8")
    ax_bar.set_ylabel("UE throughput [Mbps]")
    ax_bar.set_title("UE_THROUGHPUT_V0_1")
    ax_bar.grid(axis="y", alpha=0.3)
    fig.suptitle(f"{scenario.scenario_id} · {source_label} · Not measured · Not acceptance evidence", fontsize=10)
    fig.savefig(path, dpi=100)


def export_artifacts(
    output_dir: Path,
    scenario: SystemScenario,
    result: SystemSimulationResult,
    kpis: list[KpiResult],
    slot_trace: dict[str, np.ndarray],
    metadata: dict[str, Any],
    source_label: str,
) -> list[ArtifactRef]:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / CONFIG.name).write_text(
        yaml.safe_dump(scenario.model_dump(mode="json"), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    kpi_data = [k.model_dump(mode="json") for k in kpis]
    _json(output_dir / RESULT.name, {"result": result.model_dump(mode="json"), "kpis": kpi_data})
    _json(output_dir / UE_RESULTS.name, [u.model_dump(mode="json") for u in result.ue_results])
    _json(output_dir / KPI.name, kpi_data)
    _json(output_dir / METADATA.name, metadata)
    np.savez_compressed(
        output_dir / SLOT_TRACE.name,
        ue_ids=np.array([u.ue_id for u in result.ue_results]),
        slot_duration_s=np.array(result.slot_duration_s),
        **slot_trace,
    )
    _summary_png(output_dir / SUMMARY.name, scenario, result, source_label)
    refs = [CONFIG, RESULT, UE_RESULTS, KPI, METADATA, SLOT_TRACE, SUMMARY]
    if (output_dir / RUN_LOG.name).is_file():
        refs.append(RUN_LOG)
    return refs
