"""Independent Day 9 verifier; stdlib-only and does not import production benchmark code."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tempfile
from pathlib import Path


def sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def verify(root: Path) -> tuple[bool, list[str]]:
    failures: list[str] = []
    benchmark = json.loads((root / "benchmark.json").read_text())
    protocol = json.loads((root / "protocol.json").read_text())
    algorithms = json.loads((root / "algorithms.json").read_text())
    runs = json.loads((root / "runs.json").read_text())
    comparison = json.loads((root / "comparison.json").read_text())
    convergence = json.loads((root / "convergence.json").read_text())
    descriptor = json.loads((root / "evidence-descriptor.json").read_text())
    provenance = json.loads((root / "provenance.json").read_text())
    check = lambda name, ok: failures.append(name) if not ok else None
    protocol_hash = sha(protocol)
    check("protocol_hash", benchmark["protocol_hash"] == protocol_hash)
    check("protocol_id", protocol["protocol_id"] == "ALGORITHM_BENCHMARK_V0_1")
    check("problem_scenario", protocol["problem_type"] == "USER_ASSOCIATION" and protocol["scenario_ids"] == ["MULTICELL-DEMO-001"])
    check("budget", protocol["evaluation_budget"] > 0 and all(r["evaluations_used"] <= protocol["evaluation_budget"] for r in runs))
    check("same_objective", protocol["objective"]["id"] == "NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1")
    check("same_constraint", protocol["constraints"] == [{"id": "P5_FLOOR", "operator": ">=", "value": "baseline_p5"}])
    check("same_kpis", set(protocol["kpi_versions"]) == {"network_throughput", "average_ue_throughput", "p5_ue_throughput"})
    check("three_runnable_algorithms", len(algorithms["runnable"]) == 3 and all(x["runnable"] for x in algorithms["runnable"]))
    check("research_not_runnable", all(x["implementation_status"] == "not_integrated" for x in algorithms["research"]) if algorithms["research"] else False)
    runnable_ids = {x["algorithm_id"] for x in algorithms["runnable"]}
    check("algorithm_registry_links", {r["algorithm_id"] for r in runs} == runnable_ids and {x["algorithm_id"] for x in benchmark["algorithm_configs"]} == runnable_ids)
    check("seed_recorded", all(isinstance(r["seed"], int) for r in runs))
    check("same_channel", len({r["verification"]["channel_hash"] for r in runs}) == 1 and provenance["channel_hash"] == runs[0]["verification"]["channel_hash"])
    check("same_context", len({r["verification"]["protocol_hash"] for r in runs}) == 1)
    check("optimization_links", all(r["optimization_id"].startswith("OPT-BENCH-") for r in runs))
    check("result_run_links", {x["benchmark_run_id"] for x in comparison} == {r["benchmark_run_id"] for r in runs})
    check("kpi_fields", all(all(k in r for k in ("network_throughput_mbps", "average_ue_throughput_mbps", "p5_ue_throughput_mbps", "feasible")) for r in comparison))
    by_run = {r["benchmark_run_id"]: r for r in runs}
    check("result_kpi_matches_run", all(
        isinstance(r.get("network_throughput_mbps"), (int, float)) and
        isinstance(by_run[r["benchmark_run_id"]]["best_candidate"].get("network_throughput_mbps"), (int, float)) and
        abs(r["network_throughput_mbps"] - by_run[r["benchmark_run_id"]]["best_candidate"]["network_throughput_mbps"]) < 1e-9
        for r in comparison
    ))
    check("convergence_fields", all(all(set(("evaluation_index", "elapsed_time", "current_objective", "best_feasible_objective", "current_feasible", "best_candidate_id")) <= set(row) for row in convergence.get(r["benchmark_run_id"], [])) for r in runs))
    check("runtime_split", all(set(("optimizer_overhead_time", "simulation_evaluation_time", "total_wall_time")) <= set(r["runtime"]) for r in runs))
    check("comparison_eligible", all(r["comparison_eligible"] and r["comparison_reason"] for r in comparison) and descriptor["comparison_eligible"] is True)
    check("evidence_boundary", descriptor["verified"] is True and descriptor["acceptance_eligible"] is False and descriptor["data_source"] == "simulation")
    check("no_overall_score", "overall_score" not in benchmark and "winner" not in benchmark)
    return not failures, failures


def tamper_tests(root: Path) -> list[str]:
    failures: list[str] = []
    targets = [("protocol_hash", "benchmark.json", "protocol_hash", "tampered"),
               ("channel", "runs.json", "0", "tampered"),
               ("budget", "protocol.json", "evaluation_budget", 1),
               ("objective", "protocol.json", "objective", {"id": "OTHER"}),
               ("algorithm_config", "runs.json", "0", "tampered"),
               ("result_kpi", "comparison.json", "0", "tampered"),
               ("comparison_eligibility", "comparison.json", "0", False),
               ("convergence", "convergence.json", "0", [])]
    for name, filename, key, value in targets:
        with tempfile.TemporaryDirectory() as temp:
            clone = Path(temp) / root.name
            clone.mkdir()
            for source in root.iterdir():
                if source.is_file(): (clone / source.name).write_bytes(source.read_bytes())
            data = json.loads((clone / filename).read_text())
            if filename == "runs.json":
                if name == "algorithm_config": data[0]["algorithm_id"] = value
                else: data[0]["verification"]["channel_hash"] = value
            elif filename == "comparison.json":
                if name == "result_kpi": data[0]["network_throughput_mbps"] = value
                else: data[0]["comparison_eligible"] = value
            elif filename == "convergence.json":
                first_run = next(iter(data))
                if data[first_run]: data[first_run][0].pop("best_candidate_id", None)
            else: data[key] = value
            (clone / filename).write_text(json.dumps(data), encoding="utf-8")
            ok, _ = verify(clone)
            if ok: failures.append(name)
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--tamper", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    ok, failures = verify(args.path)
    tamper_failures = tamper_tests(args.path) if args.tamper else []
    if args.write:
        benchmark_file = args.path / "benchmark.json"
        benchmark = json.loads(benchmark_file.read_text())
        for run in benchmark.get("runs", []): run.setdefault("verification", {})["independent_verified"] = ok
        for result in benchmark.get("results", []): result["verification"] = "independent verification passed" if ok else "failed"
        benchmark_file.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")
        runs_file = args.path / "runs.json"
        runs = json.loads(runs_file.read_text())
        for run in runs: run.setdefault("verification", {})["independent_verified"] = ok
        runs_file.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
        comparison_file = args.path / "comparison.json"
        comparison = json.loads(comparison_file.read_text())
        for result in comparison: result["verification"] = "independent verification passed" if ok else "failed"
        comparison_file.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.path / "verification.json").write_text(json.dumps({"status": "independently_verified" if ok else "failed", "comparable": ok, "failed_checks": failures, "tamper_tests": "PASS" if not tamper_failures else "FAIL", "tamper_failures": tamper_failures}, indent=2), encoding="utf-8")
    print(f"Comparable = {'YES' if ok else 'NO'}")
    print(f"BENCHMARK VERIFIER: {'PASS' if ok else 'FAIL'} ({len(failures)} failed checks)")
    if failures: print("failed:", ", ".join(failures))
    print(f"TAMPER TESTS: {'PASS' if not tamper_failures else 'FAIL'}")
    if tamper_failures: print("tamper failures:", ", ".join(tamper_failures))
    raise SystemExit(0 if ok and not tamper_failures else 1)
