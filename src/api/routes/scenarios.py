from typing import Annotated

from fastapi import APIRouter, Depends

from experiments import ExperimentService

from ..deps import get_service
from ..schemas import ErrorResponse, ScenarioDetail, ScenarioList, ScenarioSummary

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=ScenarioList, summary="可运行场景列表 / Runnable scenarios")
def list_scenarios(service: Annotated[ExperimentService, Depends(get_service)]) -> ScenarioList:
    return ScenarioList(items=[ScenarioSummary.from_config(c) for c in service.list_scenarios()])


@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetail,
    responses={404: {"model": ErrorResponse}},
    summary="场景详情 / Scenario detail",
)
def get_scenario(
    scenario_id: str, service: Annotated[ExperimentService, Depends(get_service)]
) -> ScenarioDetail:
    return ScenarioDetail.from_config(service.get_scenario(scenario_id))
