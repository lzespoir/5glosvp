from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from optimization import OptimizationRecord, OptimizationService

from ..deps import get_optimization_service
from ..optimization_schemas import (
    ObjectiveList,
    ObjectiveView,
    OptimizationCreateRequest,
    OptimizationList,
    OptimizationResponse,
    OptimizerList,
    OptimizerView,
)
from ..schemas import ErrorResponse

router = APIRouter(tags=["optimizations"])

ServiceDep = Annotated[OptimizationService, Depends(get_optimization_service)]


def _to_response(service: OptimizationService, record: OptimizationRecord) -> OptimizationResponse:
    optimizers = {o.id: o for o in service.list_optimizers()}
    objectives = {o.id: o for o in service.list_objectives()}
    return OptimizationResponse.from_record(
        record, optimizers.get(record.optimizer_id), objectives.get(record.objective.id)
    )


@router.get("/optimizers", response_model=OptimizerList, summary="优化器列表 / Optimizers")
def list_optimizers(service: ServiceDep) -> OptimizerList:
    return OptimizerList(
        items=[OptimizerView.from_optimizer(o, service.max_candidates) for o in service.list_optimizers()]
    )


@router.get("/objectives", response_model=ObjectiveList, summary="目标函数列表 / Objectives")
def list_objectives(service: ServiceDep) -> ObjectiveList:
    return ObjectiveList(items=[ObjectiveView.from_objective(o) for o in service.list_objectives()])


@router.post(
    "/optimizations",
    response_model=OptimizationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="创建并运行优化 / Create and run an optimization",
    description=(
        "Day 4 同步执行：基线与全部候选评价完成后返回。候选失败时整个运行 status=failed（仍返回 201）。"
        "/ Runs synchronously; a failed candidate fails the whole run (still 201 with status=failed)."
    ),
)
def create_optimization(body: OptimizationCreateRequest, service: ServiceDep) -> OptimizationResponse:
    params = body.objective_params.model_dump(exclude_none=True) if body.objective_params else None
    record = service.create_optimization(
        name=body.name,
        scenario_id=body.scenario_id,
        optimizer_id=body.optimizer_id,
        objective_id=body.objective_id,
        parameter_space=body.parameter_space,
        objective_params=params,
    )
    return _to_response(service, record)


@router.get("/optimizations", response_model=OptimizationList, summary="优化列表（最新在前）/ Optimizations")
def list_optimizations(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OptimizationList:
    records, total = service.list(limit=limit, offset=offset)
    return OptimizationList(
        items=[_to_response(service, r) for r in records], total=total, limit=limit, offset=offset
    )


@router.get(
    "/optimizations/{optimization_id}",
    response_model=OptimizationResponse,
    responses={404: {"model": ErrorResponse}},
    summary="优化详情 / Optimization detail",
)
def get_optimization(optimization_id: str, service: ServiceDep) -> OptimizationResponse:
    return _to_response(service, service.get(optimization_id))
