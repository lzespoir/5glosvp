"""系统级测试共用场景构造 / Shared system-level test scenario builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import yaml

from system_simulation import SystemScenario

BASE_SCENARIO: dict[str, Any] = {
    "scenario_id": "SYSTEM-TEST-001",
    "name_zh": "测试系统场景",
    "name_en": "Test System Scenario",
    "backend": "fake_system",
    "scene": "etoile",
    "seed": 7,
    "base_stations": [{"bs_id": "BS-001", "position": [0.0, 0.0, 30.0]}],
    "cells": [{
        "cell_id": "CELL-001", "bs_id": "BS-001", "carrier_frequency_hz": 3.5e9, "bandwidth_hz": 100e6,
        "tx_power_dbm": 44.0, "antenna": {"num_rows": 2, "num_cols": 4},
    }],
    "ue_generator": {"count": 4, "seed": 7, "area_center": [0.0, 0.0], "area_size": [200.0, 100.0]},
    "simulation": {"num_slots": 10},
}


def scenario_dict(**overrides: Any) -> dict[str, Any]:
    data = deepcopy(BASE_SCENARIO)
    data.update(overrides)
    return data


def make_scenario(**overrides: Any) -> SystemScenario:
    return SystemScenario.model_validate(scenario_dict(**overrides))


def write_scenario(directory, **overrides: Any) -> None:
    data = scenario_dict(**overrides)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{data['scenario_id'].lower()}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
