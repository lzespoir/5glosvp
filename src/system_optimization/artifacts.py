"""
系统级优化证据导出 / System optimization evidence export.

图表只绘制后端已计算的数值（点 / 柱），不做平滑或插值。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure

from algorithms import AlgorithmMetadata
from evidence import EvidenceDescriptor

from .models import SystemOptimizationArtifact, SystemOptimizationCandidate, SystemOptimizationRecord

EVALUATION_CONTEXT = SystemOptimizationArtifact(
    name="evaluation-context.json", media_type="application/json",
    description="Frozen common evaluation context / 冻结的公共评价上下文")
BENCHMARK_PROTOCOL = SystemOptimizationArtifact(
    name="benchmark-protocol.json", media_type="application/json",
    description="Benchmark protocol used by this run / 本次运行使用的评价协议")
CANDIDATE_SUMMARY = SystemOptimizationArtifact(
    name="candidate-summary.json", media_type="application/json",
    description="Baseline and candidate KPIs / 基线与候选 KPI 汇总")
COMPARISON_PNG = SystemOptimizationArtifact(
    name="comparison.png", media_type="image/png",
    description="Candidate KPIs by parameter value / 各候选 KPI")
PER_UE_PNG = SystemOptimizationArtifact(
    name="per-ue-comparison.png", media_type="image/png",
    description="Per-UE throughput, baseline vs best / 单 UE 吞吐率对比")
ALGORITHM_METADATA = SystemOptimizationArtifact(
    name="algorithm-metadata.json", media_type="application/json",
    description="Algorithm metadata, capabilities and hyperparameter schema / 算法元数据与能力声明")
PARAMETER_SPACE = SystemOptimizationArtifact(
    name="parameter-space.json", media_type="application/json",
    description="Parameter space searched by the algorithm / 参数空间")
ALGORITHM_CONFIG = SystemOptimizationArtifact(
    name="algorithm-config.json", media_type="application/json",
    description="Resolved hyperparameters, evaluation budget and provenance hashes / 算法配置与预算")
ALGORITHM_TRACE = SystemOptimizationArtifact(
    name="algorithm-trace.json", media_type="application/json",
    description="suggest → evaluate → observe trace and stop reason / 算法轨迹与停止原因")
EVIDENCE_DESCRIPTOR = SystemOptimizationArtifact(
    name="evidence-descriptor.json", media_type="application/json",
    description="Evidence descriptor (verification ≠ acceptance) / 证据描述符")


def _json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def candidate_summary(record: SystemOptimizationRecord) -> list[dict[str, Any]]:
    rows = []
    for c in record.all_evaluations():
        rows.append({
            "candidate_id": c.candidate_id,
            "is_baseline": c.is_baseline,
            "reused_baseline": c.reused_baseline,
            "cache_hit": c.cache_hit,
            "reused_candidate_id": c.reused_candidate_id,
            "algorithm_round": c.algorithm_round,
            "parameters": c.parameters,
            "status": c.status.value,
            "experiment_id": c.experiment_id,
            "experiment_ids": c.experiment_ids,
            "evaluation_context_id": c.evaluation_context_id,
            "network_throughput_mbps": c.network_throughput_mbps.model_dump() if c.network_throughput_mbps else None,
            "average_ue_throughput_mbps": c.average_ue_throughput_mbps.model_dump()
            if c.average_ue_throughput_mbps else None,
            "p5_ue_throughput_mbps": c.p5_ue_throughput_mbps.model_dump() if c.p5_ue_throughput_mbps else None,
            "objective": c.objective.value if c.objective else None,
            "runtime_seconds": c.runtime_seconds,
            "error": c.error.model_dump() if c.error else None,
            "is_best": c.candidate_id == record.best_candidate_id,
        })
    return rows


def _param(c: SystemOptimizationCandidate, parameter_id: str) -> float:
    return float(c.parameters[parameter_id])


def _comparison_png(path: Path, record: SystemOptimizationRecord) -> None:
    pid = record.parameter.id
    evaluated = [c for c in record.all_evaluations() if c.network_throughput_mbps is not None]
    fig = Figure(figsize=(13, 4.6), layout="constrained")
    axes = fig.subplots(1, 3)
    series = (("network_throughput_mbps", "Network throughput (objective)"),
              ("average_ue_throughput_mbps", "Average UE throughput"),
              ("p5_ue_throughput_mbps", "P5 UE throughput"))
    for ax, (field, title) in zip(axes, series):
        for c in evaluated:
            stat = getattr(c, field)
            color = "#6b7280" if c.is_baseline else ("#16a34a" if c.candidate_id == record.best_candidate_id
                                                     else "#1d4ed8")
            marker = "s" if c.is_baseline else "o"
            ax.errorbar([_param(c, pid)], [stat.mean], yerr=[[stat.mean - stat.min], [stat.max - stat.mean]],
                        fmt=marker, color=color, ms=8, capsize=3)
            if c.reused:
                continue
            aliases = [o.candidate_id for o in evaluated
                       if o.reused and (o.reused_candidate_id == c.candidate_id
                                        or (c.is_baseline and o.reused_baseline))]
            label = " = ".join([c.candidate_id, *aliases])
            ax.annotate(label, (_param(c, pid), stat.mean), textcoords="offset points", xytext=(5, 5),
                        fontsize=7)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(f"{record.parameter.name_en} [{record.parameter.unit}]")
        ax.set_ylabel("Mbps")
        ax.grid(alpha=0.3)
    fig.suptitle(
        f"{record.optimization_id} · {record.objective.id} · ■ baseline ● candidate ● best (green) · "
        f"frozen context {record.evaluation_context.context_id if record.evaluation_context else '-'} · "
        "simulation, not measured", fontsize=9)
    fig.savefig(path, dpi=100)


def _per_ue_png(path: Path, record: SystemOptimizationRecord) -> None:
    baseline = record.baseline
    best = next((c for c in record.all_evaluations() if c.candidate_id == record.best_candidate_id), None)
    fig = Figure(figsize=(10, 4.6), layout="constrained")
    ax = fig.subplots()
    if baseline is not None and best is not None:
        ues = list(baseline.per_ue_throughput_mbps)
        x = np.arange(len(ues))
        pid = record.parameter.id
        ax.bar(x - 0.2, [baseline.per_ue_throughput_mbps[u] for u in ues], 0.4, color="#9ca3af",
               label=f"Baseline {pid}={_param(baseline, pid):g}")
        ax.bar(x + 0.2, [best.per_ue_throughput_mbps.get(u, 0.0) for u in ues], 0.4, color="#16a34a",
               label=f"Best ({best.candidate_id}) {pid}={_param(best, pid):g}")
        ax.set_xticks(x, ues)
        ax.legend(fontsize=8)
    ax.set_ylabel("UE_THROUGHPUT_V0_1 [Mbps]")
    ax.grid(axis="y", alpha=0.3)
    ax.set_title(f"{record.optimization_id} · per-UE throughput, baseline vs best under {record.objective.id}",
                 fontsize=10)
    fig.savefig(path, dpi=100)


def algorithm_config(record: SystemOptimizationRecord) -> dict[str, Any]:
    info = record.algorithm
    assert info is not None
    return {
        "algorithm_id": info.algorithm_id,
        "algorithm_version": info.algorithm_version,
        "sdk_version": info.sdk_version,
        "hyperparameters": info.hyperparameters,
        "auto_configured": info.auto_configured,
        "evaluation_budget": record.evaluation_budget.model_dump() if record.evaluation_budget else None,
        "algorithm_config_hash": info.algorithm_config_hash,
        "parameter_space_hash": info.parameter_space_hash,
        "source": info.source,
        "source_revision": info.source_revision,
        "stop_reason": record.stop_reason.value if record.stop_reason else None,
        "recommendation_matches_best": record.recommendation_matches_best,
    }


def export_evidence(
    directory: Path,
    record: SystemOptimizationRecord,
    algorithm_metadata: AlgorithmMetadata | None = None,
    descriptor: EvidenceDescriptor | None = None,
) -> list[SystemOptimizationArtifact]:
    directory.mkdir(parents=True, exist_ok=True)
    refs = []
    if record.evaluation_context is not None:
        _json(directory / EVALUATION_CONTEXT.name, record.evaluation_context.model_dump(mode="json"))
        refs.append(EVALUATION_CONTEXT)
    _json(directory / BENCHMARK_PROTOCOL.name, record.benchmark_protocol.model_dump(mode="json"))
    _json(directory / CANDIDATE_SUMMARY.name, candidate_summary(record))
    _comparison_png(directory / COMPARISON_PNG.name, record)
    _per_ue_png(directory / PER_UE_PNG.name, record)
    refs += [BENCHMARK_PROTOCOL, CANDIDATE_SUMMARY, COMPARISON_PNG, PER_UE_PNG]
    if algorithm_metadata is not None and record.algorithm is not None:
        _json(directory / ALGORITHM_METADATA.name, algorithm_metadata.model_dump(mode="json"))
        refs.append(ALGORITHM_METADATA)
        if record.parameter_space is not None:
            _json(directory / PARAMETER_SPACE.name, record.parameter_space.model_dump(mode="json"))
            refs.append(PARAMETER_SPACE)
        _json(directory / ALGORITHM_CONFIG.name, algorithm_config(record))
        refs.append(ALGORITHM_CONFIG)
        if record.algorithm_trace is not None:
            _json(directory / ALGORITHM_TRACE.name, record.algorithm_trace.model_dump(mode="json"))
            refs.append(ALGORITHM_TRACE)
    if descriptor is not None:
        _json(directory / EVIDENCE_DESCRIPTOR.name, descriptor.model_dump(mode="json"))
        refs.append(EVIDENCE_DESCRIPTOR)
    return refs
