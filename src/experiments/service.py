"""
实验服务 / Experiment service.

职责：创建实验、校验场景、解析后端、执行实验、更新状态、保存结果/错误、解析产物。
HTTP Router 不承担这些业务逻辑。
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from simulation import (
    ArtifactExportError,
    BackendUnavailableError,
    ScenarioConfig,
    ScenarioConfigError,
    SimulationBackend,
    new_experiment_id,
)
from simulation.artifacts import RADIO_MAP_NPZ, RUN_LOG, load_radio_map_layers, media_type_for
from simulation.models import Artifact
from simulation.registry import BackendDescriptor, BackendRegistry
from simulation.runner import execute_experiment

from .errors import ArtifactNotFoundError, ExperimentNotFoundError
from .models import (
    ExperimentError,
    ExperimentErrorCode,
    ExperimentPurpose,
    ExperimentRecord,
    ExperimentStatus,
    utc_now,
)
from .scenarios import ScenarioCatalog
from .store import ExperimentStore

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 600.0


@dataclass
class BackendStatus:
    descriptor: BackendDescriptor
    health: dict[str, Any]


def _error_code_for(exc: BaseException) -> ExperimentErrorCode:
    if isinstance(exc, BackendUnavailableError):
        return ExperimentErrorCode.BACKEND_UNAVAILABLE
    if isinstance(exc, ScenarioConfigError):
        return ExperimentErrorCode.SCENARIO_INVALID
    if isinstance(exc, ArtifactExportError):
        return ExperimentErrorCode.ARTIFACT_EXPORT_FAILED
    return ExperimentErrorCode.SIMULATION_FAILED


class ExperimentService:
    """
    同步执行实验（Day 2）。实验在单工作线程中串行执行，请求线程最多等待 timeout 秒。
    """

    def __init__(
        self,
        store: ExperimentStore,
        registry: BackendRegistry,
        catalog: ScenarioCatalog,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._store = store
        self._registry = registry
        self._catalog = catalog
        self._timeout = timeout_seconds
        # 所有状态迁移在此锁内进行，防止超时处理与工作线程互相覆盖
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="experiment")

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ------------------------------------------------------------------
    # Backends / Scenarios
    # ------------------------------------------------------------------

    def list_backends(self) -> list[BackendStatus]:
        return [
            BackendStatus(descriptor=d, health=d.factory().health_check())
            for d in self._registry.list()
        ]

    def list_scenarios(self) -> list[ScenarioConfig]:
        return self._catalog.list()

    def get_scenario(self, scenario_id: str) -> ScenarioConfig:
        return self._catalog.get(scenario_id)

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    def get_experiment(self, experiment_id: str) -> ExperimentRecord:
        record = self._store.get(experiment_id)
        if record is None:
            raise ExperimentNotFoundError(f"Experiment not found: {experiment_id}")
        return record

    def list_experiments(self, limit: int = 50, offset: int = 0) -> tuple[list[ExperimentRecord], int]:
        return self._store.list(limit=limit, offset=offset), self._store.count()

    def create_experiment(self, name: str, scenario_id: str) -> ExperimentRecord:
        return self.run_experiment(name, self._catalog.get(scenario_id))

    def backend_descriptor(self, backend_id: str) -> BackendDescriptor:
        return self._registry.get(backend_id)

    def ensure_backend_available(self, backend_id: str) -> tuple[SimulationBackend, dict[str, Any]]:
        backend = self._registry.create(backend_id)
        health = backend.health_check()
        if not health.get("available"):
            reason = "; ".join(health.get("errors") or []) or "backend not available"
            raise BackendUnavailableError(f"Backend '{backend_id}' unavailable: {reason}")
        return backend, health

    def run_experiment(
        self,
        name: str,
        config: ScenarioConfig,
        purpose: ExperimentPurpose = ExperimentPurpose.MANUAL,
        optimization_id: str | None = None,
    ) -> ExperimentRecord:
        """用给定（可能是派生的）场景配置同步运行一次实验。"""
        backend, health = self.ensure_backend_available(config.backend)

        record = ExperimentRecord(
            experiment_id=self._new_unique_id(),
            name=name,
            status=ExperimentStatus.CREATED,
            purpose=purpose,
            optimization_id=optimization_id,
            scenario_id=config.scenario_id,
            scenario_name_zh=config.name_zh,
            scenario_name_en=config.name_en,
            backend=config.backend,
            backend_version=health.get("version"),
            created_at=utc_now(),
            config=config.model_dump(mode="json"),
        )
        record.transition(ExperimentStatus.CREATED)
        self._store.create(record)
        self._log_transition(record)

        with self._lock:
            record.transition(ExperimentStatus.QUEUED)
            self._store.update(record)
        self._log_transition(record)

        future = self._executor.submit(self._execute, record.experiment_id, backend, config)
        try:
            future.result(timeout=self._timeout)
        except FutureTimeoutError:
            self._mark_timeout(record.experiment_id)
        return self.get_experiment(record.experiment_id)

    def list_artifacts(self, experiment_id: str) -> list[Artifact]:
        return self.get_experiment(experiment_id).artifacts

    def resolve_artifact(self, experiment_id: str, artifact_name: str) -> tuple[Artifact, Path]:
        record = self.get_experiment(experiment_id)
        artifact = next((a for a in record.artifacts if a.name == artifact_name), None)
        if artifact is None:
            raise ArtifactNotFoundError(
                f"Artifact {artifact_name!r} not found in experiment {experiment_id}"
            )
        return artifact, self._store.resolve_artifact(experiment_id, artifact.path)

    def radio_map_layers(self, experiment_id: str) -> dict[str, np.ndarray]:
        """实验 radio_map.npz 中的数值层（rss / path_gain / sinr …）。"""
        _, path = self.resolve_artifact(experiment_id, RADIO_MAP_NPZ)
        return load_radio_map_layers(path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _new_unique_id(self) -> str:
        while True:
            experiment_id = new_experiment_id()
            if self._store.get(experiment_id) is None:
                return experiment_id

    @staticmethod
    def _log_transition(record: ExperimentRecord) -> None:
        logger.info(
            "%s %s scenario=%s backend=%s",
            record.experiment_id, record.status.name, record.scenario_id, record.backend,
        )

    def _execute(self, experiment_id: str, backend: SimulationBackend, config: ScenarioConfig) -> None:
        """工作线程入口：不向外抛异常，所有失败都持久化为 FAILED。"""
        with self._lock:
            record = self.get_experiment(experiment_id)
            if record.status.is_terminal:
                logger.warning("%s already %s; skipping execution", experiment_id, record.status.name)
                return
            record.started_at = utc_now()
            record.transition(ExperimentStatus.RUNNING)
            self._store.update(record)
        self._log_transition(record)

        try:
            outcome = execute_experiment(
                backend, config, self._store.artifact_dir(experiment_id), experiment_id
            )
        except Exception as e:  # noqa: BLE001 - 任何失败都必须落为 FAILED，traceback 已写入日志
            logger.exception("%s simulation failed", experiment_id)
            self._finish_failed(
                experiment_id,
                ExperimentError(code=_error_code_for(e), message=str(e), type=type(e).__name__),
            )
            return

        result = outcome.result
        with self._lock:
            record = self.get_experiment(experiment_id)
            if record.status.is_terminal:
                logger.warning(
                    "%s finished after being marked %s; result kept on disk only",
                    experiment_id, record.status.name,
                )
                return
            record.result = result
            record.artifacts = list(result.artifacts)
            record.runtime = result.runtime
            record.backend_version = result.backend_version
            record.provenance = {
                "source_type": result.metadata.get("source_type"),
                **result.metadata.get("provenance", {}),
            }
            record.finished_at = utc_now()
            record.transition(ExperimentStatus.SUCCEEDED)
            self._store.update(record)
        logger.info(
            "%s SUCCEEDED simulation=%.3f s total=%.3f s",
            experiment_id, result.runtime.simulation_seconds, result.runtime.total_seconds,
        )

    def _finish_failed(self, experiment_id: str, error: ExperimentError) -> None:
        with self._lock:
            record = self.get_experiment(experiment_id)
            if record.status.is_terminal:
                return
            record.error = error
            if (self._store.artifact_dir(experiment_id) / RUN_LOG).is_file():
                record.artifacts = [
                    Artifact(
                        name=RUN_LOG, path=RUN_LOG, kind="log",
                        media_type=media_type_for(RUN_LOG), description="Run log / 运行日志",
                    )
                ]
            record.finished_at = utc_now()
            record.transition(ExperimentStatus.FAILED)
            self._store.update(record)
        logger.error("%s FAILED code=%s %s: %s", experiment_id, error.code.value, error.type, error.message)

    def _mark_timeout(self, experiment_id: str) -> None:
        self._finish_failed(
            experiment_id,
            ExperimentError(
                code=ExperimentErrorCode.SIMULATION_TIMEOUT,
                message=(
                    f"Experiment did not finish within {self._timeout:.0f} s "
                    "(soft timeout; the worker thread cannot be force-stopped)"
                ),
                type="TimeoutError",
            ),
        )
