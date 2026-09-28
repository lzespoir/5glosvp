"""
导出系统级优化参考证据 / Export a system optimization run as reference evidence.

    python scripts/export_system_optimization_reference.py OPT-XXXXXXXX \
        [--data-dir data/system_optimizations] [--experiments-dir data/system_experiments] \
        [--out reference/system_optimization]

复制持久化产物（optimization.json 与 artifacts/*），运行独立复核脚本生成 verification.json，
并按 Day 6 §89 写 README.md。只读取 JSON，不重新计算任何 KPI。已存在的参考目录不会被覆盖。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPIED_ARTIFACTS = (
    "evaluation-context.json",
    "benchmark-protocol.json",
    "candidate-summary.json",
    "comparison.png",
    "per-ue-comparison.png",
)
NETWORK = "NETWORK_THROUGHPUT_V0_1"
P5 = "P5_UE_THROUGHPUT_V0_1"
AVG = "AVG_UE_THROUGHPUT_V0_1"


def yes(flag: bool) -> str:
    return "YES" if flag else "NO"


def fmt(v: float | None, digits: int = 3) -> str:
    return "—" if v is None else f"{v:.{digits}f}"


def signed(v: float | None, digits: int = 3, suffix: str = "") -> str:
    return "—" if v is None else f"{v:+.{digits}f}{suffix}"


def bounds(b: dict | None) -> str:
    if not b:
        return "—"
    return f"{'[' if b['lower_inclusive'] else '('}{b['lower']}, {b['upper']}{']' if b['upper_inclusive'] else ')'}"


def readme(record: dict, verification: dict) -> str:
    comp = record["comparison"]
    ctx = record["evaluation_context"]
    proto = record["benchmark_protocol"]
    prov = record["provenance"]
    pid = record["parameter"]["id"]
    fair = {c["id"]: c["passed"] for c in record["fairness"]["checks"]}
    changes = {c["kpi_id"]: c for c in comp["kpi_changes"]}
    candidates = [record["baseline"], *record["candidates"]]
    n_pass = sum(c["status"] == "PASS" for c in verification["checks"])

    rows = []
    for c in candidates:
        tags = [t for t, on in (("baseline", c["is_baseline"]), ("best", c["candidate_id"] == comp["best_candidate_id"]),
                                ("reused baseline", c.get("reused_baseline"))) if on]
        net = c["network_throughput_mbps"]["mean"] if c["network_throughput_mbps"] else None
        avg = c["average_ue_throughput_mbps"]["mean"] if c["average_ue_throughput_mbps"] else None
        p5 = c["p5_ue_throughput_mbps"]["mean"] if c["p5_ue_throughput_mbps"] else None
        rows.append(f"| {c['candidate_id']} {'(' + ', '.join(tags) + ')' if tags else ''} | {c['parameters'][pid]} | "
                    f"{', '.join(c['experiment_ids']) or '—'} | {fmt(net)} | {fmt(avg)} | {fmt(p5)} | "
                    f"{fmt(c['runtime_seconds'], 1)} | {c['status']} |")

    base_ue = record["baseline"]["per_ue_throughput_mbps"]
    best = next(c for c in candidates if c["candidate_id"] == comp["best_candidate_id"])
    ue_rows = [f"| {u} | {fmt(v)} | {fmt(best['per_ue_throughput_mbps'].get(u))} | "
               f"{signed(best['per_ue_throughput_mbps'].get(u, 0.0) - v)} |" for u, v in base_ue.items()]

    kpi_rows = [f"| {k} | {fmt(changes[k]['baseline'])} | {fmt(changes[k]['best'])} | {signed(changes[k]['absolute_change'])} | "
                f"{signed(changes[k]['relative_change_percent'], 2, '%')} | {changes[k]['direction']} |" for k in (NETWORK, AVG, P5)]

    outcome = (f"在当前冻结仿真协议下，网络吞吐率提高 {comp['relative_improvement_percent']:.2f}%"
               if comp["improved"] else "当前候选范围内未发现优于基线的配置。 / No candidate improved the objective.")

    return f"""# System Optimization Reference — {record['optimization_id']}

> 当前结果来自系统级仿真优化验证，不是华为实测网络优化结果。
> Grid Search 为工程基线优化器，不属于项目学习优化算法。

**Outcome:** {outcome}

