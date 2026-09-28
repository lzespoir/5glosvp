"""
实验编排（与后端无关）/ Backend-agnostic experiment orchestration.

Config -> Backend.load_scenario -> Backend.run -> Backend.export
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .artifacts import RUN_LOG, ensure_writable_dir, finalize_result_files
from .base import SimulationBackend
from .models import ScenarioConfig, SimulationResult, new_experiment_id

logger = logging.getLogger(__name__)

# (step_key, status) 回调，用于 CLI 展示进度
StepCallback = Callable[[str, str], None]

STEPS: list[tuple[str, str]] = [
    ("load_scene", "Loading scene / 加载场景"),
    ("run", "Running radio map / 计算无线电地图"),
    ("export", "Exporting artifacts / 导出结果"),
]


@dataclass
class ExperimentOutcome:
    result: SimulationResult
    output_dir: Path


def _noop(_step: str, _status: str) -> None:
    return None


class _CurrentThreadFilter(logging.Filter):
    """run.log 只记录执行本实验的线程产生的日志（避免并发请求日志混入）。"""

    def __init__(self) -> None:
        super().__init__()
        self._thread_id = threading.get_ident()

    def filter(self, record: logging.LogRecord) -> bool:
        return record.thread == self._thread_id


def run_experiment(
    backend: SimulationBackend,
    config: ScenarioConfig,
    output_root: Path,
    on_step: StepCallback = _noop,
    experiment_id: str | None = None,
) -> ExperimentOutcome:
    """在 output_root/<experiment_id>/ 下执行一次实验。"""
    experiment_id = experiment_id or new_experiment_id()
    return execute_experiment(
        backend, config, Path(output_root) / experiment_id, experiment_id, on_step
    )


def execute_experiment(
    backend: SimulationBackend,
    config: ScenarioConfig,
    output_dir: Path,
    experiment_id: str,
    on_step: StepCallback = _noop,
) -> ExperimentOutcome:
    """在指定的产物目录中执行一次实验，并写入 run.log。"""
    output_dir = ensure_writable_dir(Path(output_dir))

    handler = logging.FileHandler(output_dir / RUN_LOG, encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.addFilter(_CurrentThreadFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    # run.log 始终记录 INFO；控制台输出级别由各 console handler 自身的 level 控制
    root.setLevel(min(previous_level or logging.INFO, logging.INFO))

    t_start = time.perf_counter()
    current = STEPS[0][0]
    try:
        logger.info(
            "Experiment start: experiment_id=%s backend=%s scenario=%s scene=%s",
            experiment_id, backend.name, config.scenario_id, config.scene_name,
        )

        on_step(current, "RUNNING")
        backend.load_scenario(config)
        scenario_load_seconds = time.perf_counter() - t_start
        on_step(current, "PASS")

        current = "run"
        on_step(current, "RUNNING")
        result = backend.run(experiment_id=experiment_id)
        on_step(current, "PASS")

        current = "export"
        on_step(current, "RUNNING")
        t_export = time.perf_counter()
        backend.export(result, output_dir)
        t_end = time.perf_counter()
        result.runtime.scenario_load_seconds = scenario_load_seconds
        result.runtime.artifact_export_seconds = t_end - t_export
        result.runtime.total_seconds = t_end - t_start
        finalize_result_files(result, output_dir)
        on_step(current, "PASS")

        logger.info(
            "Experiment finish: experiment_id=%s simulation=%.3f s export=%.3f s total=%.3f s",
            experiment_id,
            result.runtime.simulation_seconds,
            result.runtime.artifact_export_seconds,
            result.runtime.total_seconds,
        )
        for w in result.warnings:
            logger.warning(w)
        return ExperimentOutcome(result, output_dir)
    except Exception:
        on_step(current, "FAIL")
        logger.exception("Experiment failed at step '%s': experiment_id=%s", current, experiment_id)
        raise
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
        handler.close()
