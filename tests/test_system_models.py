"""系统级统一领域模型测试 / Canonical system domain model tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from system_simulation import (
    Capability,
    ModelType,
    SystemBackendDescriptor,
    SystemScenario,
    SystemScenarioCatalog,
    SystemSimulationResult,
    UserEquipmentConfig,
    UserEquipmentResult,
)
from system_simulation.fake_backend import FakeSystemBackend
from system_helpers import make_scenario, scenario_dict

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_system_scenario_model():
    s = make_scenario()
    assert s.ue_count == 4
    assert s.traffic.type.value == "full_buffer" and s.traffic.tag == "[A]"
    assert s.cell_position(s.cells[0]) == [0.0, 0.0, 30.0]
    assert s.simulation.num_subcarriers == 273 * 12
    assert s.simulation.simulated_duration_s == pytest.approx(10 * 0.5e-3)


def test_system_scenario_requires_exactly_one_ue_source():
    with pytest.raises(ValidationError):
        SystemScenario.model_validate(scenario_dict(ue_generator=None))
    with pytest.raises(ValidationError):
        SystemScenario.model_validate(scenario_dict(ues=[{"ue_id": "UE-1", "position": [1, 2, 1.5]}]))


def test_system_scenario_rejects_unknown_references():
    bad_cell = scenario_dict()
    bad_cell["cells"][0]["bs_id"] = "BS-404"
    with pytest.raises(ValidationError, match="unknown base station"):
        SystemScenario.model_validate(bad_cell)
    with pytest.raises(ValidationError, match="unknown cell"):
        SystemScenario.model_validate(scenario_dict(
            ue_generator=None, ues=[{"ue_id": "UE-1", "position": [1, 2, 1.5], "serving_cell_id": "CELL-404"}]))


def test_ue_generator_count_bounds():
    for count in (0, 11):
        data = scenario_dict()
        data["ue_generator"]["count"] = count
        with pytest.raises(ValidationError):
            SystemScenario.model_validate(data)


def test_ue_config_model():
    ue = UserEquipmentConfig(ue_id="UE-001", position=[1.0, 2.0, 1.5])
    assert ue.serving_cell_id is None
    with pytest.raises(ValidationError):
        UserEquipmentConfig(ue_id="UE-001", position=[1.0, 2.0])
    with pytest.raises(ValidationError):
        UserEquipmentConfig(ue_id="UE-001", position=[1.0, 2.0, 1.5], unknown_field=1)


def test_ue_result_model():
    ue = UserEquipmentResult(ue_id="UE-001", serving_cell_id="CELL-001", position=[0, 0, 1.5], scheduled_slots=0,
                             acked_slots=0, allocated_re_per_slot_mean=0.0, allocated_re_share=0.0, decoded_bits=0,
                             simulated_duration_s=0.1, unavailable={"sinr_eff_db_mean": "never scheduled"})
    assert ue.sinr_eff_db_mean is None and ue.mcs_index_mean is None
    assert ue.throughput_mbps is None  # 由 KPI 引擎填写，不在模型中默认为 0
    assert "sinr_eff_db_mean" in ue.unavailable


def test_system_result_model():
    result = FakeSystemBackend().run(make_scenario(), "EXP-00000000", _NullLog()).result
    data = SystemSimulationResult.model_validate(result.model_dump(mode="json"))
    assert data.backend == "fake_system" and len(data.ue_results) == 4
    assert data.simulated_duration_s == pytest.approx(data.num_slots * data.slot_duration_s)


def test_backend_capabilities():
    d = SystemBackendDescriptor(id="x", name_zh="x", name_en="x", factory=FakeSystemBackend,
                                capabilities=(Capability.SYSTEM_SIMULATION, Capability.THROUGHPUT),
                                model_type=ModelType.TEST_FIXTURE)
    assert d.supports(Capability.THROUGHPUT)
    assert not d.supports(Capability.RADIO_MAP)
    assert d.category == "system"


def test_unknown_backend_capability():
    with pytest.raises(ValueError, match="Unknown backend capability"):
        SystemBackendDescriptor(id="x", name_zh="x", name_en="x", factory=FakeSystemBackend,
                                capabilities=("teleportation",),  # type: ignore[arg-type]
                                model_type=ModelType.TEST_FIXTURE)
    with pytest.raises(ValueError):
        Capability("teleportation")


def test_demo_system_scenario_loads():
    catalog = SystemScenarioCatalog(REPO_ROOT / "configs" / "system")
    s = catalog.get("SYSTEM-DEMO-001")
    assert s.backend == "sionna_system"
    assert len(s.base_stations) == 1 and len(s.cells) == 1 and s.ue_count == 6
    assert s.cells[0].carrier_frequency_hz == 3.5e9 and s.cells[0].bandwidth_hz == 100e6
    assert s.ue_generator is not None and s.ue_generator.seed == s.seed


class _NullLog:
    def info(self, *args, **kwargs):
        pass
