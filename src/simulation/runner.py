"""
实验编排（与后端无关）/ Backend-agnostic experiment orchestration.

Config -> Backend.load_scenario -> Backend.run -> Backend.export
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .artifacts import RUN_LOG, ensure_writable_dir
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
    total_runtime_seconds: float


def _noop(_step: str, _status: str) -> None:
    return None


def run_experiment(
    backend: SimulationBackend,
    config: ScenarioConfig,
    output_root: Path,
    on_step: StepCallback = _noop,
    experiment_id: str | None = None,
) -> ExperimentOutcome:
    experiment_id = experiment_id or new_experiment_id()
    output_dir = ensure_writable_dir(Path(output_root) / experiment_id)

    handler = logging.FileHandler(output_dir / RUN_LOG, encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    # run.log 始终记录 INFO；控制台输出级别由各 console handler 自身的 level 控制
    root.setLevel(min(previous_level or logging.INFO, logging.INFO))

    t0 = time.perf_counter()
    current = STEPS[0][0]
    try:
        logger.info(
            "Experiment start: experiment_id=%s backend=%s scenario=%s scene=%s",
            experiment_id, backend.name, config.scenario_id, config.scene_name,
        )

        on_step(current, "RUNNING")
        backend.load_scenario(config)
        on_step(current, "PASS")

        current = "run"
        on_step(current, "RUNNING")
        result = backend.run(experiment_id=experiment_id)
        on_step(current, "PASS")

        current = "export"
        on_step(current, "RUNNING")
        total_runtime = time.perf_counter() - t0
        result.metadata["total_runtime_seconds"] = total_runtime
        result.metadata["simulation_runtime_seconds"] = result.runtime_seconds
        backend.export(result, output_dir)
        on_step(current, "PASS")

        logger.info(
            "Experiment finish: experiment_id=%s simulation_runtime=%.3f s total_runtime=%.3f s",
            experiment_id, result.runtime_seconds, total_runtime,
        )
        for w in result.warnings:
            logger.warning(w)
        return ExperimentOutcome(result, output_dir, total_runtime)
    except Exception:
        on_step(current, "FAIL")
        logger.exception("Experiment failed at step '%s': experiment_id=%s", current, experiment_id)
        raise
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
        handler.close()
