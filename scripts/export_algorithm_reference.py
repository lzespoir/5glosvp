"""
导出算法接入参考证据 / Export an algorithm-driven system optimization as reference evidence (Day 7).

    python scripts/export_algorithm_reference.py OPT-XXXXXXXX \
        [--data-dir data/system_optimizations] [--experiments-dir data/system_experiments] \
        [--out reference/algorithm_integration]

复制持久化产物（optimization.json 与算法 / 上下文 artifacts），运行 scripts/verify_algorithm_run.py 生成
verification.json，并按 Day 7 §92 写 README.md。只读取 JSON，不重新计算任何 KPI。
evidence-descriptor.json 记录独立复核结果；acceptance_eligible 始终为 false（复核 ≠ 验收）。
已存在的参考目录不会被覆盖。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_system_optimization_reference import AVG, NETWORK, P5, bounds, fmt, signed, yes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATEGORY_NOTICE_ZH = {
    "engineering_baseline": "Grid Search 为工程基线优化器，不属于项目学习优化算法。",
    "research_demo": "Research Demo Optimizer 为算法接入验证算法，不是项目科研成果，也不是学习优化算法。",
    "research": "科研算法结果仍为仿真验证结果，不构成验收结论。",
    "external": "科研算法结果仍为仿真验证结果，不构成验收结论。",
}
COPIED_ARTIFACTS = (
    "algorithm-metadata.json",
    "parameter-space.json",
    "algorithm-config.json",
    "algorithm-trace.json",
    "evaluation-context.json",
    "benchmark-protocol.json",
    "candidate-summary.json",
    "comparison.png",
    "per-ue-comparison.png",
)


def space_text(space: dict) -> str:
    parts = []
    for p in space["parameters"]:
        domain = f"{{{', '.join(str(c) for c in p['choices'])}}}" if p["type"] == "discrete" else bounds(p["bounds"])
        parts.append(f"`{p['id']}` {p['type']} {domain} (unit {p['unit']})")
    return "; ".join(parts)


def readme(record: dict, verification: dict, meta: dict, code_commit: str | None) -> str:
    info = record["algorithm"]
    trace = record["algorithm_trace"]
    budget = record["evaluation_budget"]
    comp = record["comparison"]
    ctx = record["evaluation_context"]
    proto = record["benchmark_protocol"]
    prov = record["provenance"]
    pid = record["parameter"]["id"]
    rt = record["runtime"]
    fair = record["fairness"]["checks"]
    changes = {c["kpi_id"]: c for c in comp["kpi_changes"]}
    candidates = [record["baseline"], *record["candidates"]]
    by_id = {c["candidate_id"]: c for c in candidates}
    n_pass = sum(c["status"] == "PASS" for c in verification["checks"])
    n_alg = [c for c in verification["checks"] if c["check"].startswith("algorithm.")]
    replay = verification.get("algorithm", {}).get("replay") or {}

    rows = []
    for c in candidates:
        flags = (("baseline", c["is_baseline"]), ("best", c["candidate_id"] == comp["best_candidate_id"]),
                 (f"cache hit → {c.get('reused_candidate_id')}", c.get("cache_hit")))
        tags = [t for t, on in flags if on]
        net = c["network_throughput_mbps"]["mean"] if c["network_throughput_mbps"] else None
        p5 = c["p5_ue_throughput_mbps"]["mean"] if c["p5_ue_throughput_mbps"] else None
        rnd = 0 if c["is_baseline"] else c.get("algorithm_round")
        label = f"{c['candidate_id']} ({', '.join(tags)})" if tags else c["candidate_id"]
        rows.append(f"| {label} | {rnd} | "
                    f"{c['parameters'][pid]} | {', '.join(c['experiment_ids']) or '—'} | {fmt(net)} | {fmt(p5)} | "
                    f"{fmt(c['runtime_seconds'], 1)} | {c['status']} |")

    round_rows = []
    for r in trace["rounds"]:
        sug = ", ".join(str(s[pid]) for s in r["suggestions"])
        rej = ", ".join(str(s[pid]) for s in r["rejected_suggestions"]) or "—"
        before = r["state_before"]
        round_rows.append(f"| {r['round']} | {before.get('mode', '—')} · x={before.get('incumbent', '—')} · "
                          f"step={before.get('step', '—')} | {sug} | {', '.join(r['evaluated_candidate_ids'])} | "
                          f"{rej} | {r['state_after'].get('last_decision', '—')} |")

    trace_rows = [f"| {e['sequence']} | {e['round']} | {e['candidate_id']} | {e['parameters'][pid]} | "
                  f"{fmt(e['objective'])} | {'yes' if e['cache_hit'] else 'no'} | {e['best_so_far_candidate_id']} |"
                  for e in trace["evaluations"]]

    fair_rows = [f"| {c['label_en']} | {'PASS' if c['passed'] else 'FAIL'} | {c['detail']} |" for c in fair]
    hp = ", ".join(f"{k} = {v}" for k, v in info["hyperparameters"].items()) or "none"
    best = by_id[comp["best_candidate_id"]]
    rec = (trace.get("recommendation") or {}).get("parameters")
    outcome = (f"在当前冻结仿真协议下，网络吞吐率提高 {comp['relative_improvement_percent']:.2f}%"
               if comp["improved"] else "当前候选范围内未发现优于基线的配置。 / No candidate improved the objective.")

    return f"""# Algorithm Integration Reference — {record['optimization_id']}

