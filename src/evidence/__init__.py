"""
证据契约 / Evidence contract (Acceptance Center Phase A).

EvidenceDescriptor 让未来的验收中心可以查询算法 / 优化证据；Day 7 不做验收判定。
verified（证据可复核）与 acceptance_eligible（可作为验收证据）是两个长期分离的概念：
verifier PASS 不会让仿真证据变成验收证据。
"""

from .models import (
    AcceptanceIneligibilityReason,
    EvidenceArtifactRef,
    EvidenceDescriptor,
    EvidenceType,
    VerificationStatus,
)

__all__ = [
    "AcceptanceIneligibilityReason",
    "EvidenceArtifactRef",
    "EvidenceDescriptor",
    "EvidenceType",
    "VerificationStatus",
]
