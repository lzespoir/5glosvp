from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit

from comparison.service import ComparisonIntent, ComparisonService
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
        "channel_hash": channel_hash, "evaluation_budget": budget,
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
