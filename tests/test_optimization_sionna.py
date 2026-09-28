"""
真实 Sionna RT 优化集成测试：基线 + 2 个不同发射功率候选（小网格以控制耗时）。
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.app import create_app
from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from optimization import (
    FileOptimizationStore,
    OptimizationService,
    default_objective_registry,
    default_optimizer_registry,
)
from simulation.backends import SionnaBackend, default_registry

pytestmark = [
    pytest.mark.integration,
    pytest.mark.sionna,
    pytest.mark.skipif(
        not SionnaBackend().health_check()["available"], reason="Sionna RT backend not available"
    ),
]

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_real_sionna_grid_search(tmp_path):
    data = yaml.safe_load((REPO_ROOT / "configs" / "sionna_demo.yaml").read_text(encoding="utf-8"))
    data["radio_map"].update(cell_size=[20.0, 20.0], samples_per_tx=200_000)
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "demo.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    experiments = ExperimentService(
        FileExperimentStore(tmp_path / "experiments"), default_registry(), ScenarioCatalog(configs)
    )
    optimizations = OptimizationService(
        experiments, FileOptimizationStore(tmp_path / "optimizations"),
        default_optimizer_registry(), default_objective_registry(),
    )
    with TestClient(create_app(experiments, optimization_service=optimizations)) as client:
        resp = client.post(
            "/api/v1/optimizations",
            json={
                "name": "Sionna Grid Search 集成测试",
                "scenario_id": "SIONNA-DEMO-001",
                "optimizer_id": "grid_search",
                "objective_id": "PROPAGATION_UTILITY_V0_1",
                "parameter_space": {"tx_power_dbm": [38, 46]},
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "succeeded", body.get("error")
        assert body["provenance"]["source_type"] == "simulation"
        assert body["provenance"]["simulation_backend"] == "sionna_rt"

        runs = [body["baseline"], *body["candidates"]]
        exp_ids = [c["experiment_id"] for c in runs]
        assert len(set(exp_ids)) == 3  # 44 dBm 基线不在搜索空间中，三次独立仿真
        for exp_id in exp_ids:
            png = client.get(f"/api/v1/experiments/{exp_id}/artifacts/radio_map.png")
            assert png.status_code == 200 and png.content[:4] == b"\x89PNG"

        coverage = {c["parameters"]["tx_power_dbm"]: c["objective"]["components"]["sinr_coverage_ratio"] for c in runs}
        assert all(0.0 < v <= 1.0 for v in coverage.values())
        # 物理一致性：同一几何与种子下，更高发射功率的 SINR 覆盖不会更低
        assert coverage[38.0] <= coverage[44.0] <= coverage[46.0]

        values = {c["candidate_id"]: c["objective"]["value"] for c in body["candidates"]}
        assert body["best_candidate"]["candidate_id"] == max(values, key=lambda k: values[k])
        cmp = body["comparison"]
        assert cmp["absolute_improvement"] == pytest.approx(cmp["optimized_objective"] - cmp["baseline_objective"])
