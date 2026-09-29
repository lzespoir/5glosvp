from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ComparisonIntent(str, Enum):
    ALGORITHM_COMPARISON = "ALGORITHM_COMPARISON"
    HYPERPARAMETER_COMPARISON = "HYPERPARAMETER_COMPARISON"
    CONFIGURATION_COMPARISON = "CONFIGURATION_COMPARISON"
    RUN_REPRODUCIBILITY = "RUN_REPRODUCIBILITY"
    SCENARIO_ANALYSIS = "SCENARIO_ANALYSIS"
    CUSTOM_ANALYSIS = "CUSTOM_ANALYSIS"


class ComparisonService:
    REQUIRED = (
        "problem_type", "dataset_id", "dataset_version", "dataset_hash",
        "scenario_id", "scenario_version", "scenario_hash", "channel_artifact_id",
        "channel_hash", "traffic_realization_id", "traffic_hash", "objective_id",
        "objective_version", "constraints_hash", "kpi_versions", "protocol_id",
        "protocol_version", "evaluation_budget", "backend_id", "backend_version",
    )

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runs_dir = self.repo_root / "reference" / "algorithm_onboarding" / "runs"
        self.dir = self.repo_root / "reference" / "comparisons"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _run(self, run_id: str) -> dict[str, Any]:
        path = self.runs_dir / f"{run_id}.json"
        if not path.is_file():
            raise KeyError(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list_runs(self) -> list[dict[str, Any]]:
        out = []
        for path in sorted(self.runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                out.append({k: record.get(k) for k in ("run_id", "status", "algorithm_id", "algorithm_version", "scenario_id", "channel_hash", "evaluation_budget", "parameters", "created_at", "finished_at", "verification")})
            except (OSError, ValueError):
                continue
        return out

    @staticmethod
    def _snapshot(run: dict[str, Any]) -> dict[str, Any]:
        provenance = run.get("provenance") if isinstance(run.get("provenance"), dict) else {}

        def value(name: str) -> Any:
            if name in run:
                return run[name]
            return provenance.get(name)

        return {
            name: value(name) for name in ComparisonService.REQUIRED
        } | {
            "algorithm": {"id": value("algorithm_id"), "version": value("algorithm_version"), "package_hash": value("package_hash")},
            "algorithm_parameters": run.get("parameters", {}),
        }

    def preview(self, run_ids: list[str], intent: ComparisonIntent, declared_varying_dimensions: list[str] | None = None) -> dict[str, Any]:
        if len(run_ids) < 2:
            raise ValueError("COMPARISON_REQUIRES_AT_LEAST_TWO_RUNS")
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("COMPARISON_RUN_IDS_MUST_BE_UNIQUE")
        runs = [self._run(run_id) for run_id in run_ids]
        snapshots = [self._snapshot(run) for run in runs]
        declared = set(declared_varying_dimensions or [])
        allowed = {"algorithm", "algorithm_parameters"} if intent is ComparisonIntent.ALGORITHM_COMPARISON else set()
        if intent is ComparisonIntent.HYPERPARAMETER_COMPARISON:
            allowed = {"algorithm_parameters"}
        if intent is ComparisonIntent.SCENARIO_ANALYSIS:
            allowed = {"scenario_id", "channel_hash"}
        dimensions = []
        incompatible = []
        declared_differences = []
        missing = []
        for name in self.REQUIRED + ("algorithm", "algorithm_parameters"):
            values = [snapshot.get(name) for snapshot in snapshots]
            equal = all(value is not None for value in values) and all(value == values[0] for value in values[1:])
            varying = name in declared or name in allowed
            dimensions.append({"name": name, "values": values, "equal": equal, "frozen_by_default": name in self.REQUIRED, "declared_varying": varying})
            if any(value is None for value in values):
                missing.append(name)
                continue
            if not equal:
                if name in declared:
                    declared_differences.append(name)
                elif name in allowed:
                    # Algorithm identity and its explicitly supplied hyperparameters
                    # are the intended varying dimensions for their comparison intent.
                    pass
                else:
                    incompatible.append(name)
        status = "insufficient_context" if missing else ("not_directly_comparable" if incompatible else ("comparable_with_declared_differences" if declared_differences else "comparable"))
        return {
            "preview_id": f"CPREV-{uuid.uuid4().hex[:10].upper()}", "selected_run_ids": run_ids, "intent": intent.value,
            "status": status, "dimensions": dimensions, "differences": incompatible + declared_differences,
            "incompatible_dimensions": incompatible, "declared_differences": declared_differences,
            "missing_dimensions": missing,
            "allowed_actions": ["side_by_side"] if incompatible or missing else ["side_by_side", "aligned_metrics", "convergence_overlay"],
            "message_zh": "关键科研身份缺失，证据不足，不能确认直接可比" if missing else ("存在未声明差异，仅允许并列查看" if incompatible else "可以按预览条件创建对比对象"),
            "created_at": _now(),
        }

    def create(self, preview: dict[str, Any], confirmed: bool) -> dict[str, Any]:
        if not confirmed:
            raise ValueError("COMPARISON_CONFIRMATION_REQUIRED")
        comparison_id = f"COMP-DAY11-{uuid.uuid4().hex[:10].upper()}"
        record = {"comparison_id": comparison_id, "created_at": _now(), "confirmed_at": _now(), "status": "created", "verification_status": "pending", "verified": False, "user_intent": preview["intent"], "selected_run_ids": preview["selected_run_ids"], "compatibility": preview, "views": {"side_by_side": True, "aligned_metrics": preview["status"] == "comparable", "convergence_overlay": preview["status"] == "comparable"}, "result_policy": {"ranking": False, "winner": False, "gain": False, "a_over_b": False}}
        (self.dir / f"{comparison_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def get(self, comparison_id: str) -> dict[str, Any]:
        path = self.dir / f"{comparison_id}.json"
        if not path.is_file():
            raise KeyError(comparison_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def verify(self, comparison_id: str) -> dict[str, Any]:
        from .verifier import ComparisonVerifier

        return ComparisonVerifier(self.repo_root).verify(comparison_id)