> 当前结果来自系统级仿真优化验证，不是华为实测网络优化结果。
> {CATEGORY_NOTICE_ZH[info['algorithm_category']]}
> 本运行用于证明算法接入框架（suggest → evaluate → observe）可用；不要求优于 Grid Search，不用于验收。
> 独立复核 PASS ≠ 验收 PASS。

**Outcome (simulation only):** {outcome}

| Field | Value |
|---|---|
| Optimization ID | `{record['optimization_id']}` |
| Algorithm ID | `{info['algorithm_id']}` |
| Algorithm Version | {info['algorithm_version']} |
| SDK Version | {info['sdk_version']} |
| Category | {info['algorithm_category']} ({', '.join(meta.get('labels', []))}) |
| Learning Algorithm | {yes(info['learning_algorithm'])} |
| Purpose | {info['purpose_zh']} / {info['purpose_en']} |
| Provider | {info['algorithm_provider']} |
| Source | `{info['source']}` @ `{info['source_revision'].get('value')}` |
{f"| Code Commit | `{code_commit}` (run executed from the uncommitted Day 7 working tree; committed in this commit) |{chr(10)}"
 if code_commit else ""}| Algorithm Config Hash | `{info['algorithm_config_hash']}` |
| Parameter Space Hash | `{info['parameter_space_hash']}` |
| Scenario | `{record['scenario_id']}` ({record['scenario_name_en']}) |
| Backend | `{record['backend_id']}` {prov.get('backend_version')} ({prov.get('model_label')}) |
| Benchmark Protocol | `{proto['protocol_id']}` v{proto['version']} ({proto['simulation_slots']} slots, warm-up \
{proto['warmup_slots']}, {proto['num_repeats']} × {proto['aggregation_method']}) |
| Objective | `{record['objective']['id']}` v{record['objective']['version']} ({record['objective']['direction']}) |
| Parameter Space | {space_text(record['parameter_space'])} |
| Search Space Source | {prov.get('search_space_source')} |
| Hyperparameters | {hp} ({'Recommended / auto-configured' if info['auto_configured'] else 'Advanced'}) |
| Evaluation Budget | {budget['max_evaluations']} |
| Evaluations Used | {budget['evaluations_used']} (simulations {budget['simulations_run']}, cache hits \
{budget['cache_hits']}, rejected suggestions {budget['rejected_suggestions']}) |
| Stop Reason | `{record['stop_reason']}` — {trace['stop_detail']} |
| Algorithm Recommendation | {pid} = {rec.get(pid) if rec else '—'} (matches platform best: \
{yes(bool(record.get('recommendation_matches_best')))}) |
| Baseline | {pid} = {comp['baseline_parameters'][pid]} (`{comp['baseline_experiment_id']}`) |
| Best Candidate | `{comp['best_candidate_id']}`: {pid} = {comp['best_parameters'][pid]} \
(`{comp['best_experiment_id']}`) |
| Network Throughput | {fmt(changes[NETWORK]['baseline'])} → {fmt(changes[NETWORK]['best'])} Mbps \
({signed(changes[NETWORK]['relative_change_percent'], 2, '%')}) |
| Average UE Throughput | {fmt(changes[AVG]['baseline'])} → {fmt(changes[AVG]['best'])} Mbps \
({signed(changes[AVG]['relative_change_percent'], 2, '%')}) |
| P5 Throughput | {fmt(changes[P5]['baseline'])} → {fmt(changes[P5]['best'])} Mbps \
({signed(changes[P5]['relative_change_percent'], 2, '%')}, {changes[P5]['direction']}) |
| Fairness Checks | {'ALL PASS' if record['fairness']['fair'] else 'FAIL'} ({len(fair)} checks) |
| Independent verification | **{verification['overall']}** ({n_pass}/{len(verification['checks'])} checks, \
{len(n_alg)} algorithm-level; decision replay {'reproduced' if replay and not replay.get('mismatches') else 'n/a'}) |
| Measured | NO |
| Huawei | NO |
| Acceptance | NO |
| Project Research Deliverable | {yes(info['project_research_deliverable'])} |

P5 is the 5th-percentile UE throughput of this simulated UE population; it is **not** an edge-user acceptance rate.

## Algorithm rounds (suggest → evaluate → observe)

| Round | State before | Suggestions ({pid}) | Evaluated | Rejected by budget | Decision (algorithm state) |
|---|---|---|---|---|---|
{chr(10).join(round_rows)}

