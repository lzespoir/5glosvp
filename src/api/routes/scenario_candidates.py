"""Stateless candidate preview and explicit promotion into the workspace library."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from scenarios.candidates import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, ScenarioCandidateService
from workspace.service import WorkspaceService

router = APIRouter(prefix="/scenario-candidates", tags=["scenario-candidates"])
candidate_service = ScenarioCandidateService()


class CandidatePreviewRequest(BaseModel):
    selection: dict[str, list[str]]
    filters: dict[str, str | list[str]] = Field(default_factory=dict)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    query_hash: str | None = None


class CandidatePromotionRequest(BaseModel):
    dimensions: dict[str, str]


def get_workspace(request: Request) -> WorkspaceService:
    return request.app.state.workspace_service


WorkspaceDep = Annotated[WorkspaceService, Depends(get_workspace)]


@router.post("/preview")
def preview(body: CandidatePreviewRequest):
    try:
        return candidate_service.preview(body.selection, body.limit, body.offset, body.filters, body.query_hash)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(422, code) from exc


@router.post("/{candidate_id}/promote", status_code=201)
def promote(candidate_id: str, body: CandidatePromotionRequest, service: WorkspaceDep):
    try:
        return service.promote_candidate(candidate_id, body.dimensions)
    except ValueError as exc:
        code = str(exc)
        status = 409 if "ALREADY" in code or "STALE" in code else 422
        raise HTTPException(status, code) from exc
