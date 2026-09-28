"""系统级测试共用场景构造 / Shared system-level test scenario builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import yaml

from evaluation.kpi import default_kpi_registry
from optimization import default_optimizer_registry
from system_optimization import (
    BenchmarkProtocolRegistry,
    FileSystemOptimizationStore,
    SystemOptimizationService,
    default_system_objective_registry,
    default_system_parameter_catalog,
)
from system_optimization.protocols import SYSTEM_BENCHMARK_V0_1_PROTOCOL
from system_simulation import (
    Capability,
    FileSystemExperimentStore,
    ModelType,
    SystemBackendDescriptor,
    SystemBackendRegistry,
    SystemExperimentService,
    SystemScenario,
    SystemScenarioCatalog,
)
from system_simulation.fake_backend import FAKE_SYSTEM_BACKEND_ID, FakeSystemBackend

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


# ---------------------------------------------------------------------------
# Day 6 system optimization builders
# ---------------------------------------------------------------------------

TEST_PROTOCOL_ID = "SYSTEM_BENCHMARK_TEST"


def make_test_protocol(**overrides: Any):
    return SYSTEM_BENCHMARK_V0_1_PROTOCOL.model_copy(
        update={"protocol_id": TEST_PROTOCOL_ID, "simulation_slots": 10, "warmup_slots": 0, **overrides}
    )


def beta_tradeoff_scale(scenario: SystemScenario, ue_index: int) -> float:
    """网络吞吐率随 β 增大而增大，最弱 UE（UE-001）随 β 增大而减小 —— 用于验证负向 trade-off 保留。"""
    beta = scenario.simulation.scheduler.beta
    return 1.0 - 0.5 * beta if ue_index == 0 else 1.0 + beta


def fake_registry(bits_scale=beta_tradeoff_scale, capabilities=None, fail_beta: float | None = None):
    def scale(scenario: SystemScenario, ue_index: int) -> float:
        if fail_beta is not None and scenario.simulation.scheduler.beta == fail_beta:
            raise RuntimeError(f"injected failure at beta={fail_beta}")
        return bits_scale(scenario, ue_index)

    registry = SystemBackendRegistry()
    registry.register(SystemBackendDescriptor(
        id=FAKE_SYSTEM_BACKEND_ID, name_zh="假后端", name_en="Fake", factory=lambda: FakeSystemBackend(scale),
        capabilities=capabilities or (Capability.SYSTEM_SIMULATION, Capability.UE_METRICS, Capability.THROUGHPUT,
                                      Capability.CHANNEL_REUSE),
        model_type=ModelType.TEST_FIXTURE, source_type="test_fixture", provider="fixture",
    ))
    return registry


def make_optimization_service(tmp_path, registry=None, protocol=None, **scenario_overrides: Any):
    write_scenario(tmp_path / "configs", **scenario_overrides)
    experiments = SystemExperimentService(
        store=FileSystemExperimentStore(tmp_path / "system_experiments"),
        registry=registry or fake_registry(),
        catalog=SystemScenarioCatalog(tmp_path / "configs"),
        kpis=default_kpi_registry(),
        platform_version="test",
    )
    return SystemOptimizationService(
        experiments=experiments,
        store=FileSystemOptimizationStore(tmp_path / "system_optimizations"),
        optimizers=default_optimizer_registry(),
        objectives=default_system_objective_registry(),
        protocols=BenchmarkProtocolRegistry([protocol or make_test_protocol()]),
        parameters=default_system_parameter_catalog(),
        git_commit="test",
        runner=lambda fn: fn(),
    )
