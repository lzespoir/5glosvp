"""独立复核脚本 scripts/verify_system_optimization.py：正常通过，篡改可被发现。"""

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from system_helpers import TEST_PROTOCOL_ID, make_optimization_service

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ONLY_FAILURES = {"not_test_fixture"}


@pytest.fixture
def optimization(tmp_path):
    service = make_optimization_service(tmp_path)
    record = service.create("verify", "SYSTEM-TEST-001", "grid_search", "NETWORK_THROUGHPUT_MAX_V0_1",
                            "scheduler_beta", [0.1, 0.5, 0.9, 0.99], TEST_PROTOCOL_ID)
    return tmp_path, record.optimization_id


def verify(tmp: Path, opt_id: str) -> dict:
    out = tmp / "verification.json"
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_system_optimization.py"), opt_id,
         "--data-dir", str(tmp / "system_optimizations"), "--experiments-dir", str(tmp / "system_experiments"),
         "--out", str(out)],
        capture_output=True, text=True, check=False,
    )
    return json.loads(out.read_text(encoding="utf-8"))


def failed(report: dict) -> set[str]:
    return {c["check"] for c in report["checks"] if c["status"] == "FAIL"}


def edit_record(tmp: Path, opt_id: str, mutate) -> None:
    path = tmp / "system_optimizations" / opt_id / "optimization.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_clean_run_passes_every_check_except_fixture_provenance(optimization):
    report = verify(*optimization)
    assert failed(report) == FIXTURE_ONLY_FAILURES
    assert report["independent"]["best_candidate_id"] == "CAND-004"
    assert len(report["checks"]) > 50


def test_tampered_kpi_is_detected(optimization):
    tmp, opt_id = optimization

    def mutate(d):
        d["candidates"][0]["network_throughput_mbps"]["mean"] *= 1.01
    edit_record(tmp, opt_id, mutate)
    assert "CAND-001.NETWORK_THROUGHPUT_V0_1" in failed(verify(tmp, opt_id))


def test_tampered_best_selection_is_detected(optimization):
    tmp, opt_id = optimization
    edit_record(tmp, opt_id, lambda d: d.update(best_candidate_id="CAND-001"))
    assert "best_candidate_selection" in failed(verify(tmp, opt_id))


def test_hidden_negative_tradeoff_is_detected(optimization):
    tmp, opt_id = optimization
    edit_record(tmp, opt_id, lambda d: d["comparison"].update(negative_kpi_changes=[]))
    assert "negative_kpi_changes_preserved" in failed(verify(tmp, opt_id))


def test_tampered_channel_is_detected(optimization):
    tmp, opt_id = optimization
    path = tmp / "system_optimizations" / opt_id / "context" / "channel.npz"
    with np.load(path) as data:
        arrays = {k: data[k].copy() for k in data.files}
    key = next(k for k in arrays if k.startswith("array__"))
    arrays[key].flat[0] += 1
    np.savez_compressed(path, **arrays)
    assert "channel_artifact_hash" in failed(verify(tmp, opt_id))


def test_verifier_does_not_import_production_evaluators():
    source = (REPO_ROOT / "scripts" / "verify_system_optimization.py").read_text(encoding="utf-8")
    pattern = re.compile(
        r"^\s*(from|import)\s+(evaluation|system_optimization|optimization|system_simulation|simulation|api)\b",
        re.MULTILINE,
    )
    assert not pattern.search(source)
