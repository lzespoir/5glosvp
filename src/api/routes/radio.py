from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from radio import RadioObservabilityService

from ..deps import get_radio_service

router = APIRouter(prefix="/radio", tags=["day14-radio-observability"])
ServiceDep = Annotated[RadioObservabilityService, Depends(get_radio_service)]


def _not_found(exc: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": str(exc).strip("'"), "message": str(exc).strip("'")})


@router.get("/scenarios")
def scenarios(service: ServiceDep):
    return {"items": service.scenarios()}


@router.get("/scenarios/{scenario_id}/context")
def context(scenario_id: str, service: ServiceDep):
    try:
        return service.context(scenario_id).model_dump(mode="json")
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.get("/scenarios/{scenario_id}/ues/{ue_id}/observations")
def observations(scenario_id: str, ue_id: str, service: ServiceDep):
    try:
        return service.observe(scenario_id, ue_id).model_dump(mode="json")
    except KeyError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "RADIO_OBSERVATION_INVALID", "message": str(exc)}) from exc


@router.get("/scenarios/{scenario_id}/ues/{ue_id}/serving-neighbor")
def serving_neighbor(scenario_id: str, ue_id: str, service: ServiceDep):
    try:
        return service.observe(scenario_id, ue_id).serving_neighbor.model_dump(mode="json")
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.get("/scenarios/{scenario_id}/ues/{ue_id}/interference")
def interference(scenario_id: str, ue_id: str, service: ServiceDep):
    try:
        result = service.observe(scenario_id, ue_id)
        serving = next(item for item in result.cells if item.role == "SERVING")
        return (serving.interference.model_dump(mode="json") if serving.interference else {})
    except KeyError as exc:
        raise _not_found(exc) from exc
