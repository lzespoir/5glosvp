"""KPI 引擎单元测试 / KPI engine unit tests."""

import numpy as np
import pytest

from evaluation.kpi import (
    ALL_DEFINITIONS,
    AVG_UE_THROUGHPUT_V0_1,
    NETWORK_THROUGHPUT_V0_1,
    P5_UE_THROUGHPUT_V0_1,
    UE_THROUGHPUT_V0_1,
    KpiContext,
    KpiNotFoundError,
    UeThroughputInput,
    default_kpi_registry,
)

pytestmark = pytest.mark.unit

CTX = KpiContext(source_experiment="EXP-0000ABCD", backend="fake_system", scenario_id="S", seed=1,
                 source_type="test_fixture")
DURATION_S = 0.1


def _inputs(mbps: list[float]) -> list[UeThroughputInput]:
    return [UeThroughputInput(ue_id=f"UE-{i}", decoded_bits=round(v * 1e6 * DURATION_S),
                              simulated_duration_s=DURATION_S) for i, v in enumerate(mbps)]


def _by_id(mbps: list[float]):
    return {k.metric_id: k for k in default_kpi_registry().evaluate(_inputs(mbps), CTX)}


def test_ue_throughput_is_decoded_bits_over_time():
    ue = _by_id([12.5])[UE_THROUGHPUT_V0_1]
    assert ue.per_ue == {"UE-0": pytest.approx(12.5)}
    assert ue.value is None and ue.scope.value == "ue"


def test_network_throughput_is_sum():
    assert _by_id([10, 20, 30.5])[NETWORK_THROUGHPUT_V0_1].value == pytest.approx(60.5)


def test_average_ue_throughput():
    assert _by_id([10, 20, 30])[AVG_UE_THROUGHPUT_V0_1].value == pytest.approx(20.0)


def test_p5_ue_throughput_linear_percentile():
    values = [5, 10, 20, 40, 80, 160]
    # 线性插值：rank = 0.05 × (n−1) = 0.25 → 5 + 0.25 × (10 − 5)
    assert _by_id(values)[P5_UE_THROUGHPUT_V0_1].value == pytest.approx(6.25)
    assert _by_id(values)[P5_UE_THROUGHPUT_V0_1].value == pytest.approx(np.percentile(values, 5))


def test_p5_includes_zero_throughput_ue():
    kpis = _by_id([0, 10, 20, 30])
    assert kpis[P5_UE_THROUGHPUT_V0_1].value == pytest.approx(0.05 * 3 * 10)
    assert kpis[P5_UE_THROUGHPUT_V0_1].sample_size == 4
    assert kpis[UE_THROUGHPUT_V0_1].per_ue["UE-0"] == 0.0


def test_empty_population_is_unavailable_not_zero():
    for k in default_kpi_registry().evaluate([], CTX):
        assert k.available is False
        assert k.value is None and k.per_ue is None
        assert k.unavailable_reason and k.sample_size == 0


def test_units_are_mbps():
    for k in default_kpi_registry().evaluate(_inputs([1, 2]), CTX):
        assert k.unit == "Mbps"
    assert {d.unit for d in ALL_DEFINITIONS} == {"Mbps"}


def test_versions_and_definitions_frozen():
    registry = default_kpi_registry()
    ids = [d.id for d in registry.definitions()]
    assert ids == [UE_THROUGHPUT_V0_1, NETWORK_THROUGHPUT_V0_1, AVG_UE_THROUGHPUT_V0_1, P5_UE_THROUGHPUT_V0_1]
    for d in registry.definitions():
        assert d.version == "0.1" and d.id.endswith("_V0_1")
        assert d.acceptance_kpi is False
        assert d.doc.startswith("docs/kpi/")
    with pytest.raises(Exception):
        registry.definitions()[0].formula = "changed"  # type: ignore[misc]
    with pytest.raises(KpiNotFoundError):
        registry.get("EDGE_USER_RATE_ACCEPTANCE")


def test_p5_definition_carries_edge_rate_note():
    note = default_kpi_registry().get(P5_UE_THROUGHPUT_V0_1).note_zh
    assert note and "边缘用户速率" in note


def test_provenance_fields():
    for k in default_kpi_registry().evaluate(_inputs([1, 2, 3]), CTX):
        assert k.source_experiment == "EXP-0000ABCD"
        assert k.backend == "fake_system" and k.scenario_id == "S" and k.seed == 1
        assert k.source_type == "test_fixture"
        assert k.measured is False and k.acceptance_kpi is False
        assert k.calculation_method and k.version == "0.1"


def test_unavailable_propagates_reason():
    kpis = default_kpi_registry().evaluate([], CTX)
    reasons = {k.unavailable_reason for k in kpis}
    assert len(reasons) == 1


def test_negative_bits_rejected():
    with pytest.raises(ValueError):
        UeThroughputInput(ue_id="x", decoded_bits=-1, simulated_duration_s=1)
    with pytest.raises(ValueError):
        UeThroughputInput(ue_id="x", decoded_bits=1, simulated_duration_s=0)
