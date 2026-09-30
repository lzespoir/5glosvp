from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from antenna import AMatrixDataError
from ue_twin import UETwinService

from ..day13_schemas import ScenarioAMatrixIdentityRequest, UETwinQueryRequest
from ..deps import get_day13_service

router = APIRouter(tags=["day13-a-matrix-ue-twin"])
ServiceDep = Annotated[UETwinService, Depends(get_day13_service)]


def _data_error(exc: AMatrixDataError) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc), "detail": exc.detail})


@router.get("/a-matrix/libraries")
def libraries(service: ServiceDep):
    try:
        return {"items": [item.model_dump(mode="json") for item in service.adapter.libraries()]}
    except AMatrixDataError as exc:
        raise _data_error(exc) from exc


@router.get("/a-matrix/profiles")
def profiles(service: ServiceDep):
    return {"items": service.adapter.profiles()}


@router.get("/a-matrix/manifest")
def manifest(service: ServiceDep):
    try:
        return {"items": [item.model_dump(mode="json") for item in service.adapter.manifest()]}
    except AMatrixDataError as exc:
        raise _data_error(exc) from exc


@router.get("/a-matrix/source-status")
def source_status(service: ServiceDep):
    return service.adapter.source_status().model_dump(mode="json")


@router.get("/a-matrix/pattern")
def pattern(
    service: ServiceDep,
    library: Annotated[str, Query(min_length=1)] = "spread",
    beam_type: Annotated[str, Query(min_length=1)] = "SSB",
    entry_key: Annotated[str, Query(min_length=1)] = "",
):
    try:
        return service.adapter.pattern(library, beam_type, entry_key).model_dump(mode="json")
    except AMatrixDataError as exc:
        raise _data_error(exc) from exc


@router.post("/ue-twin/query")
def ue_twin_query(body: UETwinQueryRequest, service: ServiceDep):
    try:
        return service.query(
            ue_id=body.ue_id,
            aau_id=body.aau_id,
            aau_position=body.aau_position,
            ue_position=body.ue_position,
            profile_id=body.profile_id,
            serving_cell_id=body.serving_cell_id,
            neighbor_cell_ids=body.neighbor_cell_ids,
            traffic_profile=body.traffic_profile,
        )
    except AMatrixDataError as exc:
        raise _data_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "UE_TWIN_QUERY_INVALID", "message": str(exc)}) from exc


@router.post("/scenario-system/amatrix-identity")
def scenario_amatrix_identity(body: ScenarioAMatrixIdentityRequest, service: ServiceDep):
    try:
        return service.scenario_identity(body.scenario, body.profile_id)
    except (AMatrixDataError, ValueError) as exc:
        if isinstance(exc, AMatrixDataError):
            raise _data_error(exc) from exc
        raise HTTPException(status_code=422, detail={"code": "SCENARIO_AMATRIX_IDENTITY_INVALID", "message": str(exc)}) from exc
