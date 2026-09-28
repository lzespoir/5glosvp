"""
Sionna RT → Sionna SYS 系统级集成测试（真实后端）/ Real Sionna system-level integration test.

不断言固定数值：GPU 光线追踪存在微小数值漂移，经 OLLA/HARQ 放大后单 UE 吞吐率有百分比级差异。
"""

import math
from pathlib import Path

import numpy as np
import pytest

from evaluation.kpi import (
    AVG_UE_THROUGHPUT_V0_1,
    NETWORK_THROUGHPUT_V0_1,
    P5_UE_THROUGHPUT_V0_1,
    UE_THROUGHPUT_V0_1,
    default_kpi_registry,
)
from simulation.backends.system import default_system_registry
from system_simulation import (
    FileSystemExperimentStore,
    SystemExperimentService,
    SystemExperimentStatus,
    SystemScenarioCatalog,
)
from system_helpers import write_scenario

REPO_ROOT = Path(__file__).resolve().parents[1]
_HEALTH = default_system_registry().get("sionna_system").factory().health_check()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.sionna,
    pytest.mark.skipif(not _HEALTH["available"], reason=f"Sionna SYS unavailable: {_HEALTH['errors']}"),
]


@pytest.fixture(scope="module")
def record(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sys")
    demo = SystemScenarioCatalog(REPO_ROOT / "configs" / "system").get("SYSTEM-DEMO-001")
    small = demo.model_dump(mode="json")
    small["simulation"]["num_slots"] = 20
    small["ue_generator"]["count"] = 3
    write_scenario(tmp / "configs", **{**small, "scenario_id": "SYSTEM-IT-001"})
    service = SystemExperimentService(FileSystemExperimentStore(tmp / "data"), default_system_registry(),
                                      SystemScenarioCatalog(tmp / "configs"), default_kpi_registry(), "test", None)
    return service.create("integration", "SYSTEM-IT-001")


def test_sionna_system_run_succeeds(record):
    assert record.status is SystemExperimentStatus.SUCCEEDED, record.error
    r = record.result
    assert r.backend == "sionna_system" and r.backend_version
    assert len(r.ue_results) == 3
    assert r.scheduler["provider"] == "sionna_sys" and r.link_adaptation["provider"] == "sionna_sys"
    assert r.ue_generation["kept_candidate_indices"] and len(r.ue_generation["kept_candidate_indices"]) == 3


def test_throughput_finite_and_consistent(record):
    kpis = {k.metric_id: k for k in record.kpis}
    tput = np.array([u.throughput_mbps for u in record.result.ue_results])
    assert np.all(np.isfinite(tput)) and np.all(tput >= 0) and tput.sum() > 0
    assert kpis[UE_THROUGHPUT_V0_1].per_ue == {u.ue_id: u.throughput_mbps for u in record.result.ue_results}
    assert kpis[NETWORK_THROUGHPUT_V0_1].value == pytest.approx(tput.sum())
    assert kpis[AVG_UE_THROUGHPUT_V0_1].value == pytest.approx(tput.mean())
    assert kpis[P5_UE_THROUGHPUT_V0_1].value == pytest.approx(np.percentile(tput, 5))


def test_resources_and_phy_quantities(record):
    r = record.result
    assert sum(u.allocated_re_share for u in r.ue_results) == pytest.approx(1.0, abs=1e-6)
    for u in r.ue_results:
        assert math.isfinite(u.mean_channel_gain_db)
        assert u.acked_slots <= u.scheduled_slots <= r.num_slots
        if u.scheduled_slots:
            assert math.isfinite(u.sinr_eff_db_mean) and 0 <= u.mcs_index_mean <= 28


def test_provenance_not_fixture_not_measured(record):
    assert record.provenance["source_type"] == "simulation"
    assert record.provenance["model_type"] == "sionna_sys"
    assert record.provenance["measured"] is False
    for k in record.kpis:
        assert k.source_type == "simulation" and k.measured is False and k.backend == "sionna_system"