## Algorithm trace

| # | Round | Candidate | {pid} | Objective (Mbps) | Cache hit | Best so far |
|---|---|---|---|---|---|---|
{chr(10).join(trace_rows)}

Best-so-far uses the platform rule: objective (direction-normalized) first, then the baseline value,
then candidate order.

## Candidates → experiments

| Candidate | Round | {pid} | Experiment | Network (Mbps) | P5 (Mbps) | Runtime (s) | Status |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Fair evaluation

| Check | Result | Detail |
|---|---|---|
{chr(10).join(fair_rows)}

Common evaluation context `{ctx['context_id']}`: UE population `{ctx['ue_population']['ue_population_id']}`
({len(ctx['ue_population']['ues'])} UEs), channel `{ctx['channel_realization']['channel_realization_id']}`
(`{ctx['channel_realization']['sha256']}`), traffic `{ctx['traffic_realization']['traffic_realization_id']}`.

## Per-UE throughput (baseline → best, Mbps)

| UE | Baseline | Best | Δ |
|---|---|---|---|
{chr(10).join(f"| {u} | {fmt(v)} | {fmt(best['per_ue_throughput_mbps'].get(u))} | "
              f"{signed(best['per_ue_throughput_mbps'].get(u, 0.0) - v)} |"
              for u, v in record['baseline']['per_ue_throughput_mbps'].items())}

![Comparison](comparison.png)

![Per-UE comparison](per-ue-comparison.png)

## Warnings

{chr(10).join('- ' + w for w in record['warnings']) or '- none'}

## Files

- `optimization.json` — full persisted record (algorithm provenance, parameter space, budget, trace, candidates).
- `algorithm-metadata.json`, `parameter-space.json`, `algorithm-config.json`, `algorithm-trace.json`
  — algorithm evidence.
- `evaluation-context.json`, `benchmark-protocol.json`, `candidate-summary.json` — exported by the backend.
- `evidence-descriptor.json` — verification status (independent) and acceptance eligibility (always false).
- `verification.json` — `scripts/verify_algorithm_run.py` (independent; imports nothing from `src/`).
- `screenshots/` — browser smoke screenshots.

Runtime: context {fmt(rt['context_seconds'], 1)} s, baseline {fmt(rt['baseline_seconds'], 1)} s,
candidates {fmt(rt['candidate_evaluation_seconds'], 1)} s, total {fmt(rt['total_seconds'], 1)} s
(platform runtime, not an acceptance KPI).
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("optimization_id")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "system_optimizations")
    parser.add_argument("--experiments-dir", type=Path, default=ROOT / "data" / "system_experiments")
    parser.add_argument("--out", type=Path, default=ROOT / "reference" / "algorithm_integration")
    parser.add_argument("--code-commit", help="commit that contains the code of a run recorded as '<rev>-dirty'")
    args = parser.parse_args()

    src = args.data_dir / args.optimization_id
    dst = args.out / args.optimization_id
    if (dst / "README.md").exists():
        print(f"{dst} already exported; refusing to overwrite reference evidence", file=sys.stderr)
        return 1
    record = json.loads((src / "optimization.json").read_text(encoding="utf-8"))
    if record["status"] != "succeeded" or record.get("algorithm") is None:
        print(f"{args.optimization_id}: only succeeded algorithm runs are exported", file=sys.stderr)
        return 1
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "optimization.json", dst / "optimization.json")
    for name in COPIED_ARTIFACTS:
        shutil.copy2(src / "artifacts" / name, dst / name)

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_algorithm_run.py"), args.optimization_id,
         "--data-dir", str(args.data_dir), "--experiments-dir", str(args.experiments_dir),
         "--out", str(dst / "verification.json")],
        capture_output=True, text=True, check=False,
    )
    print(proc.stdout.strip())
    verification = json.loads((dst / "verification.json").read_text(encoding="utf-8"))
    passed = verification["overall"] == "PASS"
    n_pass = sum(c["status"] == "PASS" for c in verification["checks"])

    descriptor = json.loads((src / "artifacts" / "evidence-descriptor.json").read_text(encoding="utf-8"))
    descriptor["verification_status"] = "independently_verified" if passed else "independent_verification_failed"
    descriptor["verification_detail"] = (f"scripts/verify_algorithm_run.py: {verification['overall']} "
                                         f"({n_pass}/{len(verification['checks'])} checks)")
    descriptor["verified"] = passed
    descriptor["acceptance_eligible"] = False
    (dst / "evidence-descriptor.json").write_text(json.dumps(descriptor, indent=2, ensure_ascii=False),
                                                  encoding="utf-8")

    meta = json.loads((src / "artifacts" / "algorithm-metadata.json").read_text(encoding="utf-8"))
    (dst / "README.md").write_text(readme(record, verification, meta, args.code_commit), encoding="utf-8")
    print(f"wrote {dst}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
