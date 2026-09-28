"""
系统级实验独立复核 / Independent verification of a system experiment.

    python scripts/verify_system_experiment.py data/system_experiments/EXP-XXXXXXXX [--out verification.json]

只读取实验产物（slot_trace.npz、ue_results.json、kpi.json、result.json），
不 import 平台的 KPI 引擎（evaluation.kpi），用独立实现复算：
    UE 吞吐率 = Σ 每时隙成功译码比特 / (时隙数 × 时隙长度) / 1e6
    网络吞吐率 = Σ UE 吞吐率；平均 = 算术平均；P5 = 手写线性插值百分位（含零吞吐率 UE）
输出每项检查 PASS/FAIL 与总体结论。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REL_TOL = 1e-9
ABS_TOL = 1e-9


def manual_percentile_linear(values: list[float], q: float) -> float:
    """线性插值百分位：rank = q/100 × (n − 1)（与 numpy method='linear' 同义，独立实现）。"""
    ordered = sorted(values)
    rank = q / 100.0 * (len(ordered) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def close(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def verify(exp_dir: Path) -> dict:
    art = exp_dir / "artifacts"
    record = json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8"))
    ues = json.loads((art / "ue_results.json").read_text(encoding="utf-8"))
    kpis = {k["metric_id"]: k for k in json.loads((art / "kpi.json").read_text(encoding="utf-8"))}
    result = json.loads((art / "result.json").read_text(encoding="utf-8"))["result"]
    trace = np.load(art / "slot_trace.npz")

    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    exp_id = record["experiment_id"]
    num_slots = int(result["num_slots"])
    slot_s = float(result["slot_duration_s"])
    duration = num_slots * slot_s
    trace_ids = [str(x) for x in trace["ue_ids"]]
    bits = trace["decoded_bits"]
    harq = trace["harq"]
    num_re = trace["num_re"]

    check("status_succeeded", record["status"] == "succeeded", record["status"])
    check("ue_count_min_3", len(ues) >= 3, f"{len(ues)} UEs")
    check("trace_shape", bits.shape == (num_slots, len(ues)) and trace_ids == [u["ue_id"] for u in ues],
          f"decoded_bits {bits.shape}, ue_ids {trace_ids}")
    check("simulated_duration", close(duration, float(result["simulated_duration_s"])),
          f"{num_slots} × {slot_s} s = {duration} s")

    recomputed: dict[str, float] = {}
    for j, u in enumerate(ues):
        total_bits = float(bits[:, j].sum())
        tput = total_bits / duration / 1e6
        recomputed[u["ue_id"]] = tput
        check(f"{u['ue_id']}.decoded_bits", int(total_bits) == u["decoded_bits"],
              f"trace Σ={int(total_bits)} vs ue_results={u['decoded_bits']}")
        check(f"{u['ue_id']}.throughput", close(tput, u["throughput_mbps"]) and close(tput, kpis["UE_THROUGHPUT_V0_1"]["per_ue"][u["ue_id"]]),
              f"independent={tput:.6f} Mbps, ue_results={u['throughput_mbps']}, kpi={kpis['UE_THROUGHPUT_V0_1']['per_ue'][u['ue_id']]}")
        check(f"{u['ue_id']}.slots", int((harq[:, j] >= 0).sum()) == u["scheduled_slots"]
              and int((harq[:, j] == 1).sum()) == u["acked_slots"],
              f"scheduled={u['scheduled_slots']} acked={u['acked_slots']}")
        check(f"{u['ue_id']}.finite", math.isfinite(tput) and tput >= 0, f"{tput}")

    values = list(recomputed.values())
    network = sum(values)
    average = network / len(values)
    p5 = manual_percentile_linear(values, 5.0)
    check("NETWORK_THROUGHPUT_V0_1", close(network, kpis["NETWORK_THROUGHPUT_V0_1"]["value"]),
          f"independent Σ={network:.6f} vs kpi={kpis['NETWORK_THROUGHPUT_V0_1']['value']}")
    check("AVG_UE_THROUGHPUT_V0_1", close(average, kpis["AVG_UE_THROUGHPUT_V0_1"]["value"]),
          f"independent mean={average:.6f} vs kpi={kpis['AVG_UE_THROUGHPUT_V0_1']['value']}")
    check("P5_UE_THROUGHPUT_V0_1", close(p5, kpis["P5_UE_THROUGHPUT_V0_1"]["value"]),
          f"independent manual P5={p5:.6f} vs kpi={kpis['P5_UE_THROUGHPUT_V0_1']['value']}")
    check("p5_population_includes_all_ues", kpis["P5_UE_THROUGHPUT_V0_1"]["sample_size"] == len(ues),
          f"sample_size={kpis['P5_UE_THROUGHPUT_V0_1']['sample_size']}")

    per_slot = num_re.sum(axis=1)
    check("re_budget", bool(np.all(per_slot <= result["num_data_re_per_slot"])),
          f"max Σ RE/slot={int(per_slot.max())} ≤ {result['num_data_re_per_slot']}")

    for k in kpis.values():
        ok = (k["source_experiment"] == exp_id and k["measured"] is False and k["acceptance_kpi"] is False
              and k["source_type"] == "simulation" and k["unit"] == "Mbps" and k["version"] == "0.1")
        check(f"{k['metric_id']}.provenance", ok,
              f"source={k['source_experiment']} backend={k['backend']} source_type={k['source_type']} measured={k['measured']}")
    check("not_test_fixture", record["provenance"].get("source_type") == "simulation"
          and record["provenance"].get("model_type") != "test_fixture", str(record["provenance"].get("model_type")))

    passed = all(c["status"] == "PASS" for c in checks)
    return {
        "experiment_id": exp_id,
        "verifier": "scripts/verify_system_experiment.py (independent; does not import evaluation.kpi)",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "overall": "PASS" if passed else "FAIL",
        "independent_values": {
            "ue_throughput_mbps": recomputed,
            "network_throughput_mbps": network,
            "avg_ue_throughput_mbps": average,
            "p5_ue_throughput_mbps": p5,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = verify(args.experiment_dir)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    for c in report["checks"]:
        print(f"[{c['status']}] {c['check']}: {c['detail']}")
    print(f"OVERALL: {report['overall']}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
