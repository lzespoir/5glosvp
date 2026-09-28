"""
系统级优化 → EvidenceDescriptor。

平台内只能给出 platform_checks_passed / failed；independently_verified 只由独立 verifier 的导出写入。
当前所有仿真证据 acceptance_eligible = false。
"""

from __future__ import annotations

from algorithms import AlgorithmCategory
from evidence import (
    AcceptanceIneligibilityReason,
    EvidenceArtifactRef,
    EvidenceDescriptor,
    EvidenceType,
    VerificationStatus,
)
from optimization.models import OptimizationStatus

from .models import SystemOptimizationRecord

_BASE_REASONS = [
    AcceptanceIneligibilityReason.SIMULATION_ONLY,
    AcceptanceIneligibilityReason.NOT_MEASURED,
    AcceptanceIneligibilityReason.NOT_HUAWEI_DATA,
    AcceptanceIneligibilityReason.UNCONFIRMED_ACCEPTANCE_KPI,
]


def _category(record: SystemOptimizationRecord) -> AlgorithmCategory:
    if record.algorithm is not None:
        return record.algorithm.algorithm_category
    return AlgorithmCategory(record.provenance.get("optimizer_category", AlgorithmCategory.ENGINEERING_BASELINE))


def describe_system_optimization(record: SystemOptimizationRecord, api_prefix: str) -> EvidenceDescriptor:
    reasons = list(_BASE_REASONS)
    category = _category(record)
    if category is AlgorithmCategory.ENGINEERING_BASELINE:
        reasons.append(AcceptanceIneligibilityReason.ENGINEERING_BASELINE)
    elif category is AlgorithmCategory.RESEARCH_DEMO:
        reasons.append(AcceptanceIneligibilityReason.INTEGRATION_DEMO_ALGORITHM)
    if record.provenance.get("source_type", "simulation") != "simulation" \
            or record.provenance.get("evidence_level") == "Software Test Fixture":
        reasons.append(AcceptanceIneligibilityReason.TEST_FIXTURE)
    if record.status is not OptimizationStatus.SUCCEEDED:
        reasons.append(AcceptanceIneligibilityReason.NOT_SUCCEEDED)

    if not record.status.is_terminal:
        status, detail = VerificationStatus.NOT_VERIFIED, "optimization still running"
    elif record.status is OptimizationStatus.SUCCEEDED and record.fairness is not None and record.fairness.fair:
        status = VerificationStatus.PLATFORM_CHECKS_PASSED
        detail = "platform fairness checks passed; independent verification is recorded only in reference evidence"
    else:
        status, detail = VerificationStatus.PLATFORM_CHECKS_FAILED, "run failed or fairness checks not met"

    base = f"{api_prefix}/system-optimizations/{record.optimization_id}"
    return EvidenceDescriptor(
        evidence_id=f"EVD-{record.optimization_id}",
        evidence_type=EvidenceType.ALGORITHM_OPTIMIZATION if record.algorithm is not None
        else EvidenceType.SYSTEM_OPTIMIZATION,
        source_entity_type="system_optimization",
        source_entity_id=record.optimization_id,
        created_at=record.finished_at or record.created_at,
        provenance={
            k: record.provenance.get(k) for k in (
                "algorithm", "algorithm_version", "algorithm_category", "sdk_version", "learning_algorithm",
                "optimizer", "optimizer_version", "optimizer_category", "objective", "objective_version",
                "scenario", "backend", "backend_version", "benchmark_protocol", "evaluation_context",
                "git_commit", "measured", "huawei_data", "acceptance_evidence", "evidence_level",
            ) if k in record.provenance
        },
        verification_status=status,
        verification_detail=detail,
        acceptance_eligible=False,
        acceptance_reason=reasons,
        artifacts=[EvidenceArtifactRef(name=a.name, media_type=a.media_type, location=f"{base}/artifacts/{a.name}")
                   for a in record.artifacts],
    )
