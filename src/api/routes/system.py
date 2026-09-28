from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse

from system_simulation import (
    Capability,
    SystemBackendNotFoundError,
    SystemExperimentRecord,
    SystemExperimentService,
)
from system_simulation.base import SystemBackendDescriptor

from ..deps import get_system_service
from ..schemas import ErrorResponse
from ..system_schemas import (
    KpiDefinitionList,
    SystemBackendList,
    SystemBackendView,
    SystemExperimentCreateRequest,
    SystemExperimentList,
    SystemExperimentResponse,
    SystemScenarioDetail,
    SystemScenarioList,
    SystemScenarioSummary,
)

router = APIRouter(tags=["system"])

ServiceDep = Annotated[SystemExperimentService, Depends(get_system_service)]

_INLINE_MEDIA_TYPES = {"image/png", "application/json", "application/x-yaml", "text/plain"}


def _descriptor(service: SystemExperimentService, backend_id: str) -> SystemBackendDescriptor | None:
    try:
        return service.backend_descriptor(backend_id)
    except SystemBackendNotFoundError:
        return None


def _to_response(service: SystemExperimentService, record: SystemExperimentRecord) -> SystemExperimentResponse:
    return SystemExperimentResponse.from_record(record, _descriptor(service, record.backend))


@router.get("/system-backends", response_model=SystemBackendList, summary="系统级后端 / System backends")
def list_system_backends(
    service: ServiceDep,
    capability: Annotated[Capability | None, Query(description="按能力过滤 / Filter by capability")] = None,
) -> SystemBackendList:
    return SystemBackendList(items=[SystemBackendView.from_status(s) for s in service.list_backends(capability)])


@router.get("/system-scenarios", response_model=SystemScenarioList, summary="系统级场景 / System scenarios")
def list_system_scenarios(service: ServiceDep) -> SystemScenarioList:
    return SystemScenarioList(items=[SystemScenarioSummary.from_scenario(s) for s in service.list_scenarios()])


@router.get(
    "/system-scenarios/{scenario_id}",
    response_model=SystemScenarioDetail,
    responses={404: {"model": ErrorResponse}},
    summary="系统级场景详情 / System scenario detail",
)
def get_system_scenario(scenario_id: str, service: ServiceDep) -> SystemScenarioDetail:
    return SystemScenarioDetail.from_scenario(service.get_scenario(scenario_id))


@router.get("/kpis", response_model=KpiDefinitionList, summary="KPI 定义 / KPI definitions")
def list_kpis(service: ServiceDep) -> KpiDefinitionList:
    return KpiDefinitionList(items=service.kpi_registry().definitions())


@router.post(
    "/system-experiments",
    response_model=SystemExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="创建并运行系统级实验 / Create and run a system experiment",
    description=(
        "同步执行（Sionna SYS 在 CPU 上约 40–60 s）。仿真失败时仍返回 201，status=failed 并包含 error。"
        "/ Runs synchronously; a failed run still returns 201 with status=failed."
    ),
)
def create_system_experiment(body: SystemExperimentCreateRequest, service: ServiceDep) -> SystemExperimentResponse:
    return _to_response(service, service.create(name=body.name, scenario_id=body.scenario_id,
                                                backend_id=body.backend_id))


@router.get("/system-experiments", response_model=SystemExperimentList, summary="系统级实验列表 / System experiments")
def list_system_experiments(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SystemExperimentList:
    records, total = service.list(limit=limit, offset=offset)
    return SystemExperimentList(items=[_to_response(service, r) for r in records], total=total,
                                limit=limit, offset=offset)


@router.get(
    "/system-experiments/{experiment_id}",
    response_model=SystemExperimentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="系统级实验详情 / System experiment detail",
)
def get_system_experiment(experiment_id: str, service: ServiceDep) -> SystemExperimentResponse:
    return _to_response(service, service.get(experiment_id))


@router.get(
    "/system-experiments/{experiment_id}/artifacts/{artifact_name}",
    response_class=FileResponse,
    responses={404: {"model": ErrorResponse}},
    summary="下载/查看系统级实验产物 / System experiment artifact",
)
def get_system_artifact(experiment_id: str, artifact_name: str, service: ServiceDep) -> FileResponse:
    artifact, path = service.resolve_artifact(experiment_id, artifact_name)
    return FileResponse(
        path, media_type=artifact.media_type, filename=artifact.name,
        content_disposition_type="inline" if artifact.media_type in _INLINE_MEDIA_TYPES else "attachment",
    )
