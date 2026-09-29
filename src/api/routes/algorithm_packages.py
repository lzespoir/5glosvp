from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from algorithm_packages import AlgorithmPackageService

router = APIRouter(tags=["algorithm-packages"])
_service = AlgorithmPackageService(Path(__file__).resolve().parents[3])


class PackagePathRequest(BaseModel):
    path: str = Field(min_length=1)


class ExperimentCreateRequest(BaseModel):
    package_id: str = Field(min_length=1)
    scenario_id: str = "MULTICELL-DEMO-001"
    parameters: dict[str, Any] = Field(default_factory=dict)
    evaluation_budget: int = Field(default=8, ge=1, le=12)
    time_limit_seconds: float | None = Field(default=None, gt=0)


class CloneRequest(BaseModel):
    package_id: str | None = None
    scenario_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    evaluation_budget: int | None = Field(default=None, ge=1, le=12)
    time_limit_seconds: float | None = Field(default=None, gt=0)


def _error(exc: Exception) -> HTTPException:
    text = str(exc)
    code, _, message = text.partition(":")
    return HTTPException(status_code=400, detail={"code": code or "ALGORITHM_PACKAGE_ERROR", "stage": "REQUEST", "message": message.strip() or text})


@router.post("/algorithm-packages/validate")
def validate_package(body: PackagePathRequest) -> dict[str, Any]:
    return _service.validate(body.path)


@router.post("/algorithm-packages/smoke-test")
def smoke_test_package(body: PackagePathRequest) -> dict[str, Any]:
    return _service.smoke_test(body.path)


@router.post("/algorithm-packages/register")
def register_package(body: PackagePathRequest) -> dict[str, Any]:
    return _service.register(body.path)


@router.get("/algorithm-packages")
def list_packages() -> dict[str, Any]:
    items = _service.list_packages()
    return {"items": items, "total": len(items)}


@router.get("/algorithm-packages/{package_id}/detail")
def package_detail(package_id: str) -> dict[str, Any]:
    try:
        return _service.get_package(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "PACKAGE_NOT_FOUND", "message": package_id}) from exc


@router.post("/algorithm-packages/{package_id}/disable")
def disable_package(package_id: str) -> dict[str, Any]:
    try:
        return _service.disable(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "PACKAGE_NOT_FOUND", "message": package_id}) from exc


@router.post("/algorithm-experiments", status_code=202)
def create_experiment(body: ExperimentCreateRequest) -> dict[str, Any]:
    try:
        return _service.create_experiment(
            body.package_id, body.scenario_id, body.parameters, body.evaluation_budget, body.time_limit_seconds,
        )
    except (KeyError, ValueError) as exc:
        raise _error(exc) from exc


@router.get("/algorithm-experiments/{run_id}")
def get_experiment(run_id: str) -> dict[str, Any]:
    try:
        return _service.get_experiment(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "EXPERIMENT_NOT_FOUND", "message": run_id}) from exc


@router.post("/algorithm-experiments/{run_id}/rerun", status_code=202)
def rerun_experiment(run_id: str) -> dict[str, Any]:
    try:
        return _service.rerun(run_id)
    except (KeyError, ValueError) as exc:
        raise _error(exc) from exc


@router.post("/algorithm-experiments/{run_id}/clone", status_code=202)
def clone_experiment(run_id: str, body: CloneRequest) -> dict[str, Any]:
    try:
        return _service.clone(run_id, body.model_dump(exclude_none=True))
    except (KeyError, ValueError) as exc:
        raise _error(exc) from exc


@router.get("/algorithm-experiments/{run_id}/export")
def export_experiment(run_id: str) -> FileResponse:
    try:
        record = _service.get_experiment(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "EXPERIMENT_NOT_FOUND", "message": run_id}) from exc
    bundle = record.get("export_bundle")
    if not bundle:
        raise HTTPException(status_code=409, detail={"code": "EXPORT_NOT_READY", "message": "experiment is not complete"})
    path = (_service.repo_root / bundle).resolve()
    if _service.repo_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "EXPORT_NOT_FOUND", "message": bundle})
    return FileResponse(path, filename=path.name, media_type="application/zip")
