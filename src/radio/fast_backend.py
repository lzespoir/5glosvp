from __future__ import annotations

import math

from .models import (
    CellRadioConfig,
    PropagationObservation,
    RadioMetricValue,
    ReceivedPowerDecomposition,
)


class FastPropagationBackend:
    """Small, explicit, uncalibrated propagation backend for observability.

    This is intentionally not an RSRP implementation. It provides a stable
    decomposition for comparing cells and exposing provenance before a full
    Sionna/measurement backend is available.
    """

    backend_id = "FAST_PROPAGATION"
    model_version = "D14-FAST-PROPAGATION-0.1"
    reference_distance_m = 1.0
    reference_loss_db = 32.4
    path_loss_exponent = 2.0
    noise_floor_dbm = -100.0

    def observe(
        self,
        cell: CellRadioConfig,
        distance_m: float,
        relative_response: float,
    ) -> tuple[PropagationObservation, ReceivedPowerDecomposition]:
        if distance_m <= 0:
            raise ValueError("RADIO_DISTANCE_INVALID: distance must be positive")
        if cell.tx_power_dbm is None:
            raise ValueError(f"CELL_RADIO_CONFIG_MISSING: tx_power_dbm for {cell.cell_id}")
        if cell.carrier_frequency_hz is None or cell.bandwidth_hz is None:
            raise ValueError(f"CELL_RADIO_CONFIG_MISSING: carrier/bandwidth for {cell.cell_id}")
        response = max(float(relative_response), 1e-12)
        path_loss = self.reference_loss_db + 10.0 * self.path_loss_exponent * math.log10(distance_m / self.reference_distance_m)
        antenna_db = 10.0 * math.log10(response)
        received_dbm = cell.tx_power_dbm + antenna_db - path_loss
        distance_metric = RadioMetricValue(
            metric_name="DISTANCE", value=distance_m, unit="m", semantic_type="GEOMETRY",
            source_type="SCENARIO_DEFINED", calibration_status="UNKNOWN",
            notes="3D Euclidean distance from the existing Day13 geometry contract.",
        )
        loss_metric = RadioMetricValue(
            metric_name="FAST_PATH_LOSS", value=path_loss, unit="dB", semantic_type="SIMULATION_DERIVED",
            source_type="FAST_PROPAGATION", calibration_status="UNCALIBRATED_SIMULATION",
            model_version=self.model_version,
            notes="Reference-loss plus explicit log-distance model; not calibrated path loss.",
        )
        power_metric = RadioMetricValue(
            metric_name="SIM_RECEIVED_POWER", value=received_dbm, unit="dBm", semantic_type="SIMULATION_DERIVED",
            source_type="FAST_PROPAGATION", calibration_status="UNCALIBRATED_SIMULATION",
            model_version=self.model_version,
            notes="Simulation-derived relative comparison value; not RSRP and not measured.",
        )
        tx_metric = RadioMetricValue(
            metric_name="TX_POWER", value=cell.tx_power_dbm, unit="dBm", semantic_type="SIMULATION_DERIVED",
            source_type="SCENARIO_DEFINED", calibration_status="UNKNOWN",
            notes="Explicit scenario radio configuration.",
        )
        antenna_metric = RadioMetricValue(
            metric_name="RELATIVE_ANTENNA_RESPONSE", value=response, unit="linear_relative",
            semantic_type="RELATIVE_ANTENNA_RESPONSE", source_type="DAY13_A_MATRIX",
            calibration_status="RELATIVE_ONLY", artifact_id=cell.a_matrix_artifact_id,
            artifact_hash=cell.a_matrix_hash,
            notes="Peak-normalized A-Matrix response; no absolute antenna gain asserted.",
        )
        propagation = PropagationObservation(
            backend_id=self.backend_id, model_version=self.model_version,
            distance_m=distance_metric, path_loss_db=loss_metric, received_power=power_metric,
            notes=["FAST_BACKEND_OBSERVATION", "SIONNA_BACKEND_NOT_EXECUTED"],
        )
        return propagation, ReceivedPowerDecomposition(
            components=[tx_metric, antenna_metric, loss_metric], total=power_metric,
        )

    def interference(self, signal_dbm: float, interferer_dbm: list[float]) -> dict[str, RadioMetricValue | list[RadioMetricValue]]:
        def mw(dbm: float) -> float:
            return 10.0 ** (dbm / 10.0)

        aggregate_mw = sum(mw(value) for value in interferer_dbm)
        noise_mw = mw(self.noise_floor_dbm)
        signal_mw = mw(signal_dbm)
        interference_dbm = 10.0 * math.log10(aggregate_mw) if aggregate_mw > 0 else None
        sinr_db = 10.0 * math.log10(signal_mw / (aggregate_mw + noise_mw))
        per = [RadioMetricValue(
            metric_name="INTERFERER_SIM_RECEIVED_POWER", value=value, unit="dBm",
            semantic_type="SIMULATION_DERIVED", source_type="DERIVED",
            calibration_status="UNCALIBRATED_SIMULATION", model_version=self.model_version,
            notes="Per-cell interferer contribution; not measured.",
        ) for value in interferer_dbm]
        aggregate = RadioMetricValue(
            metric_name="AGGREGATE_INTERFERENCE", value=interference_dbm, unit="dBm",
            semantic_type="SIMULATION_DERIVED", source_type="DERIVED",
            calibration_status="UNCALIBRATED_SIMULATION", model_version=self.model_version,
        )
        noise = RadioMetricValue(
            metric_name="NOISE_FLOOR", value=self.noise_floor_dbm, unit="dBm",
            semantic_type="SIMULATION_DERIVED", source_type="FAST_PROPAGATION",
            calibration_status="UNCALIBRATED_SIMULATION", model_version=self.model_version,
            notes="Explicit Fast backend assumption; not receiver-calibrated.",
        )
        sinr = RadioMetricValue(
            metric_name="SIM_SINR", value=sinr_db, unit="dB", semantic_type="DERIVED_KPI",
            source_type="DERIVED", calibration_status="UNCALIBRATED_SIMULATION",
            model_version=self.model_version,
            notes="Derived from simulated signal, aggregate interference and noise.",
        )
        return {"per_interferer": per, "aggregate_interference": aggregate, "noise_floor": noise, "sinr": sinr}
