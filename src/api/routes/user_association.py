from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from api.settings import REPO_ROOT
from user_association import UserAssociationService

router = APIRouter(tags=["user-association"])
service = UserAssociationService(REPO_ROOT / "configs", REPO_ROOT / "reference" / "user_association")

class UserAssociationCreate(BaseModel):
    scenario_id: str = "MULTICELL-DEMO-001"
    evaluation_budget: int = Field(default=8, ge=1, le=12)

@router.get("/multicell/scenarios")
def list_multicell_scenarios():
    return {"items": [s.model_dump(mode="json") for s in service.list_scenarios()]}

@router.get("/multicell/scenarios/{scenario_id}")
def get_multicell_scenario(scenario_id: str):
    return service.scenario_view(scenario_id)

@router.post("/user-association-optimizations", status_code=201)
def run_user_association(body: UserAssociationCreate):
    return service.run(body.scenario_id, body.evaluation_budget)
