from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse

from system_optimization import SystemOptimizationService

from ..deps import get_system_optimization_service
from ..schemas import ErrorResponse
from ..system_optimization_schemas import (
    BenchmarkProtocolList,
    SystemObjectiveList,
    SystemObjectiveView,
    SystemOptimizationCreateRequest,
    SystemOptimizationList,
    SystemOptimizationResponse,
    SystemOptimizerList,
    SystemOptimizerView,
    SystemParameterList,
    SystemParameterView,
)

router = APIRouter(tags=["system-optimization"])

ServiceDep = Annotated[SystemOptimizationService, Depends(get_system_optimization_service)]
_INLINE_MEDIA_TYPES = {"image/png", "application/json"}


@router.get("/system-optimizers", response_model=SystemOptimizerList,
            summary="支持系统级问题的优化器 / Optimizers supporting system problems")
def list_system_optimizers(service: ServiceDep) -> SystemOptimizerList:
    return SystemOptimizerList(items=[SystemOptimizerView.from_optimizer(o) for o in service.list_optimizers()])


@router.get("/system-objectives", response_model=SystemObjectiveList, summary="系统级目标 / System objectives")
def list_system_objectives(service: ServiceDep) -> SystemObjectiveList:
    return SystemObjectiveList(items=[SystemObjectiveView.from_objective(o) for o in service.list_objectives()])


@router.get("/system-parameters", response_model=SystemParameterList,
            summary="系统级优化变量 / System optimization variables")
def list_system_parameters(service: ServiceDep) -> SystemParameterList:
    return SystemParameterList(items=[SystemParameterView.from_parameter(p) for p in service.list_parameters()])


@router.get("/benchmark-protocols", response_model=BenchmarkProtocolList,
            summary="冻结评价协议 / Frozen benchmark protocols")
def list_benchmark_protocols(service: ServiceDep) -> BenchmarkProtocolList:
    return BenchmarkProtocolList(items=service.list_protocols())


@router.post(
    "/system-optimizations",
    response_model=SystemOptimizationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse},
               503: {"model": ErrorResponse}},
    summary="创建并后台运行系统级优化 / Create a system optimization (runs in background)",
    description=(
        "校验通过后立即返回 202（status=created/running）；通过 GET /system-optimizations/{id} 轮询真实阶段进度。"
        "同一时间只允许一个系统级优化运行（409）。"
    ),
)
def create_system_optimization(
    body: SystemOptimizationCreateRequest, service: ServiceDep
) -> SystemOptimizationResponse:
    record = service.create(
        name=body.name, scenario_id=body.scenario_id, optimizer_id=body.optimizer_id,
        objective_id=body.objective_id, parameter_id=body.parameter.id,
        candidate_values=body.parameter.candidate_values, benchmark_protocol_id=body.benchmark_protocol_id,
        backend_id=body.backend_id,
    )
    return SystemOptimizationResponse.from_record(record)


@router.get("/system-optimizations", response_model=SystemOptimizationList,
            summary="系统级优化列表 / System optimizations")
def list_system_optimizations(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SystemOptimizationList:
    records, total = service.list(limit=limit, offset=offset)
    return SystemOptimizationList(items=[SystemOptimizationResponse.from_record(r) for r in records], total=total,
                                  limit=limit, offset=offset)


@router.get("/system-optimizations/{optimization_id}", response_model=SystemOptimizationResponse,
            responses={404: {"model": ErrorResponse}}, summary="系统级优化详情 / System optimization detail")
def get_system_optimization(optimization_id: str, service: ServiceDep) -> SystemOptimizationResponse:
    return SystemOptimizationResponse.from_record(service.get(optimization_id))


@router.get("/system-optimizations/{optimization_id}/artifacts/{artifact_name}", response_class=FileResponse,
            responses={404: {"model": ErrorResponse}}, summary="系统级优化证据 / System optimization artifact")
def get_system_optimization_artifact(optimization_id: str, artifact_name: str, service: ServiceDep) -> FileResponse:
    artifact, path = service.resolve_artifact(optimization_id, artifact_name)
    return FileResponse(path, media_type=artifact.media_type, filename=artifact.name,
                        content_disposition_type="inline" if artifact.media_type in _INLINE_MEDIA_TYPES
                        else "attachment")
