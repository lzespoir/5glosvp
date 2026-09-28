"""
FakeSystemBackend —— 仅用于软件单元 / API / 前端测试的确定性系统级假后端。

输出 source_type = test_fixture，禁止作为 Reference System Result。
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from .base import SystemRunOutput, SystemSimulationBackend
from .models import SystemScenario, SystemSimulationResult, UserEquipmentResult
from .ue_generation import generate_candidates, ue_id_for

FAKE_SYSTEM_BACKEND_ID = "fake_system"
# 每个 UE 每时隙固定译码比特数：UE i → FIXTURE_BITS_PER_SLOT × (i + 1)
FIXTURE_BITS_PER_SLOT = 10_000
FIXTURE_SINR_BASE_DB = 5.0
FIXTURE_SINR_STEP_DB = 3.0


class FakeSystemBackend(SystemSimulationBackend):
    @property
    def name(self) -> str:
        return FAKE_SYSTEM_BACKEND_ID

    def health_check(self) -> dict[str, Any]:
        return {"available": True, "version": "fixture", "errors": [], "warnings": ["Software test fixture"]}

    def run(self, scenario: SystemScenario, experiment_id: str, log: logging.Logger) -> SystemRunOutput:
        sim = scenario.simulation
        cell = scenario.cells[0]
        if scenario.ue_generator:
            positions = generate_candidates(scenario.ue_generator)[: scenario.ue_generator.count].tolist()
            ids = [ue_id_for(i) for i in range(len(positions))]
        else:
            positions = [u.position for u in scenario.ues]
            ids = [u.ue_id for u in scenario.ues]
        n, slots = len(ids), sim.num_slots
        num_re = sim.num_data_symbols_per_slot * sim.num_subcarriers
        re_share = np.full(n, num_re // n, dtype=float)
        re_share[0] += num_re - re_share.sum()
        trace = {
            "decoded_bits": np.tile([FIXTURE_BITS_PER_SLOT * (i + 1) for i in range(n)], (slots, 1)).astype(float),
            "harq": np.ones((slots, n)),
            "mcs": np.tile([float(5 + i) for i in range(n)], (slots, 1)),
            "sinr_eff_db": np.tile([FIXTURE_SINR_BASE_DB + FIXTURE_SINR_STEP_DB * i for i in range(n)], (slots, 1)),
            "num_re": np.tile(re_share, (slots, 1)),
            "tx_power_w": np.full((slots, n), 1.0),
        }
        log.info("FakeSystemBackend: %d UEs, %d slots (TEST FIXTURE)", n, slots)
        ues = [
            UserEquipmentResult(
                ue_id=ids[i],
                serving_cell_id=cell.cell_id,
                position=list(positions[i]),
                mean_channel_gain_db=None,
                sinr_eff_db_mean=float(trace["sinr_eff_db"][0, i]),
                mcs_index_mean=float(trace["mcs"][0, i]),
                scheduled_slots=slots,
                acked_slots=slots,
                tbler=0.0,
                allocated_re_per_slot_mean=float(re_share[i]),
                allocated_re_share=float(re_share[i] / num_re),
                tx_power_w_mean=1.0,
                decoded_bits=int(trace["decoded_bits"][:, i].sum()),
                simulated_duration_s=sim.simulated_duration_s,
                unavailable={"mean_channel_gain_db": "测试夹具不计算传播 / Test fixture has no propagation"},
            )
            for i in range(n)
        ]
        result = SystemSimulationResult(
            scenario_id=scenario.scenario_id,
            backend=FAKE_SYSTEM_BACKEND_ID,
            backend_version="fixture",
            seed=scenario.seed,
            num_slots=slots,
            slot_duration_s=sim.slot_duration_s,
            simulated_duration_s=sim.simulated_duration_s,
            num_data_re_per_slot=num_re,
            ue_results=ues,
            scheduler={"id": "fixture_equal_share", "name": "Equal RE share (test fixture)", "provider": "fixture"},
            link_adaptation={"id": "fixture_fixed_mcs", "provider": "fixture"},
            power_control={"id": "fixture_equal_power", "provider": "fixture"},
            ue_generation=scenario.ue_generator.model_dump(mode="json") if scenario.ue_generator else None,
            compute_device="cpu",
        )
        return SystemRunOutput(result=result, slot_trace=trace)
