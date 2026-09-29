from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from comparison.service import ComparisonIntent, ComparisonService

router = APIRouter(prefix="/comparisons", tags=["comparisons"])
service = ComparisonService(Path(__file__).resolve().parents[3])


class ComparisonPreviewRequest(BaseModel):
    run_ids: list[str] = Field(min_length=2)
    intent: ComparisonIntent = ComparisonIntent.ALGORITHM_COMPARISON
    declared_varying_dimensions: list[str] = Field(default_factory=list)


class ComparisonCreateRequest(ComparisonPreviewRequest):
    confirmed: bool = False


@router.get("/runs")
def comparison_runs() -> dict[str, Any]:
    items = service.list_runs()
    return {"items": items, "total": len(items)}


@router.post("/preview")
def comparison_preview(body: ComparisonPreviewRequest) -> dict[str, Any]:
    try:
        return service.preview(body.run_ids, body.intent, body.declared_varying_dimensions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "COMPARISON_INVALID", "message": str(exc)}) from exc


@router.post("", status_code=201)
def create_comparison(body: ComparisonCreateRequest) -> dict[str, Any]:
    try:
        preview = service.preview(body.run_ids, body.intent, body.declared_varying_dimensions)
        return service.create(preview, body.confirmed)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "COMPARISON_INVALID", "message": str(exc)}) from exc


@router.get("/{comparison_id}")
def get_comparison(comparison_id: str) -> dict[str, Any]:
    try:
        return service.get(comparison_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "COMPARISON_NOT_FOUND", "message": comparison_id}) from exc


@router.post("/{comparison_id}/verify")
def verify_comparison(comparison_id: str) -> dict[str, Any]:
    try:
        return service.verify(comparison_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "COMPARISON_NOT_FOUND", "message": comparison_id}) from exc
