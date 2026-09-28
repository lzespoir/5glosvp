"""
统一 API 错误模型 / Unified API error model.

浏览器只会收到 {"error": {code, message_zh, message_en, detail}}，traceback 只写日志。
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from experiments import ArtifactNotFoundError, ExperimentNotFoundError, ScenarioNotFoundError
from optimization import (
    InvalidParameterSpaceError,
    ObjectiveNotFoundError,
    OptimizationNotFoundError,
    OptimizerNotFoundError,
)
from simulation import BackendUnavailableError

from .schemas import ErrorBody, ErrorResponse

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    SCENARIO_NOT_FOUND = "SCENARIO_NOT_FOUND"
    EXPERIMENT_NOT_FOUND = "EXPERIMENT_NOT_FOUND"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    SIMULATION_FAILED = "SIMULATION_FAILED"
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    OPTIMIZER_NOT_FOUND = "OPTIMIZER_NOT_FOUND"
    OBJECTIVE_NOT_FOUND = "OBJECTIVE_NOT_FOUND"
    OPTIMIZATION_NOT_FOUND = "OPTIMIZATION_NOT_FOUND"
    INVALID_PARAMETER_SPACE = "INVALID_PARAMETER_SPACE"
    OPTIMIZATION_FAILED = "OPTIMIZATION_FAILED"


# code → (HTTP status, 中文, English)
_ERRORS: dict[ErrorCode, tuple[int, str, str]] = {
    ErrorCode.SCENARIO_NOT_FOUND: (404, "场景不存在", "Scenario not found"),
    ErrorCode.EXPERIMENT_NOT_FOUND: (404, "实验不存在", "Experiment not found"),
    ErrorCode.BACKEND_UNAVAILABLE: (503, "仿真后端不可用", "Simulation backend unavailable"),
    ErrorCode.SIMULATION_FAILED: (500, "仿真运行失败", "Simulation failed"),
    ErrorCode.ARTIFACT_NOT_FOUND: (404, "实验产物不存在", "Artifact not found"),
    ErrorCode.INVALID_REQUEST: (422, "请求参数无效", "Invalid request"),
    ErrorCode.NOT_FOUND: (404, "资源不存在", "Resource not found"),
    ErrorCode.INTERNAL_ERROR: (500, "服务器内部错误", "Internal server error"),
    ErrorCode.OPTIMIZER_NOT_FOUND: (404, "优化器不存在", "Optimizer not found"),
    ErrorCode.OBJECTIVE_NOT_FOUND: (404, "目标函数不存在", "Objective not found"),
    ErrorCode.OPTIMIZATION_NOT_FOUND: (404, "优化实验不存在", "Optimization not found"),
    ErrorCode.INVALID_PARAMETER_SPACE: (422, "搜索空间无效", "Invalid parameter space"),
    ErrorCode.OPTIMIZATION_FAILED: (500, "优化运行失败", "Optimization failed"),
}


def error_response(code: ErrorCode, detail: dict[str, Any] | None = None) -> JSONResponse:
    status, zh, en = _ERRORS[code]
    body = ErrorResponse(
        error=ErrorBody(code=code.value, message_zh=zh, message_en=en, detail=detail or {})
    )
    return JSONResponse(status_code=status, content=body.model_dump())


_EXCEPTION_CODES: list[tuple[type[Exception], ErrorCode]] = [
    (ScenarioNotFoundError, ErrorCode.SCENARIO_NOT_FOUND),
    (ExperimentNotFoundError, ErrorCode.EXPERIMENT_NOT_FOUND),
    (ArtifactNotFoundError, ErrorCode.ARTIFACT_NOT_FOUND),
    (BackendUnavailableError, ErrorCode.BACKEND_UNAVAILABLE),
    (OptimizerNotFoundError, ErrorCode.OPTIMIZER_NOT_FOUND),
    (ObjectiveNotFoundError, ErrorCode.OBJECTIVE_NOT_FOUND),
    (OptimizationNotFoundError, ErrorCode.OPTIMIZATION_NOT_FOUND),
    (InvalidParameterSpaceError, ErrorCode.INVALID_PARAMETER_SPACE),
]


def install_error_handlers(app: FastAPI) -> None:
    for exc_type, code in _EXCEPTION_CODES:

        def _handler(request: Request, exc: Exception, _code: ErrorCode = code) -> JSONResponse:
            logger.info("%s %s -> %s: %s", request.method, request.url.path, _code.value, exc)
            return error_response(_code, {"reason": str(exc)})

        app.add_exception_handler(exc_type, _handler)

    @app.exception_handler(RequestValidationError)
    def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        return error_response(ErrorCode.INVALID_REQUEST, {"errors": errors})

    @app.exception_handler(StarletteHTTPException)
    def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(ErrorCode.NOT_FOUND, {"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorBody(
                    code=f"HTTP_{exc.status_code}", message_zh=str(exc.detail),
                    message_en=str(exc.detail),
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(ErrorCode.INTERNAL_ERROR, {"type": type(exc).__name__})
