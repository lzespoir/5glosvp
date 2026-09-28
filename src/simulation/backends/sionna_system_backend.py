"""
Sionna 系统级仿真适配器 / Sionna RT → Sionna SYS system backend adapter.

架构约束：除 sionna_backend.py 外，只有本模块允许 import Sionna / PyTorch。
链路（官方教程 tutorials/sys/SYS_Meets_RT，Sionna 2.1.0 API）：
    Sionna RT PathSolver → CFR
    → PFSchedulerSUMIMO（比例公平调度）
    → downlink_fair_power_control（功率分配）
    → RZF 预编码 + LMMSE 后均衡 SINR
    → OuterLoopLinkAdaptation（MCS 选择）
    → PHYAbstraction（译码比特 / HARQ）

Platform SystemScenario → Sionna API → per-slot trace → Canonical SystemSimulationResult
UE 吞吐率由平台 KPI 引擎根据 decoded_bits 计算，本模块不计算 KPI。
"""

from __future__ import annotations

import importlib.metadata
import logging
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from system_simulation.base import ChannelRealization, SystemRunOutput, SystemSimulationBackend
from system_simulation.errors import InvalidSystemScenarioError
from system_simulation.models import (
    SystemRuntime,
    SystemScenario,
    SystemSimulationResult,
    UserEquipmentResult,
)
from system_simulation.realization import propagation_fingerprint
from system_simulation.ue_generation import generate_candidates, ue_id_for

# torch 的 CUDA 构建与驱动版本不匹配时会告警；SYS 回退 CPU，由 health_check 报告
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        import mitsuba as mi
        import sionna.rt as srt
        import torch
        from sionna.phy import config as sionna_config
        from sionna.phy.constants import BOLTZMANN_CONSTANT
        from sionna.phy.mimo import StreamManagement
        from sionna.phy.nr.utils import decode_mcs_index
        from sionna.phy.ofdm import LMMSEPostEqualizationSINR, ResourceGrid, RZFPrecodedChannel
        from sionna.phy.utils import lin_to_db
        from sionna.rt import PathSolver, PlanarArray, Receiver, Transmitter, load_scene, subcarrier_frequencies
        from sionna.sys import (
            OuterLoopLinkAdaptation,
            PFSchedulerSUMIMO,
            PHYAbstraction,
            downlink_fair_power_control,
        )
        from sionna.sys.utils import spread_across_subcarriers

        _IMPORT_ERROR: str | None = None
    except Exception as _e:  # noqa: BLE001 - 诊断用途，由 health_check 报告
        _IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

logger = logging.getLogger(__name__)

SIONNA_SYSTEM_BACKEND_ID = "sionna_system"
PROVIDER = "sionna_sys"
MIN_PYTHON = (3, 10)
UE_ARRAY_PATTERN = "iso"                 # [A] UE 单天线全向
MCS_CATEGORY_PDSCH = 1
CANDIDATE_PREFIX = "cand"
TRACE_KEYS = ("decoded_bits", "harq", "mcs", "sinr_eff_db", "num_re", "tx_power_w")


def _version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _resolve_scene(scene_name: str) -> str:
    builtin = getattr(srt.scene, scene_name, None)
    if isinstance(builtin, str) and builtin.endswith(".xml"):
        return builtin
    if Path(scene_name).is_file():
        return scene_name
    raise InvalidSystemScenarioError(f"Unknown scene '{scene_name}'")


