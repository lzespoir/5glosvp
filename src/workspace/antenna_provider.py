"""Extensible antenna pattern provider contracts for configured definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from antenna import AMatrixAdapter


class AntennaPatternProvider(ABC):
    provider_type: str
    status: str

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        raise NotImplementedError

    def pattern(self, profile_id: str, beam_id: int) -> dict[str, Any]:
        raise NotImplementedError(f"{self.provider_type} pattern provider is not implemented")


class AMatrixPatternProvider(AntennaPatternProvider):
    provider_type = "A_MATRIX"
    status = "IMPLEMENTED"

    def __init__(self, adapter: AMatrixAdapter | None = None):
        self.adapter = adapter or AMatrixAdapter()

    def metadata(self) -> dict[str, Any]:
        return {"provider_type": self.provider_type, "status": self.status, "normalization": "PEAK_LINEAR_POWER_TO_RELATIVE", "calibration": "RELATIVE_ONLY", "source": "SIONNATEST_IMPLEMENTATION"}

    def pattern(self, profile_id: str, beam_id: int) -> dict[str, Any]:
        profile = next((item for item in self.adapter.profiles() if item.get("id") == profile_id), None)
        if not profile:
            raise KeyError(profile_id)
        entry_key = profile.get("keys_by_beam", {}).get(str(beam_id))
        if not entry_key:
            raise KeyError(f"beam {beam_id} not in profile {profile_id}")
        return self.adapter.pattern(profile["library"], profile["beam_type"], entry_key).model_dump(mode="json")


class ContractOnlyAntennaProvider(AntennaPatternProvider):
    status = "CONTRACT_ONLY"

    def __init__(self, provider_type: str):
        self.provider_type = provider_type

    def metadata(self) -> dict[str, Any]:
        return {"provider_type": self.provider_type, "status": self.status, "normalization": "UNKNOWN", "calibration": "UNKNOWN", "source": "PROVIDER_CONTRACT"}


class AntennaProviderRegistry:
    def __init__(self, matrix_provider: AMatrixPatternProvider | None = None):
        providers: list[AntennaPatternProvider] = [matrix_provider or AMatrixPatternProvider()]
        providers.extend(ContractOnlyAntennaProvider(kind) for kind in ("SIONNA_BUILTIN", "GAUSSIAN", "CUSTOM", "EXTERNAL"))
        self._providers = {provider.provider_type: provider for provider in providers}

    def list(self) -> list[dict[str, Any]]:
        return [provider.metadata() for provider in self._providers.values()]

    def get(self, provider_type: str) -> AntennaPatternProvider:
        return self._providers[provider_type]
