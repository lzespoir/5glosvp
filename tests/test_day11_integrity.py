from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit

from comparison.service import ComparisonIntent, ComparisonService
from comparison.verifier import ComparisonVerifier
from user_association.service import ScenarioNotFoundError, UserAssociationService


def test_missing_user_association_scenario_does_not_fallback(tmp_path):
    service = UserAssociationService(tmp_path)
    with pytest.raises(ScenarioNotFoundError):
        service.load("MULTICELL-DEMO-DOES-NOT-EXIST")


def _write_run(root, run_id, *, channel_hash="same-channel", algorithm_id="a", budget=8):
    path = root / f"{run_id}.json"
    path.write_text(json.dumps({
        "run_id": run_id, "status": "completed", "algorithm_id": algorithm_id,
        "algorithm_version": "1.0", "scenario_id": "MULTICELL-DEMO-001",
        "problem_type": "user_association", "dataset_id": "dataset", "dataset_version": "1.0", "dataset_hash": "dataset-hash",
        "scenario_version": "1.0", "scenario_hash": "scenario-hash",
        "channel_artifact_id": "CH-TEST", "channel_hash": channel_hash,
        "traffic_realization_id": "TRAFFIC-FULL-BUFFER", "traffic_hash": "traffic-hash",
        "objective_id": "objective", "objective_version": "1.0", "constraints_hash": "constraints-hash",
        "kpi_versions": {"network": "1.0"}, "protocol_id": "protocol", "protocol_version": "1.0",
        "evaluation_budget": budget, "backend_id": "backend", "backend_version": "1.0",
        "parameters": {"seed": 2026}, "provenance": {"provider": "sionna_multicell"},
    }), encoding="utf-8")


def test_comparison_preview_freezes_protocol_and_declares_algorithm_difference(tmp_path):
    runs = tmp_path / "reference" / "algorithm_onboarding" / "runs"
    runs.mkdir(parents=True)
    _write_run(runs, "R1", algorithm_id="baseline")
    _write_run(runs, "R2", algorithm_id="optimizer")
    service = ComparisonService(tmp_path)
    preview = service.preview(["R1", "R2"], ComparisonIntent.ALGORITHM_COMPARISON)
    assert preview["status"] == "comparable"
    assert preview["incompatible_dimensions"] == []


def test_comparison_preview_blocks_channel_mismatch_but_keeps_side_by_side(tmp_path):
    runs = tmp_path / "reference" / "algorithm_onboarding" / "runs"
    runs.mkdir(parents=True)
    _write_run(runs, "R1", channel_hash="channel-a")
    _write_run(runs, "R2", channel_hash="channel-b", algorithm_id="optimizer")
    service = ComparisonService(tmp_path)
    preview = service.preview(["R1", "R2"], ComparisonIntent.ALGORITHM_COMPARISON)
    assert preview["status"] == "not_directly_comparable"
    assert "channel_hash" in preview["incompatible_dimensions"]
    assert preview["allowed_actions"] == ["side_by_side"]


def test_comparison_verifier_recomputes_positive_reference_without_preview(tmp_path):
    runs = tmp_path / "reference" / "algorithm_onboarding" / "runs"
    runs.mkdir(parents=True)
    _write_run(runs, "R1", algorithm_id="baseline")
    _write_run(runs, "R2", algorithm_id="optimizer")
    service = ComparisonService(tmp_path)
    preview = service.preview(["R1", "R2"], ComparisonIntent.ALGORITHM_COMPARISON)
    record = service.create(preview, confirmed=True)
    verified = ComparisonVerifier(tmp_path).verify(record["comparison_id"])
    assert verified["verified"] is True
    assert verified["verification"]["recomputed_eligibility"] == "comparable"
    assert "ComparisonService" not in __import__("inspect").getsource(ComparisonVerifier)
    assert ".preview(" not in __import__("inspect").getsource(ComparisonVerifier)


def test_comparison_verifier_rejects_stored_eligibility_tamper(tmp_path):
    runs = tmp_path / "reference" / "algorithm_onboarding" / "runs"
    runs.mkdir(parents=True)
    _write_run(runs, "R1")
    _write_run(runs, "R2", algorithm_id="optimizer")
    service = ComparisonService(tmp_path)
    record = service.create(service.preview(["R1", "R2"], ComparisonIntent.ALGORITHM_COMPARISON), confirmed=True)
    path = tmp_path / "reference" / "comparisons" / f"{record['comparison_id']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["compatibility"]["status"] = "not_directly_comparable"
    path.write_text(json.dumps(data), encoding="utf-8")
    verified = ComparisonVerifier(tmp_path).verify(record["comparison_id"])
    assert verified["verified"] is False
    assert verified["verification_status"] == "failed"


def test_comparison_verifier_reports_insufficient_context(tmp_path):
    runs = tmp_path / "reference" / "algorithm_onboarding" / "runs"
    runs.mkdir(parents=True)
    _write_run(runs, "R1")
    incomplete = json.loads((runs / "R1.json").read_text(encoding="utf-8"))
    incomplete.pop("dataset_hash")
    (runs / "R2.json").write_text(json.dumps(incomplete), encoding="utf-8")
    service = ComparisonService(tmp_path)
    preview = service.preview(["R1", "R2"], ComparisonIntent.ALGORITHM_COMPARISON)
    assert preview["status"] == "insufficient_context"
