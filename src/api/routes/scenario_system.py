from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from scenarios import ScenarioSystemService

from ..deps import get_scenario_service
from ..scenario_system_schemas import AcceptanceResponse, ScenarioCatalogResponse, ScenarioMaterializeRequest, ScenarioPreviewRequest, ScenarioRulesResponse, ScenarioVerifyResponse

router = APIRouter(prefix="/scenario-system", tags=["scenario-system"])
ServiceDep = Annotated[ScenarioSystemService, Depends(get_scenario_service)]


@router.get("/taxonomy")
def taxonomy(service: ServiceDep): return service.taxonomy()


@router.get("/rules", response_model=ScenarioRulesResponse)
def rules(service: ServiceDep): return ScenarioRulesResponse(items=service.rules())


@router.post("/combinations/preview")
def preview(body: ScenarioPreviewRequest, service: ServiceDep): return service.preview(body.selection, body.limit)


@router.get("/catalog", response_model=ScenarioCatalogResponse)
def catalog(service: ServiceDep, offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=200)] = 50, family: str | None = None):
    items, total = service.catalog_page(offset, limit, family)
    return ScenarioCatalogResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/catalog/{scenario_id}")
def detail(scenario_id: str, service: ServiceDep):
    try: return service.detail(scenario_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}") from exc


@router.post("/materialize")
def materialize(body: ScenarioMaterializeRequest, service: ServiceDep):
    try: return service.materialize(body.scenario_id, body.seed)
    except KeyError as exc: raise HTTPException(status_code=404, detail=f"Scenario not found: {body.scenario_id}") from exc


@router.get("/coverage")
def coverage(service: ServiceDep): return service.coverage()


@router.get("/acceptance", response_model=AcceptanceResponse)
def acceptance(service: ServiceDep): return AcceptanceResponse(items=service.acceptance())


@router.get("/verification", response_model=ScenarioVerifyResponse)
def verification(service: ServiceDep): return service.verify()
