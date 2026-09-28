from typing import Annotated

from fastapi import APIRouter, Depends

from optimization.models import OptimizationStatus
from system_optimization import SystemOptimizationService

from ..algorithm_schemas import (
    AlgorithmDetail,
    AlgorithmEvidenceStatus,
    AlgorithmList,
    AlgorithmSummary,
    AlgorithmValidateRequest,
    AlgorithmValidateResponse,
    EvidenceList,
)
from ..deps import get_system_optimization_service
from ..schemas import ErrorResponse
from ..system_optimization_schemas import algorithm_notice

router = APIRouter(tags=["algorithms"])

ServiceDep = Annotated[SystemOptimizationService, Depends(get_system_optimization_service)]


@router.get("/algorithms", response_model=AlgorithmList, summary="算法目录 / Algorithm catalog (registry)")
def list_algorithms(service: ServiceDep) -> AlgorithmList:
    return AlgorithmList(items=[AlgorithmSummary.from_metadata(m) for m in service.algorithms.list()])


@router.get("/algorithms/{algorithm_id}", response_model=AlgorithmDetail, responses={404: {"model": ErrorResponse}},
            summary="算法详情 / Algorithm detail")
def get_algorithm(algorithm_id: str, service: ServiceDep) -> AlgorithmDetail:
    metadata = service.algorithms.metadata(algorithm_id)
    runs = sorted((r for r in service.list_all() if r.optimizer_id == algorithm_id),
                  key=lambda r: r.created_at, reverse=True)
    succeeded = [r for r in runs if r.status is OptimizationStatus.SUCCEEDED]
    zh, en = algorithm_notice(metadata.category)
    return AlgorithmDetail(
        metadata=metadata, notice_zh=zh, notice_en=en,
        evidence=AlgorithmEvidenceStatus(
            optimization_runs=len(runs), succeeded_runs=len(succeeded),
            latest_optimization_id=runs[0].optimization_id if runs else None,
            latest_succeeded_optimization_id=succeeded[0].optimization_id if succeeded else None,
        ),
    )


@router.post(
    "/algorithms/{algorithm_id}/validate", response_model=AlgorithmValidateResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="算法—问题兼容性检查 / Check algorithm–problem compatibility",
    description="不兼容时返回 200 且 compatible=false（附错误代码）；参数空间本身无效时返回 422。",
)
def validate_algorithm(algorithm_id: str, body: AlgorithmValidateRequest,
                       service: ServiceDep) -> AlgorithmValidateResponse:
    report = service.validate_algorithm(
        algorithm_id, body.specs(), body.objective_id, body.algorithm_hyperparameters,
        body.evaluation_budget.max_evaluations if body.evaluation_budget else None, body.scenario_id,
    )
    return AlgorithmValidateResponse(**report.model_dump())


@router.get("/evidence", response_model=EvidenceList,
            summary="证据描述符 / Evidence descriptors (verification ≠ acceptance)")
def list_evidence(service: ServiceDep) -> EvidenceList:
    items = [service.evidence(r) for r in sorted(service.list_all(), key=lambda r: r.created_at, reverse=True)]
    return EvidenceList(items=items, total=len(items))
