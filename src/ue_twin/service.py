from __future__ import annotations

import hashlib
import json
from typing import Any

from antenna import AMatrixAdapter, compute_radio_geometry
from antenna.amatrix_adapter import normalize_response
from antenna.models import BeamResponse

from .models import Position, UETwin


class UETwinService:
    def __init__(self, adapter: AMatrixAdapter | None = None) -> None:
        self.adapter = adapter or AMatrixAdapter()

    def _profile(self, profile_id: str | None) -> dict[str, Any]:
        profiles = self.adapter.profiles()
        if not profiles:
            raise ValueError("A_MATRIX_PROFILE_NOT_FOUND: profiles.json is empty")
        if profile_id:
            for profile in profiles:
                if profile.get("id") == profile_id:
                    return profile
            raise ValueError(f"A_MATRIX_PROFILE_NOT_FOUND: {profile_id}")
        return profiles[0]

    @staticmethod
    def _profile_beams(profile: dict[str, Any]) -> list[tuple[int, str]]:
        keys = profile.get("keys_by_beam") or {}
        beam_ids = profile.get("beam_ids") or [profile.get("beam_id", 0)]
        result = []
        for beam_id in beam_ids:
            key = keys.get(str(beam_id))
            if key:
                result.append((int(beam_id), str(key)))
        if not result and profile.get("entry_key"):
            result.append((int(profile.get("beam_id", 0)), str(profile["entry_key"])))
        return result

    def query(
        self,
        *,
        ue_id: str,
        aau_id: str,
        aau_position: Position,
        ue_position: Position,
        profile_id: str | None = None,
        serving_cell_id: str | None = None,
        neighbor_cell_ids: list[str] | None = None,
        traffic_profile: str = "full_buffer",
    ) -> UETwin:
        if aau_position.coordinate_system != ue_position.coordinate_system:
            raise ValueError("COORDINATE_SYSTEM_MISMATCH: AAU and UE must use the same coordinate system")
        geometry = compute_radio_geometry(aau_position.model_dump(), ue_position.model_dump(), aau_position.coordinate_system)
        profile = self._profile(profile_id)
        library = str(profile.get("library", "spread"))
        beam_type = str(profile.get("beam_type", "SSB"))
        responses: list[BeamResponse] = []
        for beam_id, entry_key in self._profile_beams(profile):
            entry, raw = self.adapter.entry(library, beam_type, entry_key)
            normalized, _field, _quality = normalize_response(raw)
            az = geometry.azimuth_deg % 360.0
            el = geometry.elevation_deg
            row = int(round((el + 90.0) / 2.0))
            row = max(0, min(90, row))
            col = int(az // 5.0) % 72
            responses.append(
                BeamResponse(
                    beam_id=beam_id,
                    entry_key=entry_key,
                    azimuth_deg=az,
                    elevation_deg=el,
                    grid_row=row,
                    grid_col=col,
                    normalized_response=float(normalized[row, col]),
                    rank=0,
                )
            )
        ordered = sorted(responses, key=lambda item: (-item.normalized_response, item.beam_id))
        ranked = [item.model_copy(update={"rank": index + 1}) for index, item in enumerate(ordered)]
        manifests = self.adapter.manifest()
        return UETwin(
            ue_id=ue_id,
            position=ue_position,
            mobility_state="STATIC_DAY13_GEOMETRY",
            serving_cell_id=serving_cell_id,
            neighbor_cell_ids=list(neighbor_cell_ids or []),
            traffic_profile=traffic_profile,
            aau_id=aau_id,
            aau_position=aau_position,
            radio_geometry=geometry,
            beam_observations=ranked,
            strongest_relative_beam_id=ranked[0].beam_id if ranked else None,
            provenance={
                "profile_id": profile.get("id"),
                "library": library,
                "beam_type": beam_type,
                "normalization_policy": "PEAK_LINEAR_POWER_TO_RELATIVE",
                "angular_grid_version": "D13-ANGULAR-GRID-0.1",
                "lookup_method": "nearest_grid",
                "a_matrix_artifact_ids": [manifest.artifact_id for manifest in manifests if manifest.source_family == ("8_BEAM_FAMILY" if library == "spread" else "7_BEAM_FAMILY")],
                "relative_only": True,
            },
        )

    def scenario_identity(self, scenario: dict[str, Any], profile_id: str | None = None) -> dict[str, Any]:
        profile = self._profile(profile_id)
        library = str(profile.get("library", "spread"))
        manifest = next(item for item in self.adapter.manifest() if item.source_family == ("8_BEAM_FAMILY" if library == "spread" else "7_BEAM_FAMILY"))
        payload = {
            "scenario_id": scenario.get("scenario_id"),
            "scenario_version": scenario.get("version"),
            "scenario_definition_hash": scenario.get("scenario_definition_hash"),
            "a_matrix_artifact_id": manifest.artifact_id,
            "a_matrix_hash": manifest.source_hash,
            "antenna_profile_id": profile.get("id"),
            "normalization_policy": "PEAK_LINEAR_POWER_TO_RELATIVE",
            "angular_grid_version": "D13-ANGULAR-GRID-0.1",
            "lookup_method": "nearest_grid",
        }
        identity_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {**payload, "identity_hash": identity_hash, "absolute_radio_kpi_status": "ABSOLUTE_RADIO_KPI_NOT_CALIBRATED"}
