"""Day15 configured workspace. Candidate catalog remains under /scenario-system."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from workspace.models import (
    AntennaDefinition, CellDefinition, CoordinateReference, EnvironmentDefinition,
    RadioModelDefinition, SiteDefinition, TrafficDefinition, UEDefinition,
)
from workspace.service import CAPABILITIES, RADIO_MODELS, ScenarioReferenced, WorkspaceService
from antenna import AMatrixDataError

router = APIRouter(prefix="/workspace", tags=["workspace"])


def get_service(request: Request) -> WorkspaceService:
    return request.app.state.workspace_service


Service = Annotated[WorkspaceService, Depends(get_service)]


def fail(exc: Exception):
    if isinstance(exc, KeyError):
        raise HTTPException(404, str(exc)) from exc
    code = str(exc)
    raise HTTPException(409 if "CONFLICT" in code or "ALREADY" in code or "ARCHIVED" in code or "REFERENCED" in code or "MUST_BE_ARCHIVED" in code or "NOT_ARCHIVED" in code else 422, code) from exc


class CreateScenario(BaseModel):
    name: str = Field(min_length=1)
    family: str = "custom"


class CandidateRequest(BaseModel):
    dimensions: dict[str, str]


class AssetRequest(BaseModel):
    name: str = Field(min_length=1)
    asset_type: str
    source_path: str
    coordinate: CoordinateReference = Field(default_factory=CoordinateReference)


class SectionRequest(BaseModel):
    expected_version: int = Field(ge=1)
    value: Any


class MaterializeRequest(BaseModel):
    seed: int


class BatchEditRequest(BaseModel):
    expected_version: int
    cell_ids: list[str]
    updates: dict[str, dict[str, Any]]


@router.get("/capabilities")
def capabilities():
    return {"items": CAPABILITIES}


@router.get("/radio/models")
def radio_models():
    return {"items": RADIO_MODELS}


@router.get("/counts")
def counts(service: Service):
    return service.counts()


@router.get("/coverage")
def coverage(service: Service):
    return service.coverage()


@router.get("/assets")
def assets(service: Service):
    return {"items": service.assets()}


@router.post("/assets", status_code=201)
def register_asset(body: AssetRequest, service: Service):
    try:
        return service.register_asset(**body.model_dump())
    except (KeyError, ValueError, OSError) as exc:
        fail(exc)


@router.get("/antennas/providers")
def antenna_providers(request: Request):
    return {"items": request.app.state.antenna_provider_registry.list()}


@router.get("/antennas/providers/{provider_type}/profiles/{profile_id}/beams/{beam_id}")
def antenna_pattern(provider_type: str, profile_id: str, beam_id: int, request: Request):
    try:
        return request.app.state.antenna_provider_registry.get(provider_type).pattern(profile_id, beam_id)
    except KeyError as exc:
        raise HTTPException(404, "ANTENNA_PROFILE_OR_BEAM_NOT_FOUND") from exc
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc)) from exc
    except AMatrixDataError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc


@router.get("/antennas/a-matrix/options")
def amatrix_options(request: Request):
    adapter = request.app.state.day13_service.adapter
    try:
        manifest = {item.source_family: item for item in adapter.manifest()}
        families = {"spread": "8_BEAM_FAMILY", "phase_power": "7_BEAM_FAMILY"}
        return {"items": [
            {"profile_id": profile["id"], "name": profile.get("alias", profile["id"]), "library": profile["library"],
             "beam_type": profile["beam_type"], "beam_ids": profile.get("beam_ids", []),
             "artifact_id": manifest[families[profile["library"]]].artifact_id,
             "artifact_hash": manifest[families[profile["library"]]].source_hash}
            for profile in adapter.profiles() if profile.get("library") in families
        ]}
    except AMatrixDataError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc


@router.get("/scenarios")
def list_scenarios(service: Service, offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 20,
                   search: str = "", family: str = "", state: str = "", problem: str = "", environment: str = "", traffic: str = "", source: str = ""):
    return service.list(offset=offset, limit=limit, search=search, family=family, state=state, problem=problem, environment=environment, traffic=traffic, source=source)


@router.post("/scenarios", status_code=201)
def create_scenario(body: CreateScenario, service: Service):
    try:
        return service.create(body.name, body.family)
    except ValueError as exc:
        fail(exc)


@router.post("/scenarios/from-candidate", status_code=201, deprecated=True, description="Compatibility endpoint. Prefer explicit candidate preview followed by /scenario-candidates/{candidate_id}/promote.")
def from_candidate(body: CandidateRequest, service: Service):
    try:
        return service.from_candidate(body.dimensions)
    except ValueError as exc:
        fail(exc)


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, service: Service):
    try:
        return service.get(scenario_id)
    except KeyError as exc:
        fail(exc)


@router.get("/scenarios/{scenario_id}/validation")
def validate_scenario(scenario_id: str, service: Service):
    try:
        return service.validate(service.get(scenario_id))
    except KeyError as exc:
        fail(exc)


@router.get("/scenarios/{scenario_id}/provenance")
def provenance(scenario_id: str, service: Service):
    try:
        return service.provenance(scenario_id)
    except KeyError as exc:
        fail(exc)


@router.patch("/scenarios/{scenario_id}/{section}")
def patch_section(scenario_id: str, section: str, body: SectionRequest, service: Service):
    parsers = {
        "environment": lambda v: EnvironmentDefinition.model_validate(v) if v is not None else None,
        "sites": lambda v: [SiteDefinition.model_validate(x) for x in v],
        "cells": lambda v: [CellDefinition.model_validate(x) for x in v],
        "antennas": lambda v: [AntennaDefinition.model_validate(x) for x in v],
        "ues": lambda v: [UEDefinition.model_validate(x) for x in v],
        "traffic": TrafficDefinition.model_validate,
        "radio": RadioModelDefinition.model_validate,
        "network_functions": lambda v: [str(x) for x in v],
        "optimization_problems": lambda v: [str(x) for x in v],
        "basic": lambda v: v,
    }
    if section not in parsers:
        raise HTTPException(404, "SECTION_NOT_FOUND")
    try:
        scenario = service.get(scenario_id)
        if body.expected_version != scenario.version:
            raise ValueError("SCENARIO_VERSION_CONFLICT")
        value = parsers[section](body.value)
        if section == "basic":
            scenario.name = str(value["name"]).strip()
            scenario.family = str(value.get("family", scenario.family))
            if not scenario.name:
                raise ValueError("SCENARIO_NAME_REQUIRED")
        else:
            setattr(scenario, section, value)
        return service.save(scenario)
    except (KeyError, ValueError, TypeError) as exc:
        fail(exc)


@router.post("/scenarios/{scenario_id}/clone", status_code=201)
def clone(scenario_id: str, service: Service):
    try:
        return service.clone(scenario_id)
    except KeyError as exc:
        fail(exc)


@router.post("/scenarios/{scenario_id}/archive")
def archive(scenario_id: str, service: Service):
    try:
        return service.archive(scenario_id)
    except KeyError as exc:
        fail(exc)


@router.post("/scenarios/{scenario_id}/restore")
def restore(scenario_id: str, service: Service):
    try:
        return service.restore(scenario_id)
    except (KeyError, ValueError) as exc:
        fail(exc)


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str, service: Service):
    try:
        return service.delete_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(404, {"code": "SCENARIO_NOT_FOUND", "scenario_id": scenario_id}) from exc
    except ScenarioReferenced as exc:
        raise HTTPException(409, {"code": "SCENARIO_REFERENCED", "scenario_id": scenario_id, "reference_summary": exc.reference_summary}) from exc
    except ValueError as exc:
        fail(exc)


@router.post("/scenarios/{scenario_id}/instances", status_code=201)
def materialize(scenario_id: str, body: MaterializeRequest, service: Service):
    try:
        return service.materialize(scenario_id, body.seed)
    except (KeyError, ValueError) as exc:
        fail(exc)


@router.get("/instances/{instance_id}")
def get_instance(instance_id: str, service: Service):
    try:
        return service.get_instance(instance_id)
    except KeyError as exc:
        fail(exc)


@router.post("/scenarios/{scenario_id}/cells/batch-edit")
def batch_edit(scenario_id: str, body: BatchEditRequest, service: Service):
    from workspace.models import Parameter
    try:
        return service.batch_edit_cells(scenario_id, body.cell_ids, {key: Parameter.model_validate(value) for key, value in body.updates.items()}, body.expected_version)
    except (KeyError, ValueError) as exc:
        fail(exc)
