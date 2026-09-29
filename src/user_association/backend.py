from __future__ import annotations
import hashlib, json, logging, math, time
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
from .models import *

@dataclass
class FrozenMultiCellChannel:
    scenario_id: str
    ue_ids: list[str]
    cell_ids: list[str]
    gains_linear: np.ndarray  # [ue, cell]
    gains_db: np.ndarray
    positions: np.ndarray
    channel_hash: str
    runtime_seconds: float
    provider_versions: dict[str, str | None]

class MultiCellBackend:
    """Sionna RT propagation + explicit, deterministic platform system bridge."""
    backend_id = "sionna_multicell"
    interference_model = INTERFERENCE_MODEL

    def __init__(self, scenario: MultiCellScenario):
        self.scenario = scenario
        self.channel: FrozenMultiCellChannel | None = None

    def _scene(self):
        srt = importlib.import_module("sionna.rt")
        load_scene, PlanarArray, Transmitter, Receiver = (srt.load_scene, srt.PlanarArray, srt.Transmitter, srt.Receiver)
        scene = load_scene(getattr(srt.scene, self.scenario.scene))
        scene.frequency = self.scenario.frequency_hz
        scene.bandwidth = self.scenario.bandwidth_hz
        scene.tx_array = PlanarArray(num_rows=self.scenario.cells[0].antenna_rows,
                                     num_cols=self.scenario.cells[0].antenna_cols,
                                     pattern="tr38901", polarization="V")
        for cell in self.scenario.cells:
            scene.add(Transmitter(cell.cell_id, position=cell.position, power_dbm=cell.tx_power_dbm))
        scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
        for ue in self.scenario.ues:
            scene.add(Receiver(ue.ue_id, position=ue.position))
        return scene

    def realize_channel(self, log: logging.Logger | None = None) -> FrozenMultiCellChannel:
        # BenchmarkService may inject the persisted Day 8 realization. Reuse it
        # instead of retracing so every algorithm sees the same frozen channel.
        if self.channel is not None:
            return self.channel
        rt = importlib.import_module("sionna.rt")
        phy = importlib.import_module("sionna.phy.ofdm")
        from importlib import metadata
        t0 = time.perf_counter()
        scene = self._scene()
        sim_sc = 273 * 12
        rg = phy.ResourceGrid(num_tx=1, num_ofdm_symbols=12, fft_size=sim_sc,
                          subcarrier_spacing=30e3, num_streams_per_tx=1)
        freq = rt.subcarrier_frequencies(num_subcarriers=sim_sc, subcarrier_spacing=30e3)
        paths = rt.PathSolver()(scene, max_depth=5, refraction=False, samples_per_src=30000, seed=self.scenario.seed)
        h = paths.cfr(frequencies=freq, sampling_frequency=1 / rg.ofdm_symbol_duration,
                      num_time_steps=12, out_type="numpy")
        # [UE, Rx, TX, antenna, symbol, subcarrier] -> [UE, TX]
        power = np.abs(h.astype(np.complex128)) ** 2
        gains = power.reshape(len(self.scenario.ues), 1, len(self.scenario.cells), -1).mean(axis=-1)[:, 0, :]
        gains = np.asarray(gains, dtype=np.float64)
        payload = {"scenario_id": self.scenario.scenario_id, "ue_ids": [u.ue_id for u in self.scenario.ues],
                   "cell_ids": [c.cell_id for c in self.scenario.cells],
                   "gains": gains.tolist(), "seed": self.scenario.seed}
        chash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        versions = {}
        for name in ("sionna", "sionna-rt", "mitsuba", "drjit", "torch"):
            try: versions[name] = metadata.version(name)
            except metadata.PackageNotFoundError: versions[name] = None
        self.channel = FrozenMultiCellChannel(self.scenario.scenario_id,
            [u.ue_id for u in self.scenario.ues], [c.cell_id for c in self.scenario.cells], gains,
            10 * np.log10(np.maximum(gains, 1e-30)), np.asarray([u.position for u in self.scenario.ues]),
            chash, time.perf_counter() - t0, versions)
        return self.channel

    def candidate_cells(self) -> dict[str, list[CandidateCell]]:
        ch = self.realize_channel()
        out = {}
        for i, ue_id in enumerate(ch.ue_ids):
            order = sorted(range(len(ch.cell_ids)), key=lambda j: (-ch.gains_linear[i, j], ch.cell_ids[j]))
            out[ue_id] = [CandidateCell(cell_id=ch.cell_ids[j], link_available=bool(ch.gains_linear[i, j] > 0),
                                        link_gain_db=float(ch.gains_db[i, j]), rank=r + 1)
                          for r, j in enumerate(order[:self.scenario.candidate_k]) if ch.gains_linear[i, j] > 0]
        return out

    def baseline(self) -> Association:
        return Association(assignments={u: cs[0].cell_id for u, cs in self.candidate_cells().items()})

    def evaluate(self, association: Association, *, p5_floor: float | None = None,
                 channel_reused: bool = True) -> AssociationEvaluation:
        t0 = time.perf_counter(); ch = self.realize_channel(); cells = self.scenario.cells
        candidates = self.candidate_cells()
        if set(association.assignments) != set(ch.ue_ids): raise ValueError("association must cover every UE exactly once")
        cid = {c.cell_id: i for i, c in enumerate(cells)}
        counts = {c.cell_id: 0 for c in cells}
        for ue in ch.ue_ids:
            cell = association.assignments[ue]
            if cell not in cid: raise ValueError(f"invalid serving cell {cell}")
            if cell not in {x.cell_id for x in candidates[ue]}: raise ValueError(f"{ue} serving cell not in candidates")
            counts[cell] += 1
        k = 1.380649e-23 * 290.0 * 100e6 * (10 ** (7.0 / 10.0))
        tx = np.array([10 ** ((c.tx_power_dbm - 30) / 10) for c in cells])
        ue_metrics=[]
        for i, ue in enumerate(ch.ue_ids):
            s = cid[association.assignments[ue]]; rx = ch.gains_linear[i] * tx
            signal = rx[s]; interference = float(rx.sum() - signal); sinr = signal / (k + interference)
            eff = math.log2(1 + max(sinr, 0.0)); share = 1.0 / counts[association.assignments[ue]]
            throughput = eff * self.scenario.bandwidth_hz * share / 1e6
            ue_metrics.append(UeMetrics(ue_id=ue, serving_cell_id=association.assignments[ue],
                throughput_mbps=throughput, link_gain_db=float(ch.gains_db[i,s]),
                sinr_db=float(10*math.log10(max(sinr,1e-30))), resource_share=share))
        values=np.asarray([u.throughput_mbps for u in ue_metrics], dtype=float)
        p5=float(np.percentile(values,5,method="linear")); net=float(values.sum()); avg=float(values.mean())
        per=[]
        for c in cells:
            v=[u.throughput_mbps for u in ue_metrics if u.serving_cell_id==c.cell_id]
            per.append(CellMetrics(cell_id=c.cell_id, associated_ue_count=len(v), throughput_mbps=float(sum(v)),
                                   average_ue_throughput_mbps=float(np.mean(v)) if v else 0.0))
        feasible=p5_floor is None or p5 + 1e-9 >= p5_floor
        return AssociationEvaluation(association=association, association_hash=association.sha256(ch.ue_ids),
            network_throughput_mbps=net, average_ue_throughput_mbps=avg, p5_ue_throughput_mbps=p5,
            cell_metrics=per, ue_metrics=ue_metrics, p5_floor_mbps=p5_floor,
            p5_margin_mbps=None if p5_floor is None else p5-p5_floor, feasible=feasible,
            channel_reused=channel_reused, runtime_seconds=time.perf_counter()-t0)
