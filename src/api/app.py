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

from . import __version__
from .errors import install_error_handlers
from .routes import experiments, health, scenarios
from .schemas import API_PREFIX


def create_app(service: ExperimentService, cors_origins: list[str] | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        service.close()

    app = FastAPI(
        title="5G Learning Optimization Simulation & Validation Platform API",
        description=(
            "5G 网络学习优化仿真验证平台 API（Day 2）。当前所有结果均为仿真生成数据"
            "（Simulation Generated），不是实测或现网数据。"
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.state.service = service

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    install_error_handlers(app)
    for router in (health.router, scenarios.router, experiments.router):
        app.include_router(router, prefix=API_PREFIX)
    return app
