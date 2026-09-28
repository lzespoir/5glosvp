"""
真实 Sionna RT 的 API 集成测试 / API integration test against real Sionna RT.
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.app import create_app
from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from simulation.backends import SionnaBackend, default_registry

pytestmark = [
    pytest.mark.integration,
    pytest.mark.sionna,
    pytest.mark.skipif(
        not SionnaBackend().health_check()["available"], reason="Sionna RT backend not available"
    ),
]

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_real_sionna_experiment_via_api(tmp_path):
    data = yaml.safe_load((REPO_ROOT / "configs" / "sionna_demo.yaml").read_text(encoding="utf-8"))
    data["radio_map"].update(cell_size=[20.0, 20.0], samples_per_tx=100_000)
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "demo.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    service = ExperimentService(
        FileExperimentStore(tmp_path / "experiments"), default_registry(), ScenarioCatalog(configs)
    )
    with TestClient(create_app(service)) as client:
        backends = {b["id"]: b for b in client.get("/api/v1/backends").json()["items"]}
        assert backends["sionna_rt"]["available"] is True
        assert "fake" not in backends

        resp = client.post(
            "/api/v1/experiments", json={"name": "Sionna API 集成测试", "scenario_id": "SIONNA-DEMO-001"}
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "succeeded", body.get("error")
        assert body["backend"]["id"] == "sionna_rt" and body["backend"]["version"]
        assert body["metrics"]["radio_map"]["num_covered_cells"] > 0
        prov = body["provenance"]
        assert prov["source_type"] == "simulation" and prov["engine"] == "Sionna RT"
        assert prov["generated"] is True and prov["measured"] is False
        assert prov["data_type_en"] == "Simulation Generated"

        png = client.get(f"/api/v1/experiments/{body['experiment_id']}/artifacts/radio_map.png")
        assert png.status_code == 200 and png.content[:4] == b"\x89PNG"
