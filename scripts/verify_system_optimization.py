"""
系统级优化独立复核 / Independent verification of a system optimization run.

    python scripts/verify_system_optimization.py OPT-XXXXXXXX \
        [--data-dir data/system_optimizations] [--experiments-dir data/system_experiments] [--out verification.json]

只读取持久化产物：optimization.json、context/channel.npz、每个候选实验的 experiment.json /
config.yaml / result.json / slot_trace.npz。不 import 平台的 KPI 引擎、目标函数或优化服务；
哈希规则、KPI 公式、目标函数与最优选择规则均按文档独立重新实现：

    channel sha256  : 按 key 排序；每个 key 依次写入 key、dtype、JSON shape、C 顺序字节
    UE population   : sha256(JSON{ue_ids, serving_cell_ids, positions}, sort_keys, separators=(",", ":"))
    UE 吞吐率       : Σ decoded_bits[warmup:] / ((num_slots − warmup) × slot_duration) / 1e6
    网络 / 平均 / P5 : Σ / 算术平均 / 手写线性插值百分位
    目标            : NETWORK_THROUGHPUT_MAX_V0_1 = NETWORK_THROUGHPUT_V0_1（maximize）
    最优选择        : 目标值最大；相同时基线参数值优先，其次候选顺序
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_system_experiment import close, manual_percentile_linear  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KPIS = ("NETWORK_THROUGHPUT_V0_1", "AVG_UE_THROUGHPUT_V0_1", "P5_UE_THROUGHPUT_V0_1")
KPI_FIELDS = {"NETWORK_THROUGHPUT_V0_1": "network_throughput_mbps",
              "AVG_UE_THROUGHPUT_V0_1": "average_ue_throughput_mbps",
              "P5_UE_THROUGHPUT_V0_1": "p5_ue_throughput_mbps"}


def channel_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with np.load(path, allow_pickle=False) as data:
        arrays = {k[len("array__"):]: data[k] for k in data.files if k.startswith("array__")}
        for key in sorted(arrays):
            a = np.ascontiguousarray(arrays[key])
            h.update(key.encode())
            h.update(str(a.dtype).encode())
            h.update(json.dumps(list(a.shape)).encode())
            h.update(a.tobytes())
    return h.hexdigest()


def ue_sha256(ue_ids: list[str], cells: list[str], positions: list[list[float]]) -> str:
    payload = {"ue_ids": ue_ids, "serving_cell_ids": cells, "positions": [[float(v) for v in p] for p in positions]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def traffic_sha256(model: dict) -> str:
    return hashlib.sha256(json.dumps(model, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def in_space(definition: dict, value: float) -> bool:
    """按参数定义独立检查取值（离散：属于候选值；连续：位于 bounds 内，含开闭区间）。"""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return False
    if definition["type"] == "discrete" and value not in definition["choices"]:
        return False
    b = definition.get("bounds")
    if b is None:
        return True
    above = value >= b["lower"] if b.get("lower_inclusive", True) else value > b["lower"]
    below = value <= b["upper"] if b.get("upper_inclusive", True) else value < b["upper"]
    return above and below


def recompute_kpis(exp_dir: Path) -> tuple[dict[str, float], dict[str, float], dict]:
    """由 slot_trace.npz 独立复算 UE / 网络 / 平均 / P5 吞吐率。"""
    art = exp_dir / "artifacts"
    result = json.loads((art / "result.json").read_text(encoding="utf-8"))["result"]
    warmup = int(result.get("warmup_slots", 0))
    num_slots = int(result["num_slots"])
    duration = (num_slots - warmup) * float(result["slot_duration_s"])
    with np.load(art / "slot_trace.npz", allow_pickle=False) as trace:
        ue_ids = [str(x) for x in trace["ue_ids"]]
        bits = trace["decoded_bits"][warmup:]
    per_ue = {u: float(bits[:, j].sum()) / duration / 1e6 for j, u in enumerate(ue_ids)}
    values = list(per_ue.values())
    kpis = {"NETWORK_THROUGHPUT_V0_1": sum(values), "AVG_UE_THROUGHPUT_V0_1": sum(values) / len(values),
            "P5_UE_THROUGHPUT_V0_1": manual_percentile_linear(values, 5.0)}
    return kpis, per_ue, result


def verify(opt_dir: Path, experiments_dir: Path) -> dict:
    record = json.loads((opt_dir / "optimization.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    opt_id = record["optimization_id"]
    ctx = record["evaluation_context"]
    pid = record["parameter"]["id"]
    baseline = record["baseline"]
    candidates = record["candidates"]
    evaluations = [baseline, *candidates] if baseline else candidates

    check("status_succeeded", record["status"] == "succeeded", record["status"])
    check("baseline_exists", baseline is not None and baseline["status"] == "evaluated",
          baseline["candidate_id"] if baseline else "missing")
    check("candidates_exist", len(candidates) > 0, f"{len(candidates)} candidates")
    cand_values = [c["parameters"][pid] for c in candidates]
    space = record.get("parameter_space")
    budget = record.get("evaluation_budget")
    if space is None:  # Day 6 记录：Grid Search 按候选列表逐个评价
        check("candidate_count", len(candidates) == len(record["candidate_values"]),
              f"{len(candidates)} vs candidate_values {record['candidate_values']}")
        values_ok = cand_values == record["candidate_values"]
    else:  # Day 7：候选由算法生成，必须位于参数空间内且不超过平台预算
        (definition,) = [p for p in space["parameters"] if p["id"] == pid]
        check("candidate_count", budget is not None and len(candidates) == budget["evaluations_used"]
              <= budget["max_evaluations"],
              f"{len(candidates)} candidates, budget used {budget and budget['evaluations_used']}"
              f"/{budget and budget['max_evaluations']}")
        values_ok = all(in_space(definition, v) for v in cand_values)
        if definition["type"] == "discrete" and len(candidates) == len(definition["choices"]):
            values_ok = values_ok and cand_values == definition["choices"]
    check("parameter_values", values_ok and baseline["parameters"] == record["baseline_parameters"],
          f"{pid}: baseline {baseline['parameters'][pid]}, candidates {cand_values}")
    ids = [c["candidate_id"] for c in evaluations]
    check("unique_candidate_ids", len(set(ids)) == len(ids), ", ".join(ids))

    # 冻结上下文本身
    channel_file = opt_dir / "context" / ctx["channel_realization"]["artifact"]
    recomputed_channel = channel_sha256(channel_file)
    check("channel_artifact_hash", recomputed_channel == ctx["channel_realization"]["sha256"],
          f"recomputed {recomputed_channel[:16]}… vs context {ctx['channel_realization']['sha256'][:16]}…")
    ctx_ues = ctx["ue_population"]["ues"]
    ctx_ue_hash = ue_sha256([u["ue_id"] for u in ctx_ues], [u["serving_cell_id"] for u in ctx_ues],
                            [u["position"] for u in ctx_ues])
    check("context_ue_hash", ctx_ue_hash == ctx["ue_population"]["sha256"], ctx["ue_population"]["ue_population_id"])
    check("context_traffic_hash", traffic_sha256(ctx["traffic_realization"]["model"])
          == ctx["traffic_realization"]["sha256"], ctx["traffic_realization"]["traffic_realization_id"])

    independent: dict[str, dict] = {}
    gains_seen: list[dict] = []
    for c in evaluations:
        cid = c["candidate_id"]
        if c["status"] != "evaluated":
            check(f"{cid}.failed_preserved", bool(c.get("error")) and c.get("objective") is None,
                  f"status={c['status']} error={c.get('error', {}).get('code') if c.get('error') else None}")
            continue
        exp_ids = c["experiment_ids"]
        values: dict[str, list[float]] = {k: [] for k in KPIS}
        per_ue_all: dict[str, list[float]] = {}
        for exp_id in exp_ids:
            exp_dir = experiments_dir / exp_id
            exp = json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8"))
            config = yaml.safe_load((exp_dir / "artifacts" / "config.yaml").read_text(encoding="utf-8"))
            kpis, per_ue, result = recompute_kpis(exp_dir)
            link = exp.get("evaluation_context") or {}
            expected_cid = c.get("reused_candidate_id") or (baseline["candidate_id"] if c.get("reused_baseline")
                                                             else cid)
            check(f"{cid}.{exp_id}.experiment_link",
                  exp["optimization_id"] == opt_id and exp["optimization_candidate_id"] == expected_cid
                  and exp["status"] == "succeeded",
                  f"optimization_id={exp['optimization_id']} candidate={exp['optimization_candidate_id']}")
            check(f"{cid}.{exp_id}.context_id",
                  c["evaluation_context_id"] == ctx["context_id"] == link.get("evaluation_context_id"),
                  f"{link.get('evaluation_context_id')}")
            check(f"{cid}.{exp_id}.parameter_applied",
                  config["simulation"]["scheduler"]["beta"] == c["parameters"][pid] == result["scheduler"]["beta"],
                  f"config β={config['simulation']['scheduler']['beta']} result β={result['scheduler']['beta']}")
            ues = result["ue_results"]
            check(f"{cid}.{exp_id}.same_ue_hash",
                  ue_sha256([u["ue_id"] for u in ues], [u["serving_cell_id"] for u in ues],
                            [u["position"] for u in ues]) == ctx["ue_population"]["sha256"], "recomputed from result")
            gains = {u["ue_id"]: u["mean_channel_gain_db"] for u in ues}
            gains_seen.append(gains)
            check(f"{cid}.{exp_id}.same_channel",
                  link.get("channel_sha256") == ctx["channel_realization"]["sha256"] == recomputed_channel
                  and link.get("channel_realization_id") == ctx["channel_realization"]["channel_realization_id"]
                  and result.get("channel_reused") is True
                  and gains == ctx["channel_realization"]["mean_channel_gain_db"],
                  f"{link.get('channel_realization_id')} reused={result.get('channel_reused')} gains identical")
            check(f"{cid}.{exp_id}.same_traffic",
                  traffic_sha256(config["traffic"]) == ctx["traffic_realization"]["sha256"], str(config["traffic"]))
            horizon = ctx["simulation_horizon"]
            check(f"{cid}.{exp_id}.same_slots",
                  config["simulation"]["num_slots"] == result["num_slots"] == horizon["num_slots"]
                  and int(result.get("warmup_slots", 0)) == horizon["warmup_slots"]
                  == config["simulation"].get("warmup_slots", 0),
                  f"{result['num_slots']} slots, warm-up {result.get('warmup_slots', 0)}")
            check(f"{cid}.{exp_id}.same_backend",
                  exp["backend"] == ctx["backend_id"] and exp["backend_version"] == ctx["backend_version"],
                  f"{exp['backend']} {exp['backend_version']}")
            for k in KPIS:
                values[k].append(kpis[k])
            for u, v in per_ue.items():
                per_ue_all.setdefault(u, []).append(v)
        means = {k: sum(v) / len(v) for k, v in values.items()}
        independent[cid] = {"kpis": means, "per_ue": {u: sum(v) / len(v) for u, v in per_ue_all.items()},
                            "parameters": c["parameters"], "iteration": c["iteration"]}
        for k, field in KPI_FIELDS.items():
            check(f"{cid}.{k}", close(means[k], c[field]["mean"]),
                  f"independent {means[k]:.6f} vs record {c[field]['mean']:.6f}")
        objective = means["NETWORK_THROUGHPUT_V0_1"]
        check(f"{cid}.objective", close(objective, c["objective"]["value"]),
              f"J = network throughput = {objective:.6f} vs record {c['objective']['value']:.6f}")

    check("channel_gains_identical_across_evaluations", all(g == gains_seen[0] for g in gains_seen),
          f"{len(gains_seen)} experiments")

    # 最优选择（独立实现的规则）
    base_params = record["baseline_parameters"]

    def key(cid: str) -> tuple[float, float, float]:
        e = independent[cid]
        return (e["kpis"]["NETWORK_THROUGHPUT_V0_1"], 1.0 if e["parameters"] == base_params else 0.0,
                -float(e["iteration"]))

    best_id = max(independent, key=key)
    check("best_candidate_selection", best_id == record["best_candidate_id"],
          f"independent {best_id} vs record {record['best_candidate_id']}")

    comp = record["comparison"]
    b = independent[baseline["candidate_id"]]["kpis"]
    w = independent[best_id]["kpis"]
    absolute = w["NETWORK_THROUGHPUT_V0_1"] - b["NETWORK_THROUGHPUT_V0_1"]
    relative = None if abs(b["NETWORK_THROUGHPUT_V0_1"]) < 1e-9 else absolute / abs(b["NETWORK_THROUGHPUT_V0_1"]) * 100
    check("absolute_improvement", close(absolute, comp["absolute_improvement"]),
          f"independent {absolute:+.6f} vs record {comp['absolute_improvement']:+.6f} Mbps")
    check("relative_improvement", (relative is None and comp["relative_improvement_percent"] is None)
          or close(relative, comp["relative_improvement_percent"]),
          f"independent {relative:+.4f}% vs record {comp['relative_improvement_percent']}")
    negatives = [k for k in KPIS if w[k] < b[k]]
    recorded_dirs = {c["kpi_id"]: c["direction"] for c in comp["kpi_changes"]}
    check("negative_kpi_changes_preserved",
          negatives == comp["negative_kpi_changes"] and all(recorded_dirs[k] == "decrease" for k in negatives),
          f"independent decreases {negatives} vs record {comp['negative_kpi_changes']}")
    for k in KPIS:
        rec = next(c for c in comp["kpi_changes"] if c["kpi_id"] == k)
        check(f"comparison.{k}", close(rec["baseline"], b[k]) and close(rec["best"], w[k]),
              f"baseline {b[k]:.4f} → best {w[k]:.4f} Mbps")

    prov = record["provenance"]
    check("provenance", prov.get("measured") is False and prov.get("huawei_data") is False
          and prov.get("acceptance_evidence") is False and prov.get("learning_algorithm") is False
          and prov.get("optimizer") == record["optimizer_id"]
          and prov.get("evaluation_context") == ctx["context_id"],
          f"source_type={prov.get('source_type')} learning_algorithm={prov.get('learning_algorithm')}")
    check("not_test_fixture", prov.get("source_type") == "simulation" and prov.get("model_type") != "test_fixture",
          str(prov.get("model_type")))
    check("recorded_fairness_all_pass", bool(record.get("fairness")) and record["fairness"]["fair"] is True,
          ", ".join(f"{c['id']}={'PASS' if c['passed'] else 'FAIL'}" for c in (record.get("fairness") or {})
                    .get("checks", [])))

    passed = all(c["status"] == "PASS" for c in checks)
    return {
        "optimization_id": opt_id,
        "verifier": "scripts/verify_system_optimization.py (independent; does not import evaluation.kpi, "
                    "system_optimization or optimization)",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "overall": "PASS" if passed else "FAIL",
        "independent": {
            "best_candidate_id": best_id,
            "baseline": independent[baseline["candidate_id"]],
            "best": independent[best_id],
            "absolute_improvement_mbps": absolute,
            "relative_improvement_percent": relative,
            "candidates": independent,
            "channel_sha256": recomputed_channel,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("optimization_id")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "system_optimizations")
    parser.add_argument("--experiments-dir", type=Path, default=ROOT / "data" / "system_experiments")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = verify(args.data_dir / args.optimization_id, args.experiments_dir)
    for c in report["checks"]:
        if c["status"] != "PASS":
            print(f"FAIL {c['check']}: {c['detail']}")
    n_pass = sum(c["status"] == "PASS" for c in report["checks"])
    print(f"{report['optimization_id']}: {report['overall']} ({n_pass}/{len(report['checks'])} checks)")
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
