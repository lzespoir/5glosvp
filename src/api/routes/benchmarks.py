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


def _benchmark_root(benchmark_id: str) -> Path:
    root = (REPO_ROOT / "reference" / "benchmarks" / benchmark_id).resolve()
    parent = (REPO_ROOT / "reference" / "benchmarks").resolve()
    if parent not in root.parents or not benchmark_id.startswith("BENCH-"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid benchmark id")
    return root


@router.get("/benchmarks/{benchmark_id}/detail")
def get_benchmark_detail(benchmark_id: str):
    root = _benchmark_root(benchmark_id)
    required = {
        "benchmark": "benchmark.json", "protocol": "protocol.json", "algorithms": "algorithms.json",
        "runs": "runs.json", "comparison": "comparison.json", "convergence": "convergence.json",
        "verification": "verification.json", "evidence": "evidence-descriptor.json", "provenance": "provenance.json",
    }
    if not (root / "benchmark.json").exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Benchmark not found")
    payload: dict[str, object] = {key: json.loads((root / filename).read_text(encoding="utf-8")) for key, filename in required.items()}
    closure = REPO_ROOT / "reference" / "benchmarks" / "closures" / f"{benchmark_id}.json"
    payload["closure"] = json.loads(closure.read_text(encoding="utf-8")) if closure.exists() else None
    return payload


@router.get("/benchmarks/{benchmark_id}/runs/{run_id}")
def get_benchmark_run(benchmark_id: str, run_id: str):
    root = _benchmark_root(benchmark_id)
    path = root / "runs.json"
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Benchmark runs not found")
    for run in json.loads(path.read_text(encoding="utf-8")):
        if run.get("benchmark_run_id") == run_id:
            return run
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Benchmark run not found")


@router.post("/benchmarks", status_code=201)
def create_benchmark(body: BenchmarkCreate):
    return service.run(body.scenario_id, body.evaluation_budget).model_dump(mode="json")
