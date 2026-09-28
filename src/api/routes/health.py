from typing import Annotated

from fastapi import APIRouter, Depends

from experiments import ExperimentService

from .. import __version__
from ..deps import get_service
from ..schemas import BackendInfo, BackendList, HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="平台状态 / Platform health",
    description="仅检查服务存活，不运行 Sionna 仿真。/ Liveness only; does not run a simulation.",
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="5glosvp",
        name_zh="5G网络学习优化仿真验证平台",
        name_en="5G Learning Optimization Simulation & Validation Platform",
        version=__version__,
    )


@router.get(
    "/backends",
    response_model=BackendList,
    summary="仿真后端列表 / Simulation backends",
    description="后端不可用时 available=false 并给出 reason，API 本身仍正常返回。",
)
def list_backends(service: Annotated[ExperimentService, Depends(get_service)]) -> BackendList:
    return BackendList(items=[BackendInfo.from_status(s) for s in service.list_backends()])
