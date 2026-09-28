"""
Day 6 Simulation Horizon Study：冻结一次信道实现，观察系统 KPI 随仿真时隙数的稳定性。

    PYTHONPATH=src python scripts/day6_horizon_study.py [--out reference/day6_horizon_study]

步骤：
1. Sionna RT 生成一次信道实现 A（UE 放置 + CFR），计算 SHA-256；再生成一次 B，量化 GPU RT 漂移。
2. 在信道 A 上对每个候选 beta 运行 1000 时隙 SYS；前缀 [0, H) 给出 H = 200 / 500 / 1000 的 KPI
   （调度/链路自适应是因果的，前缀等价性在第 3 步验证）。
3. baseline beta：单独运行 200、500 时隙并重复 200 时隙，验证前缀等价与 CPU SYS 确定性。
4. baseline beta 在信道 B 上运行 200 时隙，对比信道差异带来的 KPI 变化（非优化收益）。
5. 按 warm-up 窗口 {0, 20, 50, 100} 重新聚合 1000 时隙结果，观察启动暂态。

使用平台后端与 KPI 引擎；结果写入 results.json / slot_traces.npz / plot.png，README 由人工分析撰写。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluation.kpi import (  # noqa: E402
    AVG_UE_THROUGHPUT_V0_1,
    NETWORK_THROUGHPUT_V0_1,
    P5_UE_THROUGHPUT_V0_1,
    KpiContext,
    UeThroughputInput,
    default_kpi_registry,
)
from simulation.backends.sionna_system_backend import SionnaSystemBackend, _version  # noqa: E402
from system_simulation import SystemScenarioCatalog  # noqa: E402
from system_simulation.models import SystemScenario  # noqa: E402
from system_simulation.realization import hash_arrays  # noqa: E402

LOG = logging.getLogger("day6_horizon")
SCENARIO_ID = "SYSTEM-DEMO-001"
BETAS = (0.1, 0.3, 0.6, 0.9, 0.99)
BASELINE_BETA = 0.9
HORIZONS = (200, 500, 1000)
WARMUPS = (0, 20, 50, 100)
MOVING_WINDOW = 20
KPI_IDS = (NETWORK_THROUGHPUT_V0_1, AVG_UE_THROUGHPUT_V0_1, P5_UE_THROUGHPUT_V0_1)


def derive(scenario: SystemScenario, beta: float, num_slots: int) -> SystemScenario:
    sim = scenario.simulation
    return scenario.model_copy(update={"simulation": sim.model_copy(update={
        "num_slots": num_slots, "warmup_slots": 0,
        "scheduler": sim.scheduler.model_copy(update={"beta": beta})})})


def window_kpis(bits: np.ndarray, ue_ids: list[str], lo: int, hi: int, slot_s: float) -> dict[str, float]:
    registry = default_kpi_registry()
    ctx = KpiContext(source_experiment="HORIZON-STUDY", backend="sionna_system", scenario_id=SCENARIO_ID,
                     seed=0, source_type="simulation")
    inputs = [UeThroughputInput(ue_id=u, decoded_bits=int(bits[lo:hi, j].sum()),
                                simulated_duration_s=(hi - lo) * slot_s)
              for j, u in enumerate(ue_ids)]
    results = {k.metric_id: k for k in registry.evaluate(inputs, ctx)}
    return {k: float(results[k].value) for k in KPI_IDS}


def run(backend: SionnaSystemBackend, scenario: SystemScenario, channel, beta: float, slots: int):
    t0 = time.perf_counter()
    out = backend.run(derive(scenario, beta, slots), "HORIZON-STUDY", LOG, channel=channel)
    seconds = time.perf_counter() - t0
    LOG.info("beta=%.2f slots=%d SYS %.1fs", beta, slots, seconds)
    return out.slot_trace, seconds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "reference" / "day6_horizon_study")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args.out.mkdir(parents=True, exist_ok=True)

    scenario = SystemScenarioCatalog(ROOT / "configs" / "system").get(SCENARIO_ID)
    slot_s = scenario.simulation.slot_duration_s
    backend = SionnaSystemBackend()

    t0 = time.perf_counter()
    ch_a = backend.realize_channel(scenario, LOG)
    rt_a = time.perf_counter() - t0
    ch_b = backend.realize_channel(scenario, LOG)
    hash_a, hash_b = hash_arrays(ch_a.arrays), hash_arrays(ch_b.arrays)
    ue_ids = list(ch_a.ue_ids)
    gain_diff_db = np.abs(ch_a.mean_channel_gain_db - ch_b.mean_channel_gain_db)
    LOG.info("channel A %s… / B %s… identical=%s max |Δgain| %.5f dB", hash_a[:12], hash_b[:12],
             hash_a == hash_b, gain_diff_db.max())

    traces: dict[str, np.ndarray] = {}
    per_beta = []
    for beta in BETAS:
        trace, seconds = run(backend, scenario, ch_a, beta, max(HORIZONS))
        bits = trace["decoded_bits"]
        traces[f"beta_{beta}"] = bits
        per_beta.append({
            "beta": beta,
            "sys_seconds_1000_slots": seconds,
            "seconds_per_slot": seconds / max(HORIZONS),
            "horizons": {str(h): window_kpis(bits, ue_ids, 0, h, slot_s) for h in HORIZONS},
            "warmup_at_1000": {str(w): window_kpis(bits, ue_ids, w, max(HORIZONS), slot_s) for w in WARMUPS},
            "warmup_at_200": {str(w): window_kpis(bits, ue_ids, w, 200, slot_s) for w in WARMUPS if w < 200},
            "per_ue_1000": {u: float(bits[:, j].sum() / (max(HORIZONS) * slot_s) / 1e6) for j, u in enumerate(ue_ids)},
        })

    base_long = traces[f"beta_{BASELINE_BETA}"]
    t200, s200 = run(backend, scenario, ch_a, BASELINE_BETA, 200)
    t200b, _ = run(backend, scenario, ch_a, BASELINE_BETA, 200)
    t500, s500 = run(backend, scenario, ch_a, BASELINE_BETA, 500)
    t200_b, _ = run(backend, scenario, ch_b, BASELINE_BETA, 200)
    checks = {
        "repeat_200_bit_identical": bool(np.array_equal(t200["decoded_bits"], t200b["decoded_bits"])
                                         and np.array_equal(t200["harq"], t200b["harq"])),
        "prefix_200_equals_run_200": bool(np.array_equal(base_long[:200], t200["decoded_bits"])),
        "prefix_500_equals_run_500": bool(np.array_equal(base_long[:500], t500["decoded_bits"])),
        "sys_seconds_200": s200,
        "sys_seconds_500": s500,
    }
    kpi_a = window_kpis(t200["decoded_bits"], ue_ids, 0, 200, slot_s)
    kpi_b = window_kpis(t200_b["decoded_bits"], ue_ids, 0, 200, slot_s)
    rt_drift = {
        "channel_a_sha256": hash_a,
        "channel_b_sha256": hash_b,
        "identical": hash_a == hash_b,
        "max_abs_gain_diff_db": float(gain_diff_db.max()),
        "kpi_channel_a_200": kpi_a,
        "kpi_channel_b_200": kpi_b,
        "relative_diff_percent": {k: (kpi_b[k] - kpi_a[k]) / kpi_a[k] * 100 for k in KPI_IDS},
    }

    ref = {b["beta"]: b["horizons"][str(max(HORIZONS))] for b in per_beta}
    convergence = {
        str(b["beta"]): {str(h): {k: (b["horizons"][str(h)][k] - ref[b["beta"]][k]) / ref[b["beta"]][k] * 100
                                  for k in KPI_IDS} for h in HORIZONS}
        for b in per_beta
    }
    ranking = {
        str(h): [b["beta"] for b in sorted(per_beta, key=lambda b: -b["horizons"][str(h)][NETWORK_THROUGHPUT_V0_1])]
        for h in HORIZONS
    }

    results = {
        "scenario_id": SCENARIO_ID,
        "sionna_version": _version("sionna"),
        "provider_versions": ch_a.provider_versions,
        "ue_ids": ue_ids,
        "betas": list(BETAS),
        "baseline_beta": BASELINE_BETA,
        "horizons": list(HORIZONS),
        "warmups": list(WARMUPS),
        "rt_seconds": rt_a,
        "channel_realization": {"sha256": hash_a, "shape": list(ch_a.arrays["cfr"].shape),
                                "dtype": str(ch_a.arrays["cfr"].dtype),
                                "mean_channel_gain_db": ch_a.mean_channel_gain_db.tolist()},
        "per_beta": per_beta,
        "convergence_vs_1000_percent": convergence,
        "network_throughput_ranking": ranking,
        "determinism": checks,
        "rt_drift": rt_drift,
    }
    (args.out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    np.savez_compressed(args.out / "slot_traces.npz", ue_ids=np.array(ue_ids), slot_duration_s=slot_s, **traces)
    plot(args.out / "plot.png", per_beta, traces, slot_s)
    LOG.info("wrote %s", args.out)
    return 0


def plot(path: Path, per_beta: list[dict], traces: dict[str, np.ndarray], slot_s: float) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    ax = axes[0, 0]
    for b in per_beta:
        net = traces[f"beta_{b['beta']}"].sum(axis=1)
        cum = np.cumsum(net) / (np.arange(1, net.size + 1) * slot_s) / 1e6
        ax.plot(np.arange(1, net.size + 1), cum, label=f"β={b['beta']}")
    for h in HORIZONS:
        ax.axvline(h, color="#999", lw=0.8, ls="--")
    ax.set(title="Cumulative network throughput vs horizon", xlabel="slots", ylabel="Mbps")
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    for b in per_beta:
        net = traces[f"beta_{b['beta']}"].sum(axis=1) / slot_s / 1e6
        mov = np.convolve(net, np.ones(MOVING_WINDOW) / MOVING_WINDOW, mode="valid")
        ax.plot(np.arange(MOVING_WINDOW, net.size + 1), mov, lw=0.9, label=f"β={b['beta']}")
    ax.set(title=f"{MOVING_WINDOW}-slot moving network throughput (transient check)", xlabel="slot", ylabel="Mbps")
    ax.legend(fontsize=8)

    for ax, kpi, title in ((axes[1, 0], NETWORK_THROUGHPUT_V0_1, "Network throughput"),
                           (axes[1, 1], P5_UE_THROUGHPUT_V0_1, "P5 UE throughput")):
        for b in per_beta:
            ax.plot(HORIZONS, [b["horizons"][str(h)][kpi] for h in HORIZONS], marker="o", label=f"β={b['beta']}")
        ax.set(title=f"{title} by horizon (frozen channel)", xlabel="slots", ylabel="Mbps", xticks=HORIZONS)
        ax.legend(fontsize=8)
    fig.suptitle("Day 6 Horizon Study — SYSTEM-DEMO-001, one frozen Sionna RT channel realization")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
