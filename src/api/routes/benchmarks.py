from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from api.settings import REPO_ROOT
from algorithm_benchmark.service import BenchmarkService


router = APIRouter(tags=["benchmarks"])
service = BenchmarkService(REPO_ROOT / "configs", REPO_ROOT / "reference" / "benchmarks")


class BenchmarkCreate(BaseModel):
    scenario_id: str = "MULTICELL-DEMO-001"
    evaluation_budget: int = Field(default=8, ge=1, le=12)


@router.get("/benchmarks/algorithms")
def benchmark_algorithms():
    return {"runnable": [x.model_dump(mode="json") for x in service.catalog()], "research": service.research_catalog()}


@router.get("/benchmarks/protocols")
def benchmark_protocols():
    return {"items": [service.protocol().model_dump(mode="json")]}


@router.get("/benchmarks")
def list_benchmarks(limit: Annotated[int, Query(ge=1, le=50)] = 20):
    root = REPO_ROOT / "reference" / "benchmarks"
    items = []
    for path in sorted(root.glob("BENCH-*"), reverse=True)[:limit]:
        source = path / "benchmark.json"
        if source.exists(): items.append(json.loads(source.read_text(encoding="utf-8")))
    return {"items": items, "total": len(items)}


@router.get("/benchmarks/{benchmark_id}")
def get_benchmark(benchmark_id: str):
    path = REPO_ROOT / "reference" / "benchmarks" / benchmark_id / "benchmark.json"
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/benchmarks", status_code=201)
def create_benchmark(body: BenchmarkCreate):
    return service.run(body.scenario_id, body.evaluation_budget).model_dump(mode="json")
