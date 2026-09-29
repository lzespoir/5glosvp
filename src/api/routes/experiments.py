from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse

from experiments import ExperimentService

from ..deps import get_service
from ..schemas import (
    ArtifactList,
    ArtifactView,
    ErrorResponse,
    ExperimentCreateRequest,
    ExperimentList,
    ExperimentResponse,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])

ServiceDep = Annotated[ExperimentService, Depends(get_service)]

# 浏览器内联查看的类型；其余（如 .npz）作为附件下载
_INLINE_MEDIA_TYPES = {"image/png", "application/json", "application/yaml", "text/plain"}


@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="创建并运行实验 / Create and run an experiment",
    description=(
        "Day 2 同步执行：请求在仿真完成（或超时）后返回。仿真失败时仍返回 201，"
        "实验 status=failed 并包含 error。/ Runs synchronously; a failed simulation "
        "still returns 201 with status=failed and an error object."
    ),
)
def create_experiment(body: ExperimentCreateRequest, service: ServiceDep) -> ExperimentResponse:
    record = service.create_experiment(
        name=body.name, scenario_id=body.scenario_id,
        scenario_version=body.scenario_version,
        scenario_definition_hash=body.scenario_definition_hash,
        scenario_instance_id=body.scenario_instance_id,
    )
    return ExperimentResponse.from_record(record)


@router.get("", response_model=ExperimentList, summary="实验列表（最新在前）/ Experiments, newest first")
def list_experiments(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExperimentList:
    records, total = service.list_experiments(limit=limit, offset=offset)
    return ExperimentList(
        items=[ExperimentResponse.from_record(r) for r in records],
        total=total, limit=limit, offset=offset,
    )


@router.get(
    "/{experiment_id}",
    response_model=ExperimentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="实验详情 / Experiment detail",
)
def get_experiment(experiment_id: str, service: ServiceDep) -> ExperimentResponse:
    return ExperimentResponse.from_record(service.get_experiment(experiment_id))


@router.get(
    "/{experiment_id}/artifacts",
    response_model=ArtifactList,
    responses={404: {"model": ErrorResponse}},
    summary="实验产物列表 / Experiment artifacts",
)
def list_artifacts(experiment_id: str, service: ServiceDep) -> ArtifactList:
    return ArtifactList(
        items=[ArtifactView.from_artifact(experiment_id, a) for a in service.list_artifacts(experiment_id)]
    )


@router.get(
    "/{experiment_id}/artifacts/{artifact_name:path}",
    response_class=FileResponse,
    responses={404: {"model": ErrorResponse}},
    summary="下载/查看实验产物 / Download or view an artifact",
)
def get_artifact(experiment_id: str, artifact_name: str, service: ServiceDep) -> FileResponse:
    artifact, path = service.resolve_artifact(experiment_id, artifact_name)
    return FileResponse(
        path,
        media_type=artifact.media_type,
        filename=artifact.name,
        content_disposition_type="inline" if artifact.media_type in _INLINE_MEDIA_TYPES else "attachment",
    )
