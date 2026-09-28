"""
导出系统级实验参考证据 / Export system experiment reference evidence.

    python scripts/export_system_reference.py EXP-XXXXXXXX [--data-dir data/system_experiments] [--out reference/system]

生成 reference/system/EXP-XXXXXXXX/{README.md, result.json, kpi.json, verification.json, system-summary.png}。
verification.json 由独立复核脚本（不使用平台 KPI 引擎）生成；不复制 slot_trace.npz 等大文件。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from verify_system_experiment import verify

REPO_ROOT = Path(__file__).resolve().parents[1]


def _fmt(v: float | None, digits: int = 2) -> str:
    return "—" if v is None else f"{v:.{digits}f}"


def _readme(record: dict[str, Any], meta: dict[str, Any], report: dict[str, Any]) -> str:
    r = record["result"]
    kpis = {k["metric_id"]: k for k in record["kpis"]}
    sc = meta["scenario"]
    rows = "\n".join(
        f"| {u['ue_id']} | {u['serving_cell_id']} | ({u['position'][0]:.1f}, {u['position'][1]:.1f}) | "
        f"{_fmt(u['mean_channel_gain_db'])} | {_fmt(u['sinr_eff_db_mean'])} | {_fmt(u['mcs_index_mean'], 1)} | "
        f"{u['scheduled_slots']}/{u['acked_slots']} | {u['allocated_re_share'] * 100:.1f}% | "
        f"{u['decoded_bits']:,} | **{_fmt(u['throughput_mbps'], 3)}** |"
        for u in r["ue_results"]
    )
    failed = [c for c in report["checks"] if c["status"] != "PASS"]
    rt = r["runtime"]
    return f"""# System-Level Reference Evidence — {record['experiment_id']}

| 项 / Item | 值 / Value |
|---|---|
| Experiment ID | `{record['experiment_id']}` |
| Commit | `{meta.get('git_commit') or '—'}` |
| Platform Version | {meta.get('platform_version')} |
| Scenario | `{sc['id']}` — {record['scenario_name_zh']} / {record['scenario_name_en']} |
| Backend | `{record['backend']}` ({record['provenance'].get('model_label')}) |
| Sionna Version | {r['provider_versions'].get('sionna')} (sionna-rt {r['provider_versions'].get('sionna-rt')}, torch {r['provider_versions'].get('torch')}) |
| BS / Cell / UE | {sc['bs_count']} / {sc['cell_count']} / {len(r['ue_results'])} |
| Traffic Model | {meta['traffic_model']['type']} · {meta['traffic_model']['direction']} · [A] |
| Scheduler | {r['scheduler'].get('name')} (`{r['scheduler'].get('implementation')}`, β = {r['scheduler'].get('beta')}) |
| Link Adaptation | {r['link_adaptation'].get('name')} (BLER target {r['link_adaptation'].get('bler_target')}, MCS table {r['link_adaptation'].get('mcs_table_index')}) |
| Seed | {record['seed']} |
| Simulated Time | {r['num_slots']} slots × {r['slot_duration_s'] * 1e3:g} ms = {r['simulated_duration_s']:g} s |
| Compute Device (SYS) | {r['compute_device']} |
| Runtime | RT {_fmt(rt['propagation_seconds'])} s · SYS {_fmt(rt['system_seconds'])} s · total {_fmt(rt['total_seconds'])} s |
| **Network Throughput** (`NETWORK_THROUGHPUT_V0_1`) | **{_fmt(kpis['NETWORK_THROUGHPUT_V0_1']['value'], 3)} Mbps** |
| **Average UE Throughput** (`AVG_UE_THROUGHPUT_V0_1`) | **{_fmt(kpis['AVG_UE_THROUGHPUT_V0_1']['value'], 3)} Mbps** |
| **P5 UE Throughput** (`P5_UE_THROUGHPUT_V0_1`) | **{_fmt(kpis['P5_UE_THROUGHPUT_V0_1']['value'], 3)} Mbps** |
| Independent Verification | **{report['overall']}** ({len(report['checks']) - len(failed)}/{len(report['checks'])} checks) |
| Measured | **NO** |
| Huawei Data | **NO** |
| Acceptance Evidence | **NO** |
| Purpose | System-Level Simulation Validation |

> 当前结果来自系统级仿真，不是华为实测网络数据。
> P5 UE Throughput 尚未确认等同于项目验收口径中的“边缘用户速率”。

## Per-UE Results

| UE | Cell | Position (x, y) [m] | Mean Gain [dB] | Eff. SINR [dB] | Mean MCS | Sched/ACK slots | RE share | Decoded bits | Throughput [Mbps] |
|---|---|---|---|---|---|---|---|---|---|
{rows}

UE 吞吐率 = 成功译码比特 / 仿真时长（`UE_THROUGHPUT_V0_1`）；Eff. SINR 与 MCS 为被调度时隙均值。

## Chain

Sionna RT `PathSolver` → CFR → Sionna SYS `PFSchedulerSUMIMO` → `downlink_fair_power_control`
→ RZF precoding + LMMSE post-equalization SINR → `OuterLoopLinkAdaptation` → `PHYAbstraction` (decoded bits / HARQ)
→ platform KPI engine (`src/evaluation/kpi`).

## Files

- `result.json` — canonical `SystemSimulationResult` + KPI results
- `kpi.json` — KPI results with provenance
- `verification.json` — independent recomputation from `slot_trace.npz` (`scripts/verify_system_experiment.py`, does not import the KPI engine)
- `system-summary.png` — network view (BS ▲ / UE ●, no map background) and UE throughput bars

## Determinism

UE positions are fully determined by the seed and Sionna SYS (CPU) is bit-identical for identical channels, but Sionna RT on GPU
shows ~0.003 dB discrete channel-gain drift that OLLA/HARQ amplify; repeated runs of this scenario gave network throughput between
about 130 and 139 Mbps. The numbers above are one real run, not a tuned or averaged value.

## Assumptions

{chr(10).join(f'- {a}' for a in meta.get('assumptions', []))}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data" / "system_experiments")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "reference" / "system")
    args = parser.parse_args()

    exp_dir = args.data_dir / args.experiment_id
    art = exp_dir / "artifacts"
    record = json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8"))
    if record["provenance"].get("source_type") != "simulation":
        print("Refusing to export a non-simulation (test fixture) experiment as reference evidence", file=sys.stderr)
        return 1
    meta = json.loads((art / "metadata.json").read_text(encoding="utf-8"))
    report = verify(exp_dir)

    out = args.out / args.experiment_id
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(art / "result.json", out / "result.json")
    shutil.copyfile(art / "kpi.json", out / "kpi.json")
    shutil.copyfile(art / "system_summary.png", out / "system-summary.png")
    (out / "verification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "README.md").write_text(_readme(record, meta, report), encoding="utf-8")
    print(f"Exported {args.experiment_id} → {out} (verification {report['overall']})")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
