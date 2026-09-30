from __future__ import annotations

import hashlib
import json
from typing import Any

from antenna import AMatrixAdapter
from ue_twin import UETwinService
from ue_twin.models import Position

from .fast_backend import FastPropagationBackend
from .models import (
    CellRadioConfig, CellRadioObservation, InterferenceObservation, RadioIdentity,
    RadioMetricValue, RadioObservationSet, ScenarioRadioContext, ServingNeighborContext,
)


SCENARIO_ID = "SCN-DAY14-MULTISITE-001"
PROFILE_ID = "am_spread_aau5270e_c0_t-2_a0_multi"


class RadioObservabilityService:
    def __init__(self, ue_twin_service: UETwinService | None = None) -> None:
        self.ue_twin_service = ue_twin_service or UETwinService()
        self.backend = FastPropagationBackend()
        self._context = self._build_context()

    def _build_context(self) -> ScenarioRadioContext:
        manifest = next(item for item in self.ue_twin_service.adapter.manifest() if item.source_family == "8_BEAM_FAMILY")
        position = lambda x, y, z: Position(x=x, y=y, z=z, source="DAY14_SCENARIO_RADIO_CONTEXT")
        cells = [
            CellRadioConfig(cell_id="CELL-D14-A1", site_id="SITE-D14-A", aau_id="AAU-D14-A1", position=position(0, 0, 10), coordinate_system="SIONNA_SCENE_CARTESIAN", tx_power_dbm=46.0, carrier_frequency_hz=3.5e9, bandwidth_hz=100e6, antenna_profile_id=PROFILE_ID, a_matrix_library="spread", a_matrix_artifact_id=manifest.artifact_id, a_matrix_hash=manifest.source_hash, beam_config={"beam_type": "SSB", "beam_count": 8}, propagation_backend=self.backend.backend_id, radio_config_version="D14-RADIO-CONFIG-0.1", provenance={"source": "DAY14_EXPLICIT_FIXTURE", "calibration_status": "UNCALIBRATED_SIMULATION"}),
            CellRadioConfig(cell_id="CELL-D14-A2", site_id="SITE-D14-A", aau_id="AAU-D14-A2", position=position(120, 0, 10), coordinate_system="SIONNA_SCENE_CARTESIAN", tx_power_dbm=46.0, carrier_frequency_hz=3.5e9, bandwidth_hz=100e6, antenna_profile_id=PROFILE_ID, a_matrix_library="spread", a_matrix_artifact_id=manifest.artifact_id, a_matrix_hash=manifest.source_hash, beam_config={"beam_type": "SSB", "beam_count": 8}, propagation_backend=self.backend.backend_id, radio_config_version="D14-RADIO-CONFIG-0.1", provenance={"source": "DAY14_EXPLICIT_FIXTURE", "calibration_status": "UNCALIBRATED_SIMULATION"}),
            CellRadioConfig(cell_id="CELL-D14-B1", site_id="SITE-D14-B", aau_id="AAU-D14-B1", position=position(0, 120, 10), coordinate_system="SIONNA_SCENE_CARTESIAN", tx_power_dbm=46.0, carrier_frequency_hz=3.5e9, bandwidth_hz=100e6, antenna_profile_id=PROFILE_ID, a_matrix_library="spread", a_matrix_artifact_id=manifest.artifact_id, a_matrix_hash=manifest.source_hash, beam_config={"beam_type": "SSB", "beam_count": 8}, propagation_backend=self.backend.backend_id, radio_config_version="D14-RADIO-CONFIG-0.1", provenance={"source": "DAY14_EXPLICIT_FIXTURE", "calibration_status": "UNCALIBRATED_SIMULATION"}),
        ]
        ue_positions = {
            "UE-D14-001": position(20, 10, 1.5),
            "UE-D14-002": position(65, 20, 1.5),
            "UE-D14-003": position(12, 75, 1.5),
        }
        serving = {"UE-D14-001": "CELL-D14-A1", "UE-D14-002": "CELL-D14-A2", "UE-D14-003": "CELL-D14-B1"}
        neighbors = {ue: [cell.cell_id for cell in cells if cell.cell_id != serving[ue]] for ue in serving}
        definition = {"scenario_id": SCENARIO_ID, "version": "0.1", "scenario_family": "radio_observability", "source": "DAY14_EXPLICIT_FIXTURE", "scenario_definition_hash": "DAY14-DEFINITION-HASH-001"}
        instance = {"scenario_instance_id": "SCI-D14-MULTISITE-001", "scenario_id": SCENARIO_ID, "scenario_version": "0.1", "scenario_definition_hash": definition["scenario_definition_hash"], "seed": 14, "status": "VALID_EXECUTABLE", "identity": {"fixture": True, "seed_is_instance_only": True}}
        return ScenarioRadioContext(radio_context_id="RC-D14-MULTISITE-001", scenario_id=SCENARIO_ID, scenario_version="0.1", scenario_definition_hash=definition["scenario_definition_hash"], scenario_definition=definition, scenario_instance=instance, cells=cells, ue_positions=ue_positions, declared_serving_cells=serving, declared_neighbors=neighbors, provenance={"status": "OBSERVABILITY_FIXTURE_NOT_ACCEPTANCE_EVIDENCE", "sionna_executed": False, "measured_data": False})

    def scenarios(self) -> list[dict[str, Any]]:
        return [{"scenario_id": self._context.scenario_id, "name_zh": "Day14 多小区无线可观测性场景", "name_en": "Day14 Multi-site Radio Observability", "scenario_instance_id": self._context.scenario_instance["scenario_instance_id"], "cell_count": len(self._context.cells), "ue_count": len(self._context.ue_positions), "status": "OBSERVABILITY_READY_NOT_ACCEPTANCE_EVIDENCE"}]

    def context(self, scenario_id: str) -> ScenarioRadioContext:
        if scenario_id != self._context.scenario_id:
            raise KeyError(f"RADIO_SCENARIO_NOT_FOUND: {scenario_id}")
        return self._context

    def observe(self, scenario_id: str, ue_id: str) -> RadioObservationSet:
        context = self.context(scenario_id)
        if ue_id not in context.ue_positions:
            raise KeyError(f"RADIO_UE_NOT_FOUND: {ue_id}")
        ue_position = context.ue_positions[ue_id]
        serving_id = context.declared_serving_cells[ue_id]
        neighbor_ids = context.declared_neighbors[ue_id]
        observations: list[CellRadioObservation] = []
        serving_twin = None
        for cell in context.cells:
            twin = self.ue_twin_service.query(ue_id=ue_id, aau_id=cell.aau_id, aau_position=cell.position, ue_position=ue_position, profile_id=cell.antenna_profile_id, serving_cell_id=serving_id, neighbor_cell_ids=neighbor_ids)
            strongest = twin.beam_observations[0].normalized_response if twin.beam_observations else 0.0
            propagation, received = self.backend.observe(cell, twin.radio_geometry.distance_3d_m, strongest)
            role = "SERVING" if cell.cell_id == serving_id else ("NEIGHBOR" if cell.cell_id in neighbor_ids else "OTHER")
            if role == "SERVING":
                serving_twin = twin
            observations.append(CellRadioObservation(cell=cell, ue_id=ue_id, role=role, geometry=twin.radio_geometry, beam_observations=twin.beam_observations, strongest_relative_beam_id=twin.strongest_relative_beam_id, strongest_relative_response=RadioMetricValue(metric_name="RELATIVE_ANTENNA_RESPONSE", value=strongest, unit="linear_relative", semantic_type="RELATIVE_ANTENNA_RESPONSE", source_type="DAY13_A_MATRIX", calibration_status="RELATIVE_ONLY", artifact_id=cell.a_matrix_artifact_id, artifact_hash=cell.a_matrix_hash), propagation=propagation, received_power=received))
        signal = next(item.received_power.total.value for item in observations if item.role == "SERVING")
        neighbor_values = []
        ranked = []
        for item in observations:
            if item.role == "NEIGHBOR":
                value = float(item.received_power.total.value)
                neighbor_values.append(value)
                ranked.append({"cell_id": item.cell.cell_id, "sim_received_power_dbm": value})
        ranked.sort(key=lambda item: (-item["sim_received_power_dbm"], item["cell_id"]))
        for item in observations:
            if item.role == "SERVING":
                breakdown = self.backend.interference(float(signal), neighbor_values)
                item.interference = InterferenceObservation(**breakdown, notes=["Interference includes declared neighbor cells only", "UNCALIBRATED_SIMULATION"])
        identity_payload = {"scenario_id": context.scenario_id, "scenario_instance_id": context.scenario_instance["scenario_instance_id"], "scenario_definition_hash": context.scenario_definition_hash, "radio_context_id": context.radio_context_id, "radio_context_version": context.radio_context_version, "cell_config_hash": hashlib.sha256(json.dumps([cell.model_dump(mode="json") for cell in context.cells], sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "a_matrix_artifact_hashes": sorted({cell.a_matrix_hash for cell in context.cells}), "normalization_policy": "PEAK_LINEAR_POWER_TO_RELATIVE", "angular_grid_version": "D13-ANGULAR-GRID-0.1", "lookup_method": "nearest_grid", "propagation_backend": self.backend.model_version, "calibration_status": "UNCALIBRATED_SIMULATION"}
        identity = RadioIdentity(**identity_payload, identity_hash=hashlib.sha256(json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        observation_set_id = f"ROS-{context.scenario_id}-{ue_id}"
        assert serving_twin is not None
        twin_dump = serving_twin.model_copy(update={"radio_observations": {"observation_set_id": observation_set_id, "contract": "RadioObservationSet", "attachment_status": "REFERENCE_ATTACHED"}}).model_dump(mode="json")
        return RadioObservationSet(observation_set_id=observation_set_id, scenario_id=context.scenario_id, scenario_instance_id=context.scenario_instance["scenario_instance_id"], ue={"ue_id": ue_id, "position": ue_position.model_dump(mode="json"), "mobility_state": "STATIC_DAY14_OBSERVATION", "traffic_profile": "full_buffer"}, ue_twin=twin_dump, radio_context=context, cells=observations, serving_neighbor=ServingNeighborContext(serving_cell_id=serving_id, serving_selection_source="SCENARIO_DEFINED", neighbor_cell_ids=neighbor_ids, ranked_neighbors=ranked), identity=identity, provenance={"day13_ue_twin_reused": True, "a_matrix_raw_npy_modified": False, "sionna_executed": False, "measurement_data": False})