| Field | Value |
|---|---|
| Optimization ID | `{record['optimization_id']}` |
| Commit | `{prov.get('git_commit')}` |
| Scenario | `{record['scenario_id']}` ({record['scenario_name_en']}) |
| Backend | `{record['backend_id']}` ({prov.get('model_label')}) |
| Backend Version | {prov.get('backend_version')} |
| Optimizer | `{record['optimizer_id']}` v{record['optimizer_version']} ({prov.get('optimizer_category')}) |
| Learning Algorithm | {yes(bool(prov.get('learning_algorithm')))} |
| Objective | `{record['objective']['id']}` v{record['objective']['version']} ({record['objective']['direction']}) |
| Optimization Variable | `{pid}` ({record['parameter']['name_en']}, bounds {bounds(record['parameter']['bounds'])}) |
| Baseline Parameter | {pid} = {comp['baseline_parameters'][pid]} |
| Candidate Values | {', '.join(str(v) for v in record['candidate_values'])} |
| Best Parameter | {pid} = {comp['best_parameters'][pid]} (`{comp['best_candidate_id']}`) |
| Baseline Network Throughput | {fmt(changes[NETWORK]['baseline'])} Mbps (`{comp['baseline_experiment_id']}`) |
| Best Network Throughput | {fmt(changes[NETWORK]['best'])} Mbps (`{comp['best_experiment_id']}`) |
| Absolute Improvement | {signed(comp['absolute_improvement'])} Mbps |
| Relative Improvement | {signed(comp['relative_improvement_percent'], 2, '%')} |
| Baseline P5 | {fmt(changes[P5]['baseline'])} Mbps |
| Best P5 | {fmt(changes[P5]['best'])} Mbps ({changes[P5]['direction']}) |
| Benchmark Protocol | `{proto['protocol_id']}` v{proto['version']} (frozen {proto['frozen_at']}) |
| Simulation Slots | {proto['simulation_slots']} |
| Warmup | {proto['warmup_slots']} |
| Repeat Count | {proto['num_repeats']} ({proto['aggregation_method']}) |
| Same UE | {yes(fair.get('same_ue_population', False))} |
| Same Channel | {yes(fair.get('same_channel_realization', False))} |
| Same Traffic | {yes(fair.get('same_traffic', False))} |
| Same Horizon / Backend / Only Variable Changed | {yes(fair.get('same_simulation_horizon', False))} / {yes(fair.get('same_backend_version', False))} / {yes(fair.get('only_variable_changed', False))} |
| Measured | {yes(bool(prov.get('measured')))} |
| Huawei | {yes(bool(prov.get('huawei_data')))} |
| Acceptance | {yes(bool(prov.get('acceptance_evidence')))} |
| Independent verification | **{verification['overall']}** ({n_pass}/{len(verification['checks'])} checks) |

## Common evaluation context

| Item | ID | sha256 |
|---|---|---|
| Context | `{ctx['context_id']}` | — |
| UE population ({len(ctx['ue_population']['ues'])} UEs) | `{ctx['ue_population']['ue_population_id']}` | `{ctx['ue_population']['sha256']}` |
| Channel realization | `{ctx['channel_realization']['channel_realization_id']}` | `{ctx['channel_realization']['sha256']}` |
| Traffic | `{ctx['traffic_realization']['traffic_realization_id']}` | `{ctx['traffic_realization']['sha256']}` |
| Scenario version | — | `{ctx['scenario_version']}` |

Channel hash rule: {ctx['channel_realization']['hash_rule']}.

## KPI changes (baseline → best)

| KPI | Baseline (Mbps) | Best (Mbps) | Δ (Mbps) | Δ % | Direction |
|---|---|---|---|---|---|
{chr(10).join(kpi_rows)}

Negative KPI changes: {', '.join(comp['negative_kpi_changes']) or 'none'}.
Within observed variability (±{comp['observed_variability_percent']}%): {yes(comp['within_observed_variability'])}.
Tie-break rule: {comp['tie_break_rule']}.

## Candidates

| Candidate | {pid} | Experiment | Network (Mbps) | Average (Mbps) | P5 (Mbps) | Runtime (s) | Status |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Per-UE throughput (baseline → best, Mbps)

| UE | Baseline | Best | Δ |
|---|---|---|---|
{chr(10).join(ue_rows)}

![Comparison](comparison.png)

![Per-UE comparison](per-ue-comparison.png)

## Warnings

{chr(10).join('- ' + w for w in record['warnings']) or '- none'}

## Files

- `optimization.json` — full persisted record (context, candidates, comparison, fairness, provenance).
- `evaluation-context.json`, `benchmark-protocol.json`, `candidate-summary.json` — exported by the backend.
- `verification.json` — `scripts/verify_system_optimization.py` (independent recomputation from slot traces).
- `comparison.png`, `per-ue-comparison.png` — backend-rendered plots.
- `screenshots/` — browser smoke screenshots 01–08.

Runtime: context {fmt(record['runtime']['context_seconds'], 1)} s, baseline {fmt(record['runtime']['baseline_seconds'], 1)} s,
candidates {fmt(record['runtime']['candidate_evaluation_seconds'], 1)} s, total {fmt(record['runtime']['total_seconds'], 1)} s
(platform runtime, not an acceptance KPI).
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("optimization_id")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "system_optimizations")
    parser.add_argument("--experiments-dir", type=Path, default=ROOT / "data" / "system_experiments")
    parser.add_argument("--out", type=Path, default=ROOT / "reference" / "system_optimization")
    args = parser.parse_args()

    src = args.data_dir / args.optimization_id
    dst = args.out / args.optimization_id
    if (dst / "README.md").exists():
        print(f"{dst} already exported; refusing to overwrite reference evidence", file=sys.stderr)
        return 1
    record = json.loads((src / "optimization.json").read_text(encoding="utf-8"))
    if record["status"] != "succeeded":
        print(f"{args.optimization_id} status={record['status']}; only succeeded runs are exported", file=sys.stderr)
        return 1
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "optimization.json", dst / "optimization.json")
    for name in COPIED_ARTIFACTS:
        shutil.copy2(src / "artifacts" / name, dst / name)

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_system_optimization.py"), args.optimization_id,
         "--data-dir", str(args.data_dir), "--experiments-dir", str(args.experiments_dir),
         "--out", str(dst / "verification.json")],
        capture_output=True, text=True, check=False,
    )
    print(proc.stdout.strip())
    verification = json.loads((dst / "verification.json").read_text(encoding="utf-8"))
    (dst / "README.md").write_text(readme(record, verification), encoding="utf-8")
    print(f"wrote {dst}")
    return 0 if verification["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
