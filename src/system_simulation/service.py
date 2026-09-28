"""
系统级实验服务 / System experiment service.

    Scenario → SystemSimulationBackend（按 capability 选择）→ Canonical Result
    → KPI Engine → Artifacts → Store

同步执行：一次只运行一个系统级实验（进程内锁），请求线程等待完成。
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.kpi import KpiContext, KpiRegistry, KpiResult, UeThroughputInput, UE_THROUGHPUT_V0_1
from simulation.models import new_experiment_id

from .artifacts import RUN_LOG, export_artifacts
from .base import (
    Capability,
    ChannelRealization,
    ModelType,
    SystemBackendDescriptor,
    SystemBackendRegistry,
    SystemSimulationBackend,
)
from .errors import (
    InvalidSystemScenarioError,
    SystemArtifactNotFoundError,
    SystemBackendUnavailableError,
    SystemCapabilityNotSupportedError,
    SystemExperimentNotFoundError,
)
from .models import (
    ArtifactRef,
    CellTopology,
    EvaluationContextLink,
    SystemErrorCode,
    SystemExperimentError,
    SystemExperimentPurpose,
    SystemExperimentRecord,
    SystemExperimentStatus,
    SystemScenario,
)
from .scenarios import SystemScenarioCatalog
from .store import FileSystemExperimentStore

logger = logging.getLogger(__name__)

MODEL_LABELS = {
    ModelType.SIONNA_SYS: "Sionna Simulation Generated",
    ModelType.ENGINEERING_APPROXIMATION: "Fast Engineering Approximation",
    ModelType.TEST_FIXTURE: "TEST FIXTURE",
}


@dataclass(frozen=True)
class SystemBackendStatus:
    descriptor: SystemBackendDescriptor
    health: dict[str, Any]


class KpiCalculationError(Exception):
    pass


class NoUeResultsError(Exception):
    pass


class SystemExperimentService:
    def __init__(
        self,
        store: FileSystemExperimentStore,
        registry: SystemBackendRegistry,
        catalog: SystemScenarioCatalog,
        kpis: KpiRegistry,
        platform_version: str,
        git_commit: str | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._catalog = catalog
        self._kpis = kpis
        self._platform_version = platform_version
        self._git_commit = git_commit
        self._run_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_backends(self, capability: Capability | None = None) -> list[SystemBackendStatus]:
        descriptors = self._registry.with_capability(capability) if capability else self._registry.list()
        return [SystemBackendStatus(d, d.factory().health_check()) for d in descriptors]

    def backend_descriptor(self, backend_id: str) -> SystemBackendDescriptor:
        return self._registry.get(backend_id)

    def list_scenarios(self) -> list[SystemScenario]:
        return self._catalog.list()

    def get_scenario(self, scenario_id: str) -> SystemScenario:
        return self._catalog.get(scenario_id)

    def kpi_registry(self) -> KpiRegistry:
        return self._kpis

    def get(self, experiment_id: str) -> SystemExperimentRecord:
        record = self._store.get(experiment_id)
        if record is None:
            raise SystemExperimentNotFoundError(f"System experiment not found: {experiment_id}")
        return record

    def list(self, limit: int = 50, offset: int = 0) -> tuple[list[SystemExperimentRecord], int]:
        return self._store.list(limit=limit, offset=offset), self._store.count()

    def resolve_artifact(self, experiment_id: str, name: str) -> tuple[ArtifactRef, Path]:
        record = self.get(experiment_id)
        artifact = next((a for a in record.artifacts if a.name == name), None)
        if artifact is None:
            raise SystemArtifactNotFoundError(f"Artifact not found: {name!r}")
        return artifact, self._store.resolve_artifact(experiment_id, name)

    # ------------------------------------------------------------------
    # Create & run
    # ------------------------------------------------------------------

    def require_backend(
        self, backend_id: str, *capabilities: Capability
    ) -> tuple[SystemBackendDescriptor, SystemSimulationBackend, dict[str, Any]]:
        """按 capability 校验并实例化后端；不可用时抛出平台异常。"""
        descriptor = self._registry.get(backend_id)
        for capability in (Capability.SYSTEM_SIMULATION, *capabilities):
            if not descriptor.supports(capability):
                raise SystemCapabilityNotSupportedError(
                    f"Backend '{descriptor.id}' does not declare capability '{capability.value}'"
                )
        backend = descriptor.factory()
        health = backend.health_check()
        if not health.get("available"):
            raise SystemBackendUnavailableError("; ".join(health.get("errors") or []) or "unavailable")
        return descriptor, backend, health

    def realize_channel(self, scenario: SystemScenario, backend_id: str) -> ChannelRealization:
        """生成一次冻结信道实现（需要 CHANNEL_REUSE 能力）。"""
        _, backend, _ = self.require_backend(backend_id, Capability.CHANNEL_REUSE)
        with self._run_lock:
            return backend.realize_channel(scenario, logger)

    def create(self, name: str, scenario_id: str, backend_id: str | None = None) -> SystemExperimentRecord:
        scenario = self._catalog.get(scenario_id)
        descriptor, backend, health = self.require_backend(backend_id or scenario.backend)
        return self._create_and_run(name, scenario, descriptor, backend, health)

    def run_in_context(
        self,
        name: str,
        scenario: SystemScenario,
        backend_id: str,
        channel: ChannelRealization,
        *,
        purpose: SystemExperimentPurpose,
        optimization_id: str,
        candidate_id: str,
        context: EvaluationContextLink,
    ) -> SystemExperimentRecord:
        """在冻结评价上下文中运行派生场景（系统优化的基线 / 候选）。"""
        descriptor, backend, health = self.require_backend(backend_id, Capability.CHANNEL_REUSE)
        return self._create_and_run(
            name, scenario, descriptor, backend, health, channel=channel, purpose=purpose,
            optimization_id=optimization_id, candidate_id=candidate_id, context=context,
        )

    def _create_and_run(
        self,
        name: str,
        scenario: SystemScenario,
        descriptor: SystemBackendDescriptor,
        backend: SystemSimulationBackend,
        health: dict[str, Any],
        *,
        channel: ChannelRealization | None = None,
        purpose: SystemExperimentPurpose = SystemExperimentPurpose.STANDALONE,
        optimization_id: str | None = None,
        candidate_id: str | None = None,
        context: EvaluationContextLink | None = None,
    ) -> SystemExperimentRecord:
        experiment_id = new_experiment_id()
        while self._store.exists(experiment_id):
            experiment_id = new_experiment_id()
        record = SystemExperimentRecord(
            experiment_id=experiment_id,
            name=name,
            scenario_id=scenario.scenario_id,
            scenario_name_zh=scenario.name_zh,
            scenario_name_en=scenario.name_en,
            backend=descriptor.id,
            backend_version=health.get("version"),
            seed=scenario.seed,
            purpose=purpose,
            optimization_id=optimization_id,
            optimization_candidate_id=candidate_id,
            evaluation_context=context,
            provenance=self._provenance(descriptor, scenario),
        )
        record.transition(SystemExperimentStatus.CREATED)
        self._store.create(record)

        with self._run_lock:
            record.transition(SystemExperimentStatus.RUNNING)
            self._store.update(record)
            logger.info("%s RUNNING system scenario=%s backend=%s purpose=%s", experiment_id,
                        scenario.scenario_id, descriptor.id, purpose.value)
            self._execute(record, scenario, descriptor, backend, channel)
        return record

    def _provenance(self, descriptor: SystemBackendDescriptor, scenario: SystemScenario) -> dict[str, Any]:
        return {
            "backend": descriptor.id,
            "provider": descriptor.provider,
            "model_type": descriptor.model_type.value,
            "model_label": MODEL_LABELS[descriptor.model_type],
            "source_type": descriptor.source_type,
            "measured": False,
            "huawei_data": False,
            "acceptance_evidence": False,
            "traffic_model": scenario.traffic.model_dump(mode="json"),
            "assumptions": list(scenario.assumptions),
        }

    def _execute(
        self,
        record: SystemExperimentRecord,
        scenario: SystemScenario,
        descriptor: SystemBackendDescriptor,
        backend: SystemSimulationBackend,
        channel: ChannelRealization | None,
    ) -> None:
        artifact_dir = self._store.artifact_dir(record.experiment_id)
        run_log = logging.getLogger(f"system_simulation.run.{record.experiment_id}")
        run_log.setLevel(logging.INFO)
        handler = logging.FileHandler(artifact_dir / RUN_LOG.name, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        run_log.addHandler(handler)
        t0 = time.perf_counter()
        stage = SystemErrorCode.SYSTEM_SIMULATION_FAILED
        try:
            run_log.info("experiment=%s scenario=%s backend=%s seed=%s", record.experiment_id,
                         scenario.scenario_id, descriptor.id, scenario.seed)
            if record.evaluation_context is not None:
                link = record.evaluation_context
                run_log.info("evaluation context %s channel=%s sha256=%s", link.evaluation_context_id,
                             link.channel_realization_id, link.channel_sha256)
            output = backend.run(scenario, record.experiment_id, run_log, channel=channel)
            result = output.result
            if not result.ue_results:
                stage = SystemErrorCode.NO_UE_RESULTS
                raise NoUeResultsError("Backend returned no UE results")

            stage = SystemErrorCode.KPI_CALCULATION_FAILED
            kpis = self._evaluate_kpis(record, result, descriptor)
            ue_kpi = next(k for k in kpis if k.metric_id == UE_THROUGHPUT_V0_1)
            for ue in result.ue_results:
                ue.throughput_mbps = (ue_kpi.per_ue or {}).get(ue.ue_id)
                ue.throughput_metric_id = UE_THROUGHPUT_V0_1
            result.cells = [
                CellTopology(cell_id=c.cell_id, bs_id=c.bs_id, position=list(scenario.cell_position(c)),
                             carrier_frequency_hz=c.carrier_frequency_hz, bandwidth_hz=c.bandwidth_hz,
                             tx_power_dbm=c.tx_power_dbm)
                for c in scenario.cells
            ]
            result.runtime.total_seconds = time.perf_counter() - t0
            record.result = result
            record.kpis = kpis
            record.backend_version = result.backend_version
            record.warnings = list(result.warnings)

            stage = SystemErrorCode.ARTIFACT_EXPORT_FAILED
            run_log.info("KPIs: %s", {k.metric_id: k.value for k in kpis if k.scope.value == "network"})
            record.artifacts = export_artifacts(
                artifact_dir, scenario, result, kpis, output.slot_trace,
                self._metadata(record, scenario, descriptor), MODEL_LABELS[descriptor.model_type],
            )
            record.transition(SystemExperimentStatus.SUCCEEDED)
        except InvalidSystemScenarioError as exc:
            self._fail(record, SystemErrorCode.INVALID_SYSTEM_SCENARIO, exc, run_log)
        except Exception as exc:  # noqa: BLE001 - 任何仿真/评价异常都必须持久化为 failed
            self._fail(record, stage, exc, run_log)
        finally:
            run_log.removeHandler(handler)
            handler.close()
            if (artifact_dir / RUN_LOG.name).is_file() and RUN_LOG.name not in {a.name for a in record.artifacts}:
                record.artifacts.append(RUN_LOG)
            self._store.update(record)
            logger.info("%s %s", record.experiment_id, record.status.value.upper())

    def _evaluate_kpis(self, record: SystemExperimentRecord, result, descriptor) -> list[KpiResult]:
        context = KpiContext(
            source_experiment=record.experiment_id,
            backend=descriptor.id,
            scenario_id=result.scenario_id,
            seed=result.seed,
            source_type=descriptor.source_type,
        )
        inputs = [
            UeThroughputInput(ue_id=u.ue_id, decoded_bits=u.decoded_bits, simulated_duration_s=u.simulated_duration_s)
            for u in result.ue_results
        ]
        try:
            return self._kpis.evaluate(inputs, context)
        except Exception as exc:  # noqa: BLE001
            raise KpiCalculationError(str(exc)) from exc

    def _metadata(self, record: SystemExperimentRecord, scenario: SystemScenario, descriptor) -> dict[str, Any]:
        result = record.result
        return {
            "platform_version": self._platform_version,
            "git_commit": self._git_commit,
            "experiment_id": record.experiment_id,
            "experiment_type": record.experiment_type.value,
            "purpose": record.purpose.value,
            "optimization_id": record.optimization_id,
            "optimization_candidate_id": record.optimization_candidate_id,
            "evaluation_context": record.evaluation_context.model_dump() if record.evaluation_context else None,
            "backend": descriptor.id,
            "backend_version": record.backend_version,
            "provider_versions": result.provider_versions if result else {},
            "scenario": {"id": scenario.scenario_id, "scene": scenario.scene,
                         "bs_count": len(scenario.base_stations), "cell_count": len(scenario.cells),
                         "ue_count": scenario.ue_count},
            "seed": scenario.seed,
            "traffic_model": scenario.traffic.model_dump(mode="json"),
            "simulation_horizon": {"num_slots": scenario.simulation.num_slots,
                                   "warmup_slots": scenario.simulation.warmup_slots,
                                   "slot_duration_s": scenario.simulation.slot_duration_s},
            "channel_reused": result.channel_reused if result else None,
            "scheduler": result.scheduler if result else None,
            "link_adaptation": result.link_adaptation if result else None,
            "power_control": result.power_control if result else None,
            "ue_generation": result.ue_generation if result else None,
            "kpi_versions": {k.metric_id: k.version for k in record.kpis},
            "source_type": descriptor.source_type,
            "model_type": descriptor.model_type.value,
            "measured": False,
            "created_at": record.created_at.isoformat(),
            "runtime": result.runtime.model_dump() if result else None,
            "compute_device": result.compute_device if result else None,
            "assumptions": list(scenario.assumptions),
        }

    def _fail(self, record: SystemExperimentRecord, code: SystemErrorCode, exc: BaseException,
              run_log: logging.Logger) -> None:
        run_log.exception("System experiment failed: %s", exc)
        logger.warning("%s FAILED %s: %s", record.experiment_id, code.value, exc)
        record.error = SystemExperimentError(code=code, message=str(exc) or type(exc).__name__, type=type(exc).__name__)
        record.transition(SystemExperimentStatus.FAILED)
