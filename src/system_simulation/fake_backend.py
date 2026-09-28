"""
FakeSystemBackend —— 仅用于软件单元 / API / 前端测试的确定性系统级假后端。

输出 source_type = test_fixture，禁止作为 Reference System Result。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np

from .base import ChannelRealization, SystemRunOutput, SystemSimulationBackend
from .errors import InvalidSystemScenarioError
from .models import SystemScenario, SystemSimulationResult, UserEquipmentResult
from .realization import propagation_fingerprint
from .ue_generation import generate_candidates, ue_id_for

FAKE_SYSTEM_BACKEND_ID = "fake_system"
FAKE_PROVIDER = "fixture"
# 每个 UE 每时隙固定译码比特数：UE i → FIXTURE_BITS_PER_SLOT × (i + 1) × bits_scale(scenario, i)
FIXTURE_BITS_PER_SLOT = 10_000
FIXTURE_SINR_BASE_DB = 5.0
FIXTURE_SINR_STEP_DB = 3.0
FIXTURE_GAIN_BASE_DB = -90.0
FIXTURE_GAIN_STEP_DB = -5.0

BitsScale = Callable[[SystemScenario, int], float]


def _unit_scale(scenario: SystemScenario, ue_index: int) -> float:
    return 1.0


class FakeSystemBackend(SystemSimulationBackend):
    """bits_scale 让测试注入确定性的参数响应（例如随 scheduler beta 变化）。"""

    def __init__(self, bits_scale: BitsScale = _unit_scale) -> None:
        self._bits_scale = bits_scale

    @property
    def name(self) -> str:
        return FAKE_SYSTEM_BACKEND_ID

    def health_check(self) -> dict[str, Any]:
        return {"available": True, "version": "fixture", "errors": [], "warnings": ["Software test fixture"]}

    def realize_channel(self, scenario: SystemScenario, log: logging.Logger) -> ChannelRealization:
        cell = scenario.cells[0]
        if scenario.ue_generator:
            positions = generate_candidates(scenario.ue_generator)[: scenario.ue_generator.count]
            ids = [ue_id_for(i) for i in range(len(positions))]
        else:
            positions = np.array([u.position for u in scenario.ues], dtype=float)
            ids = [u.ue_id for u in scenario.ues]
        gain_linear = (10 ** (np.array([FIXTURE_GAIN_BASE_DB + FIXTURE_GAIN_STEP_DB * i for i in range(len(ids))])
                              / 10)).astype(np.float32)
        return ChannelRealization(
            ue_ids=tuple(ids),
            serving_cell_ids=tuple(cell.cell_id for _ in ids),
            positions=np.asarray(positions, dtype=float),
            mean_channel_gain_db=10 * np.log10(gain_linear.astype(float)),
            arrays={"gain_linear": gain_linear},
            provider=FAKE_PROVIDER,
            provider_versions={"fixture": "fixture"},
            propagation_fingerprint=propagation_fingerprint(scenario),
            metadata={"ue_generation": scenario.ue_generator.model_dump(mode="json") if scenario.ue_generator
                      else None},
        )

    def run(
        self,
        scenario: SystemScenario,
        experiment_id: str,
        log: logging.Logger,
        channel: ChannelRealization | None = None,
    ) -> SystemRunOutput:
        sim = scenario.simulation
        reused = channel is not None
        if channel is None:
            channel = self.realize_channel(scenario, log)
        elif channel.propagation_fingerprint != propagation_fingerprint(scenario):
            raise InvalidSystemScenarioError("Channel realization was generated for different propagation conditions")
        ids = list(channel.ue_ids)
        n, slots = len(ids), sim.num_slots
        num_re = sim.num_data_symbols_per_slot * sim.num_subcarriers
        re_share = np.full(n, num_re // n, dtype=float)
        re_share[0] += num_re - re_share.sum()
        bits = [FIXTURE_BITS_PER_SLOT * (i + 1) * self._bits_scale(scenario, i) for i in range(n)]
        trace = {
            "decoded_bits": np.tile(bits, (slots, 1)).astype(float),
            "harq": np.ones((slots, n)),
            "mcs": np.tile([float(5 + i) for i in range(n)], (slots, 1)),
            "sinr_eff_db": np.tile([FIXTURE_SINR_BASE_DB + FIXTURE_SINR_STEP_DB * i for i in range(n)], (slots, 1)),
            "num_re": np.tile(re_share, (slots, 1)),
            "tx_power_w": np.full((slots, n), 1.0),
        }
        window = slice(sim.warmup_slots, slots)
        measured = slots - sim.warmup_slots
        gain_db = 10 * np.log10(channel.arrays["gain_linear"].astype(float)) if "gain_linear" in channel.arrays \
            else channel.mean_channel_gain_db
        log.info("FakeSystemBackend: %d UEs, %d slots (TEST FIXTURE)", n, slots)
        ues = [
            UserEquipmentResult(
                ue_id=ids[i],
                serving_cell_id=channel.serving_cell_ids[i],
                position=[float(v) for v in channel.positions[i]],
                mean_channel_gain_db=float(gain_db[i]),
                sinr_eff_db_mean=float(trace["sinr_eff_db"][0, i]),
                mcs_index_mean=float(trace["mcs"][0, i]),
                scheduled_slots=measured,
                acked_slots=measured,
                tbler=0.0,
                allocated_re_per_slot_mean=float(re_share[i]),
                allocated_re_share=float(re_share[i] / num_re),
                tx_power_w_mean=1.0,
                decoded_bits=int(trace["decoded_bits"][window, i].sum()),
                simulated_duration_s=sim.simulated_duration_s,
            )
            for i in range(n)
        ]
        result = SystemSimulationResult(
            scenario_id=scenario.scenario_id,
            backend=FAKE_SYSTEM_BACKEND_ID,
            backend_version="fixture",
            seed=scenario.seed,
            num_slots=slots,
            warmup_slots=sim.warmup_slots,
            slot_duration_s=sim.slot_duration_s,
            simulated_duration_s=sim.simulated_duration_s,
            num_data_re_per_slot=num_re,
            ue_results=ues,
            scheduler={"id": "fixture_equal_share", "name": "Equal RE share (test fixture)",
                       "beta": sim.scheduler.beta, "provider": FAKE_PROVIDER},
            link_adaptation={"id": "fixture_fixed_mcs", "provider": FAKE_PROVIDER},
            power_control={"id": "fixture_equal_power", "provider": FAKE_PROVIDER},
            ue_generation=channel.metadata.get("ue_generation"),
            channel_reused=reused,
            compute_device="cpu",
        )
        return SystemRunOutput(result=result, slot_trace=trace)
