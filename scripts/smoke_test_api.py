"""
API 冒烟测试 / API smoke test.

默认请求已启动的服务（uvicorn api.main:app --app-dir src）：
    python scripts/smoke_test_api.py [--base-url http://127.0.0.1:8000]

无需启动服务、在进程内装配生产应用：
    python scripts/smoke_test_api.py --in-process
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

LINE = "=" * 48
API = "/api/v1"


class SmokeFailure(Exception):
    pass


def _expect(cond: bool, message: str) -> None:
    if not cond:
        raise SmokeFailure(message)


def _json(resp: httpx.Response, status: int = 200) -> Any:
    _expect(resp.status_code == status, f"HTTP {resp.status_code} (expected {status}): {resp.text[:300]}")
    return resp.json()


def run_smoke(client: httpx.Client, scenario_id: str | None) -> dict[str, Any]:
    state: dict[str, Any] = {}

    def health() -> None:
        body = _json(client.get(f"{API}/health"))
        _expect(body["status"] == "ok", f"health status {body['status']}")

    def backends() -> None:
        items = _json(client.get(f"{API}/backends"))["items"]
        available = [b["id"] for b in items if b["available"]]
        _expect(bool(available), f"no available backend: {items}")
        state["backends"] = available

    def scenarios() -> None:
        items = _json(client.get(f"{API}/scenarios"))["items"]
        runnable = [s for s in items if s["backend"] in state["backends"]]
        _expect(bool(runnable), "no scenario for an available backend")
        chosen = scenario_id or runnable[0]["scenario_id"]
        _json(client.get(f"{API}/scenarios/{chosen}"))
        state["scenario_id"] = chosen

    def create() -> None:
        body = _json(
            client.post(
                f"{API}/experiments",
                json={"name": "API 冒烟测试 / API smoke test", "scenario_id": state["scenario_id"]},
            ),
            201,
        )
        _expect(body["status"] == "succeeded", f"status={body['status']} error={body.get('error')}")
        state["experiment"] = body

    def result() -> None:
        exp_id = state["experiment"]["experiment_id"]
        body = _json(client.get(f"{API}/experiments/{exp_id}"))
        _expect(body["status"] == "succeeded", "experiment not succeeded on re-read")
        _expect(body["provenance"]["measured"] is False, "provenance.measured must be false")
        listed = _json(client.get(f"{API}/experiments?limit=5"))
        _expect(any(e["experiment_id"] == exp_id for e in listed["items"]), "not in experiment list")

    def artifacts() -> None:
        exp_id = state["experiment"]["experiment_id"]
        items = _json(client.get(f"{API}/experiments/{exp_id}/artifacts"))["items"]
        names = {a["name"]: a for a in items}
        for required in ("result.json", "metadata.json", "radio_map.png"):
            _expect(required in names, f"missing artifact {required}")
        png = client.get(names["radio_map.png"]["url"])
        _expect(png.status_code == 200 and png.content[:4] == b"\x89PNG", "radio_map.png not served")
        state["artifacts"] = sorted(names)

    steps: list[tuple[str, Callable[[], None]]] = [
        ("Health", health),
        ("Backend", backends),
        ("Scenario", scenarios),
        ("Create Experiment", create),
        ("Experiment Result", result),
        ("Artifacts", artifacts),
    ]

    print(LINE)
    print("API Smoke Test / API 冒烟测试")
    print(LINE)
    print()
    for label, step in steps:
        try:
            step()
        except (SmokeFailure, httpx.HTTPError, KeyError) as e:
            print(f"{label:<26}FAIL")
            print(f"\n  reason: {type(e).__name__}: {e}")
            state["failed"] = label
            break
        print(f"{label:<26}PASS")
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--in-process", action="store_true", help="assemble the production app in-process")
    parser.add_argument("--scenario-id", default=None)
    parser.add_argument("--timeout", type=float, default=900.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    if args.in_process:
        from fastapi.testclient import TestClient  # noqa: PLC0415 - 仅 --in-process 模式需要装配完整应用（会初始化 Sionna）

        from api.main import build_app  # noqa: PLC0415 - 同上

        with TestClient(build_app()) as client:
            state = run_smoke(client, args.scenario_id)
    else:
        with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
            state = run_smoke(client, args.scenario_id)

    print()
    if "experiment" in state:
        exp = state["experiment"]
        print(f"Experiment: {exp['experiment_id']}  status={exp['status']}")
        rt = exp["runtime"]
        print(
            f"Runtime: simulation {rt['simulation_seconds']:.2f} s, "
            f"export {rt['artifact_export_seconds']:.2f} s, total {rt['total_seconds']:.2f} s"
        )
    if "artifacts" in state:
        print(f"Artifacts: {', '.join(state['artifacts'])}")
    print(LINE)
    ok = "failed" not in state
    print(f"STATUS: {'SUCCESS' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
