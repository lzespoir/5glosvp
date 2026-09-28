"""
生产入口：装配默认后端、实验仓库与场景目录。
Production entrypoint wiring the default backends, store and scenario catalog.

    uvicorn api.main:app --app-dir src
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from experiments import ExperimentService, FileExperimentStore, ScenarioCatalog
from simulation.backends import default_registry

from .app import create_app
from .settings import Settings


def build_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    service = ExperimentService(
        store=FileExperimentStore(settings.data_dir),
        registry=default_registry(include_testing=settings.testing),
        catalog=ScenarioCatalog(settings.configs_dir),
        timeout_seconds=settings.experiment_timeout_seconds,
    )
    return create_app(service, cors_origins=list(settings.cors_origins))


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
app = build_app()
