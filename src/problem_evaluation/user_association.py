from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from algorithm_benchmark.association_optimization import AssociationOptimizationService
from frozen_artifacts import FrozenArtifactService
from user_association.backend import MultiCellBackend
from user_association.service import UserAssociationService


class UserAssociationEvaluationAdapter:
    problem_type = "user_association"

    def execute(self, *, repo_root: Path, record: dict[str, Any], package: dict[str, Any], algorithm: type) -> dict[str, Any]:
        scenario = UserAssociationService(repo_root / "configs").load(record["scenario_id"])
        backend = MultiCellBackend(scenario)
        channel = FrozenArtifactService(repo_root / "reference").load_day8_channel(scenario, backend)
        params = dict(record["parameters"])
        seed = int(params.get("seed", scenario.seed))
        scenario_json = scenario.model_dump(mode="json")
        scenario_hash = hashlib.sha256(json.dumps(scenario_json, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        traffic = {"model": scenario.traffic_model, "num_slots": scenario.num_slots, "slot_duration_s": scenario.slot_duration_s}
        traffic_hash = hashlib.sha256(json.dumps(traffic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {
            "execution": AssociationOptimizationService().run(
                algorithm(), scenario, backend, record["evaluation_budget"], seed, record["run_id"],
                algorithm_hyperparameters=params,
            ),
            "channel": channel,
            "identity": {
                "problem_type": "user_association",
                "dataset_id": "SIMULATION_MULTICELL_SCENARIO_SET",
                "dataset_version": "0.1",
                "dataset_hash": scenario_hash,
                "scenario_id": scenario.scenario_id,
                "scenario_version": str(scenario.metadata.get("scenario_version", "0.1")),
                "scenario_hash": scenario_hash,
                "channel_artifact_id": "CH-MULTICELL-" + channel.channel_hash[:8].upper(),
                "channel_hash": channel.channel_hash,
                "traffic_realization_id": "TRAFFIC-" + scenario.traffic_model.upper(),
                "traffic_hash": traffic_hash,
                "objective_id": "NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1",
                "objective_version": "0.1",
                "constraints_hash": hashlib.sha256(b"P5_UE_THROUGHPUT_GE_BASELINE_P5_V0_1").hexdigest(),
                "kpi_versions": {"network_throughput": "0.1", "average_ue_throughput": "0.1", "p5_ue_throughput": "0.1"},
                "protocol_id": "USER_ASSOCIATION_EVALUATION_PROTOCOL_V0_1",
                "protocol_version": "0.1",
                "evaluation_budget": record["evaluation_budget"],
                "backend_id": "sionna_multicell",
                "backend_version": "frozen-artifact-v0.1",
            },
        }
