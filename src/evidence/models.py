"""证据描述符模型 / Evidence descriptor models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class EvidenceType(str, Enum):
    SYSTEM_OPTIMIZATION = "system_optimization"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    # Historical values are retained for Day 4-10 evidence compatibility.
    NOT_VERIFIED = "not_verified"
    PLATFORM_CHECKS_PASSED = "platform_checks_passed"
    PLATFORM_CHECKS_FAILED = "platform_checks_failed"
    INDEPENDENTLY_VERIFIED = "independently_verified"
    INDEPENDENT_VERIFICATION_FAILED = "independent_verification_failed"


class AcceptanceIneligibilityReason(str, Enum):
    SIMULATION_ONLY = "simulation_only"
    NOT_MEASURED = "not_measured"
    NOT_HUAWEI_DATA = "not_huawei_data"
    UNCONFIRMED_ACCEPTANCE_KPI = "unconfirmed_acceptance_kpi"
    ENGINEERING_BASELINE = "engineering_baseline"
    INTEGRATION_DEMO_ALGORITHM = "integration_demo_algorithm"
    TEST_FIXTURE = "test_fixture"
    NOT_SUCCEEDED = "not_succeeded"


class EvidenceArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    media_type: str
    location: str


class EvidenceDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    evidence_type: EvidenceType
    source_entity_type: str
    source_entity_id: str
    created_at: str
    provenance: dict[str, Any]
    verification_status: VerificationStatus
    verification_detail: str = ""
    verifier_id: str | None = None
    verified_at: str | None = None
    verification_hash: str | None = None
    legacy_verification_semantics: bool = False
    acceptance_eligible: bool
    acceptance_reason: list[AcceptanceIneligibilityReason] = Field(default_factory=list)
    artifacts: list[EvidenceArtifactRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> EvidenceDescriptor:
        if not self.acceptance_eligible and not self.acceptance_reason:
            raise ValueError("an ineligible evidence descriptor must state why")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verified(self) -> bool:
        return self.verification_status in {VerificationStatus.VERIFIED, VerificationStatus.INDEPENDENTLY_VERIFIED}
