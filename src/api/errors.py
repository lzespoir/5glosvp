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

from algorithms import AlgorithmCompatibilityError, AlgorithmNotFoundError
from experiments import ArtifactNotFoundError, ExperimentNotFoundError, ScenarioNotFoundError
from optimization import (
    InvalidParameterSpaceError,
    ObjectiveNotFoundError,
    OptimizationNotFoundError,
    OptimizerNotFoundError,
)
from simulation import BackendUnavailableError
from system_optimization import (
    BenchmarkProtocolNotFoundError,
    SystemOptimizationArtifactNotFoundError,
    SystemOptimizationBusyError,
    SystemOptimizationNotFoundError,
    UnsupportedProblemTypeError,
)
from system_simulation import (
    InvalidSystemScenarioError,
    SystemArtifactNotFoundError,
    SystemBackendNotFoundError,
    SystemBackendUnavailableError,
    SystemCapabilityNotSupportedError,
    SystemExperimentNotFoundError,
    SystemScenarioNotFoundError,
)

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
    SYSTEM_SCENARIO_NOT_FOUND = "SYSTEM_SCENARIO_NOT_FOUND"
    SYSTEM_EXPERIMENT_NOT_FOUND = "SYSTEM_EXPERIMENT_NOT_FOUND"
    SYSTEM_BACKEND_NOT_FOUND = "SYSTEM_BACKEND_NOT_FOUND"
    SYSTEM_BACKEND_UNAVAILABLE = "SYSTEM_BACKEND_UNAVAILABLE"
    SYSTEM_CAPABILITY_NOT_SUPPORTED = "SYSTEM_CAPABILITY_NOT_SUPPORTED"
    SYSTEM_SIMULATION_FAILED = "SYSTEM_SIMULATION_FAILED"
    INVALID_SYSTEM_SCENARIO = "INVALID_SYSTEM_SCENARIO"
    NO_UE_RESULTS = "NO_UE_RESULTS"
    KPI_CALCULATION_FAILED = "KPI_CALCULATION_FAILED"
    SYSTEM_OPTIMIZATION_NOT_FOUND = "SYSTEM_OPTIMIZATION_NOT_FOUND"
    BENCHMARK_PROTOCOL_NOT_FOUND = "BENCHMARK_PROTOCOL_NOT_FOUND"
    SYSTEM_OPTIMIZATION_BUSY = "SYSTEM_OPTIMIZATION_BUSY"
    UNSUPPORTED_PROBLEM_TYPE = "UNSUPPORTED_PROBLEM_TYPE"
    ALGORITHM_NOT_FOUND = "ALGORITHM_NOT_FOUND"
    ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED = "ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED"
    ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED = "ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED"
    ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED = "ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED"
    ALGORITHM_CONSTRAINTS_NOT_SUPPORTED = "ALGORITHM_CONSTRAINTS_NOT_SUPPORTED"
    ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED = "ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED"
    INVALID_HYPERPARAMETER = "INVALID_HYPERPARAMETER"
    INVALID_EVALUATION_BUDGET = "INVALID_EVALUATION_BUDGET"


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
    ErrorCode.SYSTEM_SCENARIO_NOT_FOUND: (404, "系统级场景不存在", "System scenario not found"),
    ErrorCode.SYSTEM_EXPERIMENT_NOT_FOUND: (404, "系统级实验不存在", "System experiment not found"),
    ErrorCode.SYSTEM_BACKEND_NOT_FOUND: (404, "系统级仿真后端不存在", "System backend not found"),
    ErrorCode.SYSTEM_BACKEND_UNAVAILABLE: (503, "系统级仿真后端不可用", "System backend unavailable"),
    ErrorCode.SYSTEM_CAPABILITY_NOT_SUPPORTED: (
        422, "该后端不支持系统级仿真能力", "Backend does not support the system simulation capability"
    ),
    ErrorCode.SYSTEM_SIMULATION_FAILED: (500, "系统级仿真失败", "System simulation failed"),
    ErrorCode.INVALID_SYSTEM_SCENARIO: (422, "系统级场景无效", "Invalid system scenario"),
    ErrorCode.NO_UE_RESULTS: (500, "没有 UE 结果", "No UE results"),
    ErrorCode.KPI_CALCULATION_FAILED: (500, "KPI 计算失败", "KPI calculation failed"),
    ErrorCode.SYSTEM_OPTIMIZATION_NOT_FOUND: (404, "系统级优化不存在", "System optimization not found"),
    ErrorCode.BENCHMARK_PROTOCOL_NOT_FOUND: (404, "评价协议不存在", "Benchmark protocol not found"),
    ErrorCode.SYSTEM_OPTIMIZATION_BUSY: (
        409, "已有系统级优化正在运行，请稍后重试", "Another system optimization is running; retry later"
    ),
    ErrorCode.UNSUPPORTED_PROBLEM_TYPE: (422, "优化器不支持该问题类型", "Optimizer does not support this problem type"),
    ErrorCode.ALGORITHM_NOT_FOUND: (404, "算法不存在", "Algorithm not found"),
    ErrorCode.ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED: (
        422, "算法不支持该问题类型", "Algorithm does not support this problem type"
    ),
    ErrorCode.ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED: (
        422, "算法不支持该参数类型", "Algorithm does not support this parameter type"
    ),
    ErrorCode.ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED: (
        422, "参数数量超出算法支持范围", "Too many parameters for this algorithm"
    ),
    ErrorCode.ALGORITHM_CONSTRAINTS_NOT_SUPPORTED: (422, "算法不支持参数约束", "Algorithm does not support constraints"),
    ErrorCode.ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED: (
        422, "算法不支持多目标", "Algorithm does not support multiple objectives"
    ),
    ErrorCode.INVALID_HYPERPARAMETER: (422, "算法超参数无效", "Invalid algorithm hyperparameter"),
    ErrorCode.INVALID_EVALUATION_BUDGET: (422, "评价预算无效", "Invalid evaluation budget"),
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
    (SystemScenarioNotFoundError, ErrorCode.SYSTEM_SCENARIO_NOT_FOUND),
    (SystemExperimentNotFoundError, ErrorCode.SYSTEM_EXPERIMENT_NOT_FOUND),
    (SystemArtifactNotFoundError, ErrorCode.ARTIFACT_NOT_FOUND),
    (SystemBackendNotFoundError, ErrorCode.SYSTEM_BACKEND_NOT_FOUND),
    (SystemBackendUnavailableError, ErrorCode.SYSTEM_BACKEND_UNAVAILABLE),
    (SystemCapabilityNotSupportedError, ErrorCode.SYSTEM_CAPABILITY_NOT_SUPPORTED),
    (InvalidSystemScenarioError, ErrorCode.INVALID_SYSTEM_SCENARIO),
    (SystemOptimizationNotFoundError, ErrorCode.SYSTEM_OPTIMIZATION_NOT_FOUND),
    (SystemOptimizationArtifactNotFoundError, ErrorCode.ARTIFACT_NOT_FOUND),
    (BenchmarkProtocolNotFoundError, ErrorCode.BENCHMARK_PROTOCOL_NOT_FOUND),
    (SystemOptimizationBusyError, ErrorCode.SYSTEM_OPTIMIZATION_BUSY),
    (UnsupportedProblemTypeError, ErrorCode.UNSUPPORTED_PROBLEM_TYPE),
    (AlgorithmNotFoundError, ErrorCode.ALGORITHM_NOT_FOUND),
]


def install_error_handlers(app: FastAPI) -> None:
    for exc_type, code in _EXCEPTION_CODES:

        def _handler(request: Request, exc: Exception, _code: ErrorCode = code) -> JSONResponse:
            logger.info("%s %s -> %s: %s", request.method, request.url.path, _code.value, exc)
            return error_response(_code, {"reason": str(exc)})

        app.add_exception_handler(exc_type, _handler)

    @app.exception_handler(AlgorithmCompatibilityError)
    def _incompatible(request: Request, exc: AlgorithmCompatibilityError) -> JSONResponse:
        code = ErrorCode(exc.code.value)
        logger.info("%s %s -> %s: %s", request.method, request.url.path, code.value, exc)
        return error_response(code, {"reason": str(exc), "errors": [e.model_dump(mode="json") for e in exc.errors]})

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
