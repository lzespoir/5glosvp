from pathlib import Path

import numpy as np
import pytest

from scenarios.amatrix import profile_file
from scenarios.catalog import ScenarioCatalog
from scenarios.combination import scenario_from_dimensions
from scenarios.contracts import BEAM_SPACE_TRAFFIC_ADAPTER, UETwin
from scenarios.service import ScenarioSystemService
from scenarios.verifier import verify_catalog

pytestmark = pytest.mark.unit


def test_taxonomy_and_real_semantic_catalog_are_separate_from_seed():
    service = ScenarioSystemService(ScenarioCatalog(materialized_limit=120))
    assert service.taxonomy().taxonomy_version == "0.1"
    assert len(service.catalog.definitions()) == 120
    assert service.catalog.counts().materialized_count == 120
    first = service.catalog.definitions()[0]
    second = service.materialize(first.scenario_id, seed=999).scenario_instance
    assert first.scenario_id == second.scenario_id
    assert first.scenario_definition_hash == second.scenario_definition_hash
    assert second.scenario_instance_id != service.materialize(first.scenario_id, seed=1000).scenario_instance.scenario_instance_id


def test_rules_distinguish_invalid_and_external_asset():
    service = ScenarioSystemService()
    invalid = service.preview({"network_function": ["handover"], "topology": ["single_site_single_cell"], "mobility": ["mobile"]})
    assert invalid.counts.invalid_count == invalid.counts.theoretical_count
    external = service.preview({"traffic": ["beam_space_traffic"]})
    assert external.counts.requires_external_asset_count > 0
    assert all(item.compatibility_status == "REQUIRES_EXTERNAL_ASSET" for item in external.combinations[:3])


def test_canonical_hash_and_independent_verifier_detect_tamper():
    service = ScenarioSystemService(ScenarioCatalog(materialized_limit=8))
    definitions = list(service.catalog.definitions())
    assert verify_catalog(definitions)["verified"] is True
    definitions[0] = definitions[0].model_copy(update={"scenario_definition_hash": "0" * 64})
    result = verify_catalog(definitions)
    assert result["verified"] is False
    assert definitions[0].scenario_id in result["mismatches"]


def test_amatrix_profile_is_read_only_contract(tmp_path: Path):
    path = tmp_path / "sample.npy"
    np.save(path, {"SSB": {"entry": np.ones((2, 3), dtype=np.float64)}})
    before = path.read_bytes()
    artifact = profile_file(path)
    assert path.read_bytes() == before
    assert artifact.artifact_type == "A_MATRIX"
    assert artifact.leaf_shape_groups == {"[2, 3]": 1}
    assert artifact.unit == "UNKNOWN"


def test_scenario_workspace_contains_experiment_identity():
    service = ScenarioSystemService(ScenarioCatalog(materialized_limit=4))
    scenario = service.catalog.definitions()[0]
    workspace = service.materialize(scenario.scenario_id, seed=42)
    assert workspace.experiment_identity == {
        "scenario_id": scenario.scenario_id,
        "scenario_version": "0.1",
        "scenario_definition_hash": scenario.scenario_definition_hash,
        "scenario_instance_id": workspace.scenario_instance.scenario_instance_id,
    }


def test_ue_twin_and_metric_provenance_contracts_do_not_fake_radio_metrics():
    ue = UETwin(
        ue_id="UE-1",
        position=[1.0, 2.0],
        serving_cell_id="CELL-1",
        neighbor_cell_ids=["CELL-2"],
        candidate_cells=["CELL-1", "CELL-2"],
        traffic_profile="full_buffer",
        radio_metrics=[{"metric_id": "rsrp", "value": None, "unit": "UNKNOWN", "source": "UNKNOWN"}],
    )
    assert ue.radio_metrics[0].source == "UNKNOWN"
    assert BEAM_SPACE_TRAFFIC_ADAPTER.source_type == "REQUIRES_EXTERNAL_MODEL"
