"""
生产入口：装配默认后端、实验仓库、场景目录、优化服务与系统级仿真服务。
Production entrypoint wiring the default backends, stores, scenario catalogs, optimization and system services.

    uvicorn api.main:app --app-dir src
"""

from __future__ import annotations

import logging
import subprocess

from fastapi import FastAPI

from evaluation.kpi import default_kpi_registry
from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from optimization import (
    FileOptimizationStore,
    OptimizationService,
    default_objective_registry,
    default_optimizer_registry,
)
from simulation.backends import default_registry
from simulation.backends.system import default_system_registry
from system_simulation import FileSystemExperimentStore, SystemExperimentService, SystemScenarioCatalog

from . import __version__
from .app import create_app
from .settings import REPO_ROOT, Settings


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=7"], cwd=REPO_ROOT,
                             capture_output=True, text=True, timeout=5, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def build_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    service = ExperimentService(
        store=FileExperimentStore(settings.data_dir),
        registry=default_registry(include_testing=settings.testing),
        catalog=ScenarioCatalog(settings.configs_dir),
        timeout_seconds=settings.experiment_timeout_seconds,
    )
    optimization_service = OptimizationService(
        experiments=service,
        store=FileOptimizationStore(settings.optimizations_dir),
        optimizers=default_optimizer_registry(),
        objectives=default_objective_registry(),
    )
    system_service = SystemExperimentService(
        store=FileSystemExperimentStore(settings.system_experiments_dir),
        registry=default_system_registry(include_testing=settings.testing),
        catalog=SystemScenarioCatalog(settings.system_configs_dir),
        kpis=default_kpi_registry(),
        platform_version=__version__,
        git_commit=_git_commit(),
    )
    return create_app(
        service,
        cors_origins=list(settings.cors_origins),
        testing=settings.testing,
        optimization_service=optimization_service,
        system_service=system_service,
    )


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
app = build_app()
