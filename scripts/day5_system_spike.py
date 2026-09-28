"""
Day 5 System Spike：验证 Sionna RT → Sionna SYS 系统级链路能否在本机真实运行。

    python scripts/day5_system_spike.py [--out reference/day5_spike] [--num-ue 6] [--num-slots 200]

链路（基于官方教程 tutorials/sys/SYS_Meets_RT.ipynb，按当前安装的 Sionna 2.1.0 API）：
    Sionna RT PathSolver → CFR（信道频率响应）
    → Sionna SYS PFSchedulerSUMIMO（比例公平调度）
    → downlink_fair_power_control（功率分配）
    → RZF 预编码 + LMMSE 后均衡 SINR（sionna.phy.ofdm）
    → OuterLoopLinkAdaptation（MCS 选择）
    → PHYAbstraction（译码比特 / HARQ）
UE 吞吐率 = Σ 成功译码比特 / 仿真时长（不是 Shannon 公式）。

本脚本是一次性技术探针，独立于平台代码，允许直接 import Sionna。
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import sionna.rt
import torch
from sionna.phy import config as sionna_config
from sionna.phy.constants import BOLTZMANN_CONSTANT
from sionna.phy.mimo import StreamManagement
from sionna.phy.nr.utils import decode_mcs_index
from sionna.phy.ofdm import LMMSEPostEqualizationSINR, ResourceGrid, RZFPrecodedChannel
from sionna.phy.utils import lin_to_db
from sionna.rt import PathSolver, PlanarArray, Receiver, Transmitter, load_scene, subcarrier_frequencies
from sionna.sys import OuterLoopLinkAdaptation, PFSchedulerSUMIMO, PHYAbstraction, downlink_fair_power_control
from sionna.sys.utils import spread_across_subcarriers

LOG = logging.getLogger("day5_spike")

CARRIER_HZ = 3.5e9
SUBCARRIER_SPACING_HZ = 30e3
NUM_PRB = 273                                  # 100 MHz @ 30 kHz SCS（TS 38.101-1 最大 PRB 数）
NUM_SUBCARRIERS = NUM_PRB * 12
NUM_DATA_SYMBOLS = 12                          # [A] 每时隙 14 符号中 2 个用于控制/DMRS 开销
SLOT_DURATION_S = 0.5e-3                       # 30 kHz SCS 时隙长度
BS_POSITION = [-150.3, 21.63, 42.5]            # 与 Day 4 SIONNA-DEMO-001 相同
BS_POWER_DBM = 44.0
BS_ARRAY = (2, 4)                              # [A] 8 天线 TR 38.901 平面阵
UE_HEIGHT_M = 1.5
UE_AREA_CENTER = (0.0, 0.0)
UE_AREA_SIZE = (850.0, 670.0)                  # 与 Day 4 radio map 测量区域相同
NOISE_FIGURE_DB = 7.0                          # [A] UE 噪声系数
TEMPERATURE_K = 290.0
BLER_TARGET = 0.1
MCS_TABLE_INDEX = 1
SEED = 20260927


def generate_ue_candidates(rng: np.random.Generator, count: int) -> np.ndarray:
    cx, cy = UE_AREA_CENTER
    sx, sy = UE_AREA_SIZE
    xs = rng.uniform(cx - sx / 2, cx + sx / 2, count)
    ys = rng.uniform(cy - sy / 2, cy + sy / 2, count)
    return np.stack([xs, ys, np.full(count, UE_HEIGHT_M)], axis=1)


def build_scene(bs_ant_rows: int, bs_ant_cols: int):
    scene = load_scene(sionna.rt.scene.etoile)
    scene.frequency = CARRIER_HZ
    scene.bandwidth = NUM_SUBCARRIERS * SUBCARRIER_SPACING_HZ
    scene.tx_array = PlanarArray(num_rows=bs_ant_rows, num_cols=bs_ant_cols, pattern="tr38901", polarization="V")
    scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.add(Transmitter("bs0", position=BS_POSITION, power_dbm=BS_POWER_DBM))
    return scene


def select_ues(scene, candidates: np.ndarray, num_ue: int, resource_grid, frequencies):
    """保留（按生成顺序）前 num_ue 个与基站存在传播路径的候选位置。"""
    for i, pos in enumerate(candidates):
        scene.add(Receiver(f"cand{i}", position=pos.tolist()))
    paths = PathSolver()(scene, max_depth=5, refraction=False, samples_per_src=10**6, seed=SEED)
    h = paths.cfr(frequencies=frequencies, sampling_frequency=1 / resource_grid.ofdm_symbol_duration,
                  num_time_steps=resource_grid.num_ofdm_symbols, out_type="numpy")
    h = torch.from_numpy(np.ascontiguousarray(h)).to(torch.complex64)
    gain = torch.mean(torch.abs(h) ** 2, dim=(1, 2, 3, 4, 5)).cpu().numpy()
    keep = [i for i in range(len(candidates)) if gain[i] > 0][:num_ue]
    for i in range(len(candidates)):
        scene.remove(f"cand{i}")
    return keep, h[keep], gain


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("reference/day5_spike"))
    parser.add_argument("--num-ue", type=int, default=6)
    parser.add_argument("--num-slots", type=int, default=200)
    parser.add_argument("--num-candidates", type=int, default=60)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(args.out / "run.log", mode="w", encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[handler, logging.StreamHandler(sys.stdout)])

    t0 = time.perf_counter()
    sionna_config.seed = SEED
    sionna_config.precision = "single"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    env = {
        "python": platform.python_version(),
        "sionna": version("sionna"),
        "sionna_rt": version("sionna-rt"),
        "mitsuba": version("mitsuba"),
        "drjit": version("drjit"),
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "torch_cuda_available": torch.cuda.is_available(),
        "sys_device": device,
        "mitsuba_variant": __import__("mitsuba").variant(),
    }
    LOG.info("environment %s", env)

    num_ue = args.num_ue
    num_bs_ant = BS_ARRAY[0] * BS_ARRAY[1]
    resource_grid = ResourceGrid(num_ofdm_symbols=NUM_DATA_SYMBOLS, fft_size=NUM_SUBCARRIERS,
                                 subcarrier_spacing=SUBCARRIER_SPACING_HZ, num_tx=num_ue, num_streams_per_tx=1)
    frequencies = subcarrier_frequencies(num_subcarriers=NUM_SUBCARRIERS, subcarrier_spacing=SUBCARRIER_SPACING_HZ)

    t_rt = time.perf_counter()
    scene = build_scene(*BS_ARRAY)
    rng = np.random.default_rng(SEED)
    candidates = generate_ue_candidates(rng, args.num_candidates)
    keep, h, gain = select_ues(scene, candidates, num_ue, resource_grid, frequencies)
    if len(keep) < num_ue:
        raise SystemExit(f"only {len(keep)} candidates have propagation paths")
    rt_seconds = time.perf_counter() - t_rt
    ue_pos = candidates[keep]
    LOG.info("RT done in %.2fs; kept candidates %s; h shape %s", rt_seconds, keep, tuple(h.shape))

    # h: [num_ut, num_rx_ant, num_bs, num_bs_ant, num_ofdm_sym, num_sc]（静止 UE，各时隙信道相同）
    h = h.to(device)
    no = BOLTZMANN_CONSTANT * TEMPERATURE_K * SUBCARRIER_SPACING_HZ * 10 ** (NOISE_FIGURE_DB / 10)
    stream_management = StreamManagement(np.ones([num_ue, 1]), num_ue)
    phy_abs = PHYAbstraction(device=device)
    olla = OuterLoopLinkAdaptation(phy_abs, num_ut=num_ue, bler_target=BLER_TARGET, batch_size=[1], device=device)
    scheduler = PFSchedulerSUMIMO(num_ue, NUM_SUBCARRIERS, NUM_DATA_SYMBOLS, batch_size=[1], num_streams_per_ut=1,
                                  beta=0.9, device=device)
    precoded_channel = RZFPrecodedChannel(resource_grid=resource_grid, stream_management=stream_management, device=device)
    lmmse = LMMSEPostEqualizationSINR(resource_grid=resource_grid, stream_management=stream_management, device=device)

    channel_gain = torch.abs(h).pow(2).float()
    rate_achievable = torch.log2(1.0 + channel_gain / no).mean(dim=(-3, -5)).permute(1, 2, 3, 0)
    pathloss = torch.mean(1 / channel_gain, dim=[1, 3, 4, 5]).permute(1, 0)

    harq = -torch.ones([1, num_ue], dtype=torch.int32, device=device)
    sinr_fb = torch.zeros([1, num_ue], dtype=torch.float32, device=device)
    decoded = torch.zeros([1, num_ue], dtype=torch.int32, device=device)
    hist = {k: np.zeros([args.num_slots, num_ue]) for k in
            ("decoded_bits", "harq", "mcs", "sinr_eff_db", "num_re", "tx_power_w", "se_la")}

    t_sys = time.perf_counter()
    for slot in range(args.num_slots):
        is_scheduled = scheduler(decoded, rate_achievable)
        num_re = torch.sum(is_scheduled.int(), dim=[-4, -3, -1])
        tx_power_ut, _ = downlink_fair_power_control(pathloss, no, num_re, bs_max_power_dbm=BS_POWER_DBM,
                                                     guaranteed_power_ratio=0.5, fairness=0)
        tx_power = spread_across_subcarriers(tx_power_ut.unsqueeze(-2), is_scheduled, num_tx=1)
        h_eff = precoded_channel(h[None, ...], tx_power=tx_power, alpha=no)
        sinr = lmmse(h_eff, no=no, interference_whitening=True)
        mcs = olla(num_allocated_re=num_re, sinr_eff=sinr_fb, mcs_table_index=MCS_TABLE_INDEX, mcs_category=1,
                   harq_feedback=harq)
        decoded, harq, sinr_eff, *_ = phy_abs(mcs, sinr=sinr, mcs_table_index=MCS_TABLE_INDEX, mcs_category=1)
        sinr_fb = torch.where(num_re > 0, sinr_eff, 0)
        mod, rate = decode_mcs_index(mcs, table_index=MCS_TABLE_INDEX, is_pusch=False)
        hist["decoded_bits"][slot] = decoded[0].cpu().numpy()
        hist["harq"][slot] = harq[0].cpu().numpy()
        hist["mcs"][slot] = mcs[0].cpu().numpy()
        hist["sinr_eff_db"][slot] = lin_to_db(sinr_eff)[0].cpu().numpy()
        hist["num_re"][slot] = num_re[0].cpu().numpy()
        hist["tx_power_w"][slot] = tx_power_ut[0].cpu().numpy()
        hist["se_la"][slot] = (mod.float() * rate)[0].cpu().numpy()
    sys_seconds = time.perf_counter() - t_sys

    duration = args.num_slots * SLOT_DURATION_S
    ues = []
    for u in range(num_ue):
        scheduled = hist["harq"][:, u] >= 0
        acks = int(np.sum(hist["harq"][:, u] == 1))
        tx = int(np.sum(scheduled))
        ues.append({
            "ue_id": f"UE-{u + 1:03d}",
            "position_m": ue_pos[u].round(2).tolist(),
            "mean_channel_gain_db": float(10 * np.log10(gain[keep[u]])),
            "total_decoded_bits": int(hist["decoded_bits"][:, u].sum()),
            "throughput_mbps": float(hist["decoded_bits"][:, u].sum() / duration / 1e6),
            "scheduled_slots": tx,
            "acked_slots": acks,
            "tbler": float(1 - acks / tx) if tx else None,
            "mean_mcs_scheduled": float(hist["mcs"][scheduled, u].mean()) if tx else None,
            "mean_sinr_eff_db_scheduled": float(hist["sinr_eff_db"][scheduled, u].mean()) if tx else None,
            "mean_allocated_re_per_slot": float(hist["num_re"][:, u].mean()),
        })
    tput = np.array([u["throughput_mbps"] for u in ues])
    result = {
        "status": "success",
        "chain": "Sionna RT PathSolver -> CFR -> Sionna SYS (PF scheduler, fair power control, RZF+LMMSE SINR, OLLA, PHYAbstraction)",
        "config": {
            "scene": "etoile", "carrier_hz": CARRIER_HZ, "bandwidth_hz": NUM_SUBCARRIERS * SUBCARRIER_SPACING_HZ,
            "subcarrier_spacing_hz": SUBCARRIER_SPACING_HZ, "num_subcarriers": NUM_SUBCARRIERS,
            "num_data_symbols_per_slot": NUM_DATA_SYMBOLS, "slot_duration_s": SLOT_DURATION_S,
            "num_slots": args.num_slots, "bs_position_m": BS_POSITION, "bs_power_dbm": BS_POWER_DBM,
            "bs_array": list(BS_ARRAY), "noise_figure_db": NOISE_FIGURE_DB, "bler_target": BLER_TARGET,
            "mcs_table_index": MCS_TABLE_INDEX, "seed": SEED, "num_ue": num_ue,
            "ue_generation": {"type": "uniform_area_with_path", "seed": SEED, "candidates": args.num_candidates,
                              "kept_candidate_indices": keep, "area_center": UE_AREA_CENTER, "area_size": UE_AREA_SIZE},
        },
        "ue_results": ues,
        "network": {
            "sum_throughput_mbps": float(tput.sum()),
            "mean_ue_throughput_mbps": float(tput.mean()),
            "p5_ue_throughput_mbps": float(np.percentile(tput, 5, method="linear")),
        },
        "runtime_s": {"rt": rt_seconds, "sys": sys_seconds, "total": time.perf_counter() - t0},
    }
    (args.out / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    (args.out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    LOG.info("network %s runtime %s", result["network"], result["runtime_s"])
    for u in ues:
        LOG.info("%s", u)


if __name__ == "__main__":
    main()
