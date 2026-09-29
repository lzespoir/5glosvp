"""
FastAPI 应用工厂 / FastAPI application factory.

本模块不 import 任何具体仿真后端；生产环境的后端装配见 api/main.py。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from experiments import ExperimentService
from optimization import OptimizationService
from system_optimization import SystemOptimizationService
from system_simulation import SystemExperimentService
from scenarios import ScenarioSystemService

from . import __version__
from .errors import install_error_handlers
from .routes import algorithm_packages, algorithms, benchmarks, comparisons, experiments, health, optimizations, scenarios, scenario_system, system, system_optimization, user_association
from .schemas import API_PREFIX


def create_app(
    service: ExperimentService,
    cors_origins: list[str] | None = None,
    testing: bool = False,
    optimization_service: OptimizationService | None = None,
    system_service: SystemExperimentService | None = None,
    system_optimization_service: SystemOptimizationService | None = None,
    scenario_service: ScenarioSystemService | None = None,
) -> FastAPI:
    """optimization_service / system_service / system_optimization_service 为 None 时不挂载对应路由。"""
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        service.close()

    app = FastAPI(
        title="5G Learning Optimization Simulation & Validation Platform API",
        description=(
            "5G 网络学习优化仿真验证平台 API（Day 7）。当前所有结果均为仿真生成数据"
            "（Simulation Generated），不是实测或现网数据。"
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.state.service = service
    app.state.optimization_service = optimization_service
    app.state.system_service = system_service
    app.state.system_optimization_service = system_optimization_service
    app.state.scenario_service = scenario_service or ScenarioSystemService()
    app.state.testing = testing

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    install_error_handlers(app)
    for router in (health.router, scenarios.router, scenario_system.router, experiments.router, user_association.router, benchmarks.router, algorithm_packages.router, comparisons.router):
        app.include_router(router, prefix=API_PREFIX)
    if optimization_service is not None:
        app.include_router(optimizations.router, prefix=API_PREFIX)
    if system_service is not None:
        app.include_router(system.router, prefix=API_PREFIX)
    if system_optimization_service is not None:
        app.include_router(system_optimization.router, prefix=API_PREFIX)
        app.include_router(algorithms.router, prefix=API_PREFIX)
    return app
