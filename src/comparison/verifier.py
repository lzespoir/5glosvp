from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class ComparisonVerifier:
    """Independent persisted-record verifier; intentionally does not import production service code."""

    VERSION = "comparison-independent-verifier-v0.2"
    REQUIRED = ("problem_type", "dataset_id", "dataset_version", "dataset_hash", "scenario_id", "scenario_version", "scenario_hash", "channel_artifact_id", "channel_hash", "traffic_realization_id", "traffic_hash", "objective_id", "objective_version", "constraints_hash", "kpi_versions", "protocol_id", "protocol_version", "evaluation_budget", "backend_id", "backend_version")

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runs_dir = self.repo_root / "reference" / "algorithm_onboarding" / "runs"
        self.dir = self.repo_root / "reference" / "comparisons"

    def _load(self, comparison_id: str) -> dict[str, Any]:
        path = self.dir / f"{comparison_id}.json"
        if not path.is_file():
            raise KeyError(comparison_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _run(self, run_id: str) -> dict[str, Any]:
        path = self.runs_dir / f"{run_id}.json"
        if not path.is_file():
            raise KeyError(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def _snapshot(cls, run: dict[str, Any]) -> dict[str, Any]:
        provenance = run.get("provenance") if isinstance(run.get("provenance"), dict) else {}

        def value(name: str) -> Any:
            return run[name] if name in run else provenance.get(name)

        return {name: value(name) for name in cls.REQUIRED} | {
            "algorithm": {"id": value("algorithm_id"), "version": value("algorithm_version"), "package_hash": value("package_hash")},
            "algorithm_parameters": run.get("parameters") if "parameters" in run else None,
        }

    @classmethod
    def _recompute(cls, run_ids: list[str], intent: str, runs: list[dict[str, Any]]) -> dict[str, Any]:
        snapshots = [cls._snapshot(run) for run in runs]
        allowed = {"algorithm", "algorithm_parameters"} if intent == "ALGORITHM_COMPARISON" else set()
        if intent == "HYPERPARAMETER_COMPARISON":
            allowed = {"algorithm_parameters"}
        if intent == "SCENARIO_ANALYSIS":
            allowed = {"scenario_id", "scenario_version", "scenario_hash", "channel_artifact_id", "channel_hash"}
        dimensions = []
        missing: list[str] = []
        mismatches: list[str] = []
        declared = set()
        for name in cls.REQUIRED + ("algorithm", "algorithm_parameters"):
            values = [snapshot.get(name) for snapshot in snapshots]
            equal = all(v is not None for v in values) and all(v == values[0] for v in values[1:])
            dimensions.append({"name": name, "values": values, "equal": equal, "frozen_by_default": name in cls.REQUIRED, "declared_varying": name in allowed})
            if any(v is None for v in values):
                missing.append(name)
            elif not equal and name not in allowed:
                mismatches.append(name)
            elif not equal and name in allowed:
                # The comparison intent itself declares this dimension as the
                # expected varying dimension.  It is not an additional
                # undeclared difference in the persisted preview contract.
                pass
        status = "insufficient_context" if missing else ("not_directly_comparable" if mismatches else ("comparable_with_declared_differences" if declared else "comparable"))
        return {"selected_run_ids": run_ids, "intent": intent, "status": status, "dimensions": dimensions, "missing_dimensions": missing, "incompatible_dimensions": mismatches, "declared_differences": sorted(declared)}

    def verify(self, comparison_id: str) -> dict[str, Any]:
        record = self._load(comparison_id)
        run_ids = record.get("selected_run_ids")
        checks: list[dict[str, Any]] = []
        mismatches: list[str] = []
        try:
            runs = [self._run(run_id) for run_id in run_ids]
            checks.append({"check": "selected_run_ids_exist", "status": "PASS"})
        except (KeyError, TypeError) as exc:
            runs = []
            mismatches.append(f"selected_run_ids:{exc}")
            checks.append({"check": "selected_run_ids_exist", "status": "FAIL", "detail": str(exc)})
        recomputed = self._recompute(run_ids, str(record.get("user_intent")), runs) if runs else {"status": "insufficient_context", "selected_run_ids": run_ids, "intent": record.get("user_intent")}
        stored = record.get("compatibility") or {}
        checks.append({"check": "stored_selection_matches", "status": "PASS" if stored.get("selected_run_ids") == run_ids else "FAIL"})
        checks.append({"check": "stored_intent_matches", "status": "PASS" if stored.get("intent") == record.get("user_intent") else "FAIL"})
        checks.append({"check": "stored_eligibility_matches_recomputed", "status": "PASS" if stored.get("status") == recomputed.get("status") else "FAIL", "stored": stored.get("status"), "recomputed": recomputed.get("status")})
        checks.append({"check": "result_policy_has_no_ranking", "status": "PASS" if record.get("result_policy") == {"ranking": False, "winner": False, "gain": False, "a_over_b": False} else "FAIL"})
        if stored.get("status") != recomputed.get("status"):
            mismatches.append("eligibility")
        passed = bool(runs) and not mismatches and all(item["status"] == "PASS" for item in checks) and recomputed.get("status") != "insufficient_context"
        record.update({"verification_status": "verified" if passed else "failed", "verified": passed, "verifier_id": self.VERSION, "verifier_version": self.VERSION, "verified_at": _now(), "verification_hash": _hash({"recomputed": recomputed, "stored": stored}), "verification": {"status": "PASS" if passed else "FAIL", "comparison_id": comparison_id, "recomputed_eligibility": recomputed.get("status"), "stored_eligibility": stored.get("status"), "checks": checks, "mismatches": mismatches, "verified_at": _now(), "verifier_version": self.VERSION}})
        (self.dir / f"{comparison_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return record