class SionnaSystemBackend(SystemSimulationBackend):
    @property
    def name(self) -> str:
        return SIONNA_SYSTEM_BACKEND_ID

    def health_check(self) -> dict[str, Any]:
        errors: list[str] = []
        warns: list[str] = []
        if sys.version_info[:2] < MIN_PYTHON:
            errors.append(f"Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} required")
        if _IMPORT_ERROR is not None:
            errors.append(f"Sionna SYS import failed: {_IMPORT_ERROR}")
        report: dict[str, Any] = {
            "available": False,
            "version": _version("sionna"),
            "provider_versions": self._provider_versions(),
            "sys_device": None,
            "errors": errors,
            "warnings": warns,
        }
        if _IMPORT_ERROR is None:
            report["sys_device"] = self._device()
            report["mitsuba_variant"] = mi.variant()
            if report["sys_device"] == "cpu":
                warns.append("PyTorch CUDA unavailable; Sionna SYS runs on CPU (slower)")
        report["available"] = not errors
        return report

    @staticmethod
    def _provider_versions() -> dict[str, str | None]:
        return {
            "sionna": _version("sionna"),
            "sionna-rt": _version("sionna-rt"),
            "mitsuba": _version("mitsuba"),
            "drjit": _version("drjit"),
            "torch": _version("torch"),
        }

    @staticmethod
    def _device() -> str:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return "cuda" if torch.cuda.is_available() else "cpu"

    # ------------------------------------------------------------------

    @staticmethod
    def _validate(scenario: SystemScenario) -> None:
        if _IMPORT_ERROR is not None:
            raise RuntimeError(f"Sionna SYS unavailable: {_IMPORT_ERROR}")
        if len(scenario.cells) != 1 or len(scenario.base_stations) != 1:
            raise InvalidSystemScenarioError("sionna_system V0.1 supports exactly 1 BS / 1 cell")
        cell = scenario.cells[0]
        sim = scenario.simulation
        occupied_bw = sim.num_subcarriers * sim.subcarrier_spacing_hz
        if occupied_bw > cell.bandwidth_hz:
            raise InvalidSystemScenarioError(
                f"Occupied bandwidth {occupied_bw:.0f} Hz exceeds channel bandwidth {cell.bandwidth_hz:.0f} Hz"
            )
        for u in scenario.ues:
            if u.serving_cell_id not in (None, cell.cell_id):
                raise InvalidSystemScenarioError(f"UE {u.ue_id} serving cell must be {cell.cell_id}")
        if sim.warmup_slots >= sim.num_slots:
            raise InvalidSystemScenarioError(
                f"warmup_slots ({sim.warmup_slots}) must be smaller than num_slots ({sim.num_slots})"
            )

    @staticmethod
    def _rg_template(sim) -> dict[str, Any]:
        return dict(num_ofdm_symbols=sim.num_data_symbols_per_slot, fft_size=sim.num_subcarriers,
                    subcarrier_spacing=sim.subcarrier_spacing_hz, num_streams_per_tx=1)

    def realize_channel(self, scenario: SystemScenario, log: logging.Logger) -> ChannelRealization:
        """Sionna RT 一次：放置 UE、求解路径、导出 CFR。"""
        self._validate(scenario)
        cell = scenario.cells[0]
        sim = scenario.simulation
        sionna_config.seed = scenario.seed
        sionna_config.precision = "single"
        t0 = time.perf_counter()
        probe_rg = ResourceGrid(num_tx=1, **self._rg_template(sim))
        frequencies = subcarrier_frequencies(num_subcarriers=sim.num_subcarriers,
                                             subcarrier_spacing=sim.subcarrier_spacing_hz)
        scene = self._build_scene(scenario, sim.num_subcarriers * sim.subcarrier_spacing_hz)

        if scenario.ue_generator:
            candidates = generate_candidates(scenario.ue_generator)
            candidate_ids = [f"{CANDIDATE_PREFIX}{i}" for i in range(len(candidates))]
            want = scenario.ue_generator.count
        else:
            candidates = np.array([u.position for u in scenario.ues], dtype=float)
            candidate_ids = [u.ue_id for u in scenario.ues]
            want = len(scenario.ues)
        h_all, gain = self._solve_channels(scene, candidates, candidate_ids, probe_rg, frequencies, sim, scenario.seed)
        with_path = [i for i in range(len(candidates)) if gain[i] > 0]
        if scenario.ue_generator:
            keep = with_path[:want]
            if len(keep) < want:
                raise InvalidSystemScenarioError(
                    f"Only {len(keep)} of {len(candidates)} generated candidates have propagation paths (need {want})"
                )
            ue_ids = [ue_id_for(i) for i in range(want)]
        else:
            no_path = [candidate_ids[i] for i in range(len(candidates)) if gain[i] <= 0]
            if no_path:
                raise InvalidSystemScenarioError(f"No propagation path to UE(s): {', '.join(no_path)}")
            keep = list(range(want))
            ue_ids = candidate_ids
        prop_seconds = time.perf_counter() - t0
        log.info("Propagation (Sionna RT) %.2fs; UEs kept=%s (candidate indices %s)", prop_seconds, want, keep)
        ue_generation = None
        if scenario.ue_generator:
            ue_generation = {**scenario.ue_generator.model_dump(mode="json"),
                             "kept_candidate_indices": keep, "candidates_with_path": len(with_path)}
        cfr = np.ascontiguousarray(h_all[keep].numpy())
        return ChannelRealization(
            ue_ids=tuple(ue_ids),
            serving_cell_ids=tuple(cell.cell_id for _ in keep),
            positions=np.asarray(candidates[keep], dtype=float),
            mean_channel_gain_db=self._mean_gain_db(cfr),
            arrays={"cfr": cfr},
            provider=PROVIDER,
            provider_versions=self._provider_versions(),
            propagation_fingerprint=propagation_fingerprint(scenario),
            metadata={"ue_generation": ue_generation, "candidate_indices": keep,
                      "propagation_seconds": prop_seconds},
        )

    def _check_reusable(self, scenario: SystemScenario, channel: ChannelRealization) -> None:
        sim = scenario.simulation
        if channel.provider != PROVIDER:
            raise InvalidSystemScenarioError(f"Channel realization provider '{channel.provider}' != '{PROVIDER}'")
        if channel.propagation_fingerprint != propagation_fingerprint(scenario):
            raise InvalidSystemScenarioError(
                "Channel realization was generated for different propagation conditions; it cannot be reused"
            )
        cfr = channel.arrays.get("cfr")
        if cfr is None or cfr.shape[0] != scenario.ue_count or cfr.shape[-1] != sim.num_subcarriers \
                or cfr.shape[-2] != sim.num_data_symbols_per_slot:
            raise InvalidSystemScenarioError(
                f"Channel realization shape {None if cfr is None else cfr.shape} does not match the scenario grid"
            )

    def run(
        self,
        scenario: SystemScenario,
        experiment_id: str,
        log: logging.Logger,
        channel: ChannelRealization | None = None,
    ) -> SystemRunOutput:
        self._validate(scenario)
        cell = scenario.cells[0]
        sim = scenario.simulation
        reused = channel is not None
        if channel is None:
            channel = self.realize_channel(scenario, log)
            prop_seconds = float(channel.metadata.get("propagation_seconds") or 0.0)
        else:
            self._check_reusable(scenario, channel)
            prop_seconds = 0.0
            log.info("Reusing frozen channel realization (%d UEs); Sionna RT skipped", len(channel.ue_ids))
        sionna_config.seed = scenario.seed
        sionna_config.precision = "single"
        device = self._device()

        cfr = np.ascontiguousarray(channel.arrays["cfr"])
        # 由实际送入 SYS 的信道重新计算平均增益（复用时各候选应逐位一致）
        gain_db = self._mean_gain_db(cfr)
        h = torch.from_numpy(cfr).to(torch.complex64).to(device)
        num_ue = len(channel.ue_ids)
        t_sys = time.perf_counter()
        trace = self._run_sys(h, num_ue, cell.tx_power_dbm, sim, self._rg_template(sim), device, log)
        sys_seconds = time.perf_counter() - t_sys
        log.info("System (Sionna SYS, device=%s) %.2fs for %d slots", device, sys_seconds, sim.num_slots)

        num_re_total = sim.num_data_symbols_per_slot * sim.num_subcarriers
        # KPI 聚合窗口：丢弃前 warmup_slots 个时隙（启动暂态）
        window = slice(sim.warmup_slots, sim.num_slots)
        measured_slots = sim.num_slots - sim.warmup_slots
        duration = measured_slots * sim.slot_duration_s
        candidate_indices = channel.metadata.get("candidate_indices") or list(range(num_ue))
        ue_results = []
        for j, ue_id in enumerate(channel.ue_ids):
            harq = trace["harq"][window, j]
            scheduled = harq >= 0
            tx = int(scheduled.sum())
            acks = int((harq == 1).sum())
            unavailable: dict[str, str] = {}
            if not tx:
                unavailable = {k: "UE 未被调度 / UE never scheduled"
                               for k in ("sinr_eff_db_mean", "mcs_index_mean", "tbler")}
            ue_results.append(UserEquipmentResult(
                ue_id=ue_id,
                serving_cell_id=channel.serving_cell_ids[j],
                position=[float(v) for v in channel.positions[j]],
                mean_channel_gain_db=float(gain_db[j]),
                sinr_eff_db_mean=float(trace["sinr_eff_db"][window, j][scheduled].mean()) if tx else None,
                mcs_index_mean=float(trace["mcs"][window, j][scheduled].mean()) if tx else None,
                scheduled_slots=tx,
                acked_slots=acks,
                tbler=float(1 - acks / tx) if tx else None,
                allocated_re_per_slot_mean=float(trace["num_re"][window, j].mean()),
                allocated_re_share=float(trace["num_re"][window, j].sum() / (num_re_total * measured_slots)),
                tx_power_w_mean=float(trace["tx_power_w"][window, j].mean()),
                decoded_bits=int(trace["decoded_bits"][window, j].sum()),
                simulated_duration_s=duration,
                unavailable=unavailable,
                metadata={"candidate_index": candidate_indices[j]},
            ))

        warns = []
        if device == "cpu":
            warns.append("Sionna SYS ran on CPU (PyTorch CUDA unavailable)")
        result = SystemSimulationResult(
            scenario_id=scenario.scenario_id,
            backend=SIONNA_SYSTEM_BACKEND_ID,
            backend_version=_version("sionna"),
            provider_versions=self._provider_versions(),
            seed=scenario.seed,
            num_slots=sim.num_slots,
            warmup_slots=sim.warmup_slots,
            slot_duration_s=sim.slot_duration_s,
            simulated_duration_s=duration,
            num_data_re_per_slot=num_re_total,
            ue_results=ue_results,
            scheduler={"id": sim.scheduler.id, "name": "Proportional Fair SU-MIMO",
                       "implementation": "sionna.sys.PFSchedulerSUMIMO", "beta": sim.scheduler.beta,
                       "provider": PROVIDER},
            link_adaptation={"id": sim.link_adaptation.id, "name": "Outer-Loop Link Adaptation",
                             "implementation": "sionna.sys.OuterLoopLinkAdaptation",
                             "bler_target": sim.link_adaptation.bler_target,
                             "mcs_table_index": sim.link_adaptation.mcs_table_index,
                             "phy_abstraction": "sionna.sys.PHYAbstraction", "provider": PROVIDER},
            power_control={"id": sim.power_control.id, "implementation": "sionna.sys.downlink_fair_power_control",
                           "guaranteed_power_ratio": sim.power_control.guaranteed_power_ratio,
                           "fairness": sim.power_control.fairness, "provider": PROVIDER,
                           "precoding": "RZF (sionna.phy.ofdm.RZFPrecodedChannel)",
                           "sinr": "LMMSE post-equalization (sionna.phy.ofdm.LMMSEPostEqualizationSINR)"},
            ue_generation=channel.metadata.get("ue_generation"),
            channel_reused=reused,
            compute_device=device,
            runtime=SystemRuntime(propagation_seconds=prop_seconds, system_seconds=sys_seconds),
            warnings=warns,
        )
        return SystemRunOutput(result=result, slot_trace=trace)

    @staticmethod
    def _mean_gain_db(cfr: np.ndarray) -> np.ndarray:
        """每个 UE 的平均信道功率增益 [dB]，在 float64 中由 CFR 计算（与张量形状无关，结果可逐位复现）。"""
        power = np.abs(cfr.astype(np.complex128)) ** 2
        return 10 * np.log10(power.reshape(cfr.shape[0], -1).mean(axis=1))

    @staticmethod
    def _build_scene(scenario: SystemScenario, occupied_bw: float):
        cell = scenario.cells[0]
        scene_path = _resolve_scene(scenario.scene)
        try:
            scene = load_scene(scene_path)
        except Exception as e:  # noqa: BLE001 - 转换为平台异常
            raise InvalidSystemScenarioError(f"Failed to load scene '{scenario.scene}': {e}") from e
        scene.frequency = cell.carrier_frequency_hz
        scene.bandwidth = occupied_bw
        scene.tx_array = PlanarArray(num_rows=cell.antenna.num_rows, num_cols=cell.antenna.num_cols,
                                     pattern=cell.antenna.pattern, polarization=cell.antenna.polarization)
        scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern=UE_ARRAY_PATTERN,
                                     polarization=cell.antenna.polarization)
        scene.add(Transmitter(cell.cell_id, position=list(scenario.cell_position(cell)),
                              power_dbm=cell.tx_power_dbm))
        return scene

    @staticmethod
    def _solve_channels(scene, positions: np.ndarray, ids: list[str], resource_grid, frequencies, sim, seed: int):
        for rx_id, pos in zip(ids, positions):
            scene.add(Receiver(rx_id, position=[float(v) for v in pos]))
        paths = PathSolver()(scene, max_depth=sim.max_depth, refraction=False,
                             samples_per_src=sim.samples_per_src, seed=seed)
        # out_type="numpy"：torch 无法使用 CUDA 时 dlpack 直通不可用
        h = paths.cfr(frequencies=frequencies, sampling_frequency=1 / resource_grid.ofdm_symbol_duration,
                      num_time_steps=resource_grid.num_ofdm_symbols, out_type="numpy")
        h = torch.from_numpy(np.ascontiguousarray(h)).to(torch.complex64)
        gain = torch.mean(torch.abs(h) ** 2, dim=(1, 2, 3, 4, 5)).numpy()
        return h, gain

    @staticmethod
    def _run_sys(h, num_ue: int, bs_power_dbm: float, sim, rg_template: dict, device: str,
                 log: logging.Logger) -> dict[str, np.ndarray]:
        # h: [num_ut, num_rx_ant, num_bs, num_bs_ant, num_ofdm_sym, num_sc]；静止 UE，各时隙信道相同
        la = sim.link_adaptation
        resource_grid = ResourceGrid(num_tx=num_ue, **rg_template)
        no = BOLTZMANN_CONSTANT * sim.temperature_k * sim.subcarrier_spacing_hz * 10 ** (sim.noise_figure_db / 10)
        stream_management = StreamManagement(np.ones([num_ue, 1]), num_ue)
        phy_abs = PHYAbstraction(device=device)
        olla = OuterLoopLinkAdaptation(phy_abs, num_ut=num_ue, bler_target=la.bler_target, batch_size=[1],
                                       device=device)
        scheduler = PFSchedulerSUMIMO(num_ue, sim.num_subcarriers, sim.num_data_symbols_per_slot, batch_size=[1],
                                      num_streams_per_ut=1, beta=sim.scheduler.beta, device=device)
        precoded_channel = RZFPrecodedChannel(resource_grid=resource_grid, stream_management=stream_management,
                                              device=device)
        lmmse = LMMSEPostEqualizationSINR(resource_grid=resource_grid, stream_management=stream_management,
                                          device=device)

        channel_gain = torch.abs(h).pow(2).float()
        rate_achievable = torch.log2(1.0 + channel_gain / no).mean(dim=(-3, -5)).permute(1, 2, 3, 0)
        pathloss = torch.mean(1 / channel_gain, dim=[1, 3, 4, 5]).permute(1, 0)

        harq = -torch.ones([1, num_ue], dtype=torch.int32, device=device)
        sinr_fb = torch.zeros([1, num_ue], dtype=torch.float32, device=device)
        decoded = torch.zeros([1, num_ue], dtype=torch.int32, device=device)
        trace = {k: np.zeros([sim.num_slots, num_ue]) for k in TRACE_KEYS}
        log_every = max(1, sim.num_slots // 10)
        with torch.no_grad():
            for slot in range(sim.num_slots):
                is_scheduled = scheduler(decoded, rate_achievable)
                num_re = torch.sum(is_scheduled.int(), dim=[-4, -3, -1])
                tx_power_ut, _ = downlink_fair_power_control(
                    pathloss, no, num_re, bs_max_power_dbm=bs_power_dbm,
                    guaranteed_power_ratio=sim.power_control.guaranteed_power_ratio,
                    fairness=sim.power_control.fairness)
                tx_power = spread_across_subcarriers(tx_power_ut.unsqueeze(-2), is_scheduled, num_tx=1)
                h_eff = precoded_channel(h[None, ...], tx_power=tx_power, alpha=no)
                sinr = lmmse(h_eff, no=no, interference_whitening=True)
                mcs = olla(num_allocated_re=num_re, sinr_eff=sinr_fb, mcs_table_index=la.mcs_table_index,
                           mcs_category=MCS_CATEGORY_PDSCH, harq_feedback=harq)
                decoded, harq, sinr_eff, *_ = phy_abs(mcs, sinr=sinr, mcs_table_index=la.mcs_table_index,
                                                      mcs_category=MCS_CATEGORY_PDSCH)
                sinr_fb = torch.where(num_re > 0, sinr_eff, 0)
                trace["decoded_bits"][slot] = decoded[0].cpu().numpy()
                trace["harq"][slot] = harq[0].cpu().numpy()
                trace["mcs"][slot] = mcs[0].cpu().numpy()
                trace["sinr_eff_db"][slot] = lin_to_db(sinr_eff)[0].cpu().numpy()
                trace["num_re"][slot] = num_re[0].cpu().numpy()
                trace["tx_power_w"][slot] = tx_power_ut[0].cpu().numpy()
                if (slot + 1) % log_every == 0:
                    log.info("slot %d/%d", slot + 1, sim.num_slots)
        # decode_mcs_index 验证 MCS 表可解析（频谱效率仅记入日志，不参与 KPI）
        mod, rate = decode_mcs_index(mcs, table_index=la.mcs_table_index, is_pusch=False)
        log.info("last-slot MCS %s → spectral efficiency %s bit/RE",
                 mcs[0].tolist(), [round(v, 3) for v in (mod.float() * rate)[0].tolist()])
        return trace
