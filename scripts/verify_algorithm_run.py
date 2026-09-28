"""
算法运行独立复核 / Independent verification of an algorithm-driven system optimization (Day 7).

    python scripts/verify_algorithm_run.py OPT-XXXXXXXX \
        [--data-dir data/system_optimizations] [--experiments-dir data/system_experiments] [--out verification.json]

先运行 verify_system_optimization.py 的全部检查（冻结上下文、候选 → 实验、KPI / 目标复算、最优选择、公平性），
再只依据持久化产物独立复核算法层：
    身份        : algorithm id / version / SDK 版本在 record、provenance、trace、algorithm-metadata.json 之间一致
    参数空间    : sha256(canonical JSON(parameter_space)) 复算；每个候选值位于参数空间内
    超参数      : 按 algorithm-metadata.json 声明的 schema 独立检查；config hash 复算
    预算        : evaluations_used = 候选数 ≤ max_evaluations；simulations_run + cache_hits = evaluations_used
    Trace       : 评价顺序 / 参数 / 目标 / 轮次与候选一致；best-so-far 按平台规则独立重算
    缓存        : cache key 独立复算；命中项指向更早的同参数评价且复用同一实验
    Stop Reason : 与预算和 trace 一致
    决策重放    : grid_search → 一次性建议全部候选值；research_demo_optimizer → 用独立实现的
                  自适应局部搜索规则，以记录的目标值逐轮重放，建议序列、停止原因与推荐值必须一致
不 import src/ 下任何模块（algorithms、system_optimization、evaluation 等）。
canonical JSON = json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_system_optimization import in_space, verify as verify_optimization  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SDK_VERSION = "0.1"
DEMO_ROUND_DIGITS = 6
TERMINAL_STOPS = {"completed", "max_iterations", "converged", "no_improvement", "budget_exhausted"}


def canonical_sha256(data: Any) -> str:
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_key(ctx: dict, parameters: dict, backend_id: str, backend_version: str | None) -> str:
    material = {
        "context": {
            "ue_population_sha256": ctx["ue_population"]["sha256"],
            "channel_sha256": ctx["channel_realization"]["sha256"],
            "traffic_sha256": ctx["traffic_realization"]["sha256"],
            "simulation_horizon": ctx["simulation_horizon"],
            "benchmark_protocol": [ctx["benchmark_protocol_id"], ctx["benchmark_protocol_version"]],
            "scheduler_config": ctx["scheduler_config"],
            "link_adaptation_config": ctx["link_adaptation_config"],
            "power_control_config": ctx["power_control_config"],
            "scenario_version": ctx["scenario_version"],
        },
        "parameters": {k: parameters[k] for k in sorted(parameters)},
        "backend": {"id": backend_id, "version": backend_version},
    }
    return canonical_sha256(material)


def hyperparameter_ok(definition: dict, value: Any) -> bool:
    t = definition["type"]
    if t == "boolean":
        return isinstance(value, bool)
    if t == "categorical":
        return value in (definition.get("choices") or [])
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    if t == "integer" and not float(value).is_integer():
        return False
    b = definition.get("bounds")
    if b is None:
        return True
    above = value >= b["lower"] if b.get("lower_inclusive", True) else value > b["lower"]
    below = value <= b["upper"] if b.get("upper_inclusive", True) else value < b["upper"]
    return above and below


def replay_research_demo(space_param: dict, hp: dict, baseline: dict, rounds: list[dict],
                         objective_of: dict[str, float | None], maximize: bool, max_evaluations: int) -> dict:
    """独立实现的自适应局部搜索（与算法 README 描述的规则一致），按记录的目标值逐轮重放。"""
    pid = space_param["id"]
    b = space_param["bounds"]
    min_step, shrink = float(hp["min_step"]), float(hp["shrink_factor"])
    lo = b["lower"] if b.get("lower_inclusive", True) else b["lower"] + min_step
    hi = b["upper"] if b.get("upper_inclusive", True) else b["upper"] - min_step

    def clip(v: float) -> float:
        return round(min(max(v, lo), hi), DEMO_ROUND_DIGITS)

    def score(obj: float | None) -> float:
        return -math.inf if obj is None else (obj if maximize else -obj)

    memory: dict[float, float] = {}
    if baseline:
        memory[round(float(baseline["parameters"][pid]), DEMO_ROUND_DIGITS)] = score(
            objective_of.get(baseline["candidate_id"]))
    x = clip((lo + hi) / 2) if hp["start_point"] == "center" else clip(float(baseline["parameters"][pid]))
    step, direction = float(hp["initial_step"]), 0
    mode = "explore" if x in memory else "start"
    stop: str | None = None

    def decide(pending: list[float]) -> None:
        nonlocal x, step, direction, mode, stop
        if mode == "start":
            mode = "explore"
            return
        fx = memory.get(x, -math.inf)
        scored = [(memory[p], -i, p) for i, p in enumerate(pending) if p in memory]
        best = max(scored) if scored else None
        if best is not None and best[0] > fx:
            direction = 1 if best[2] > x else -1
            x, mode = best[2], "extend"
            return
        step, mode = step * shrink, "explore"
        if step < min_step:
            stop = "converged"

    def next_points() -> list[float]:
        while stop is None:
            if mode == "start":
                return [x]
            if mode == "explore":
                raw = [clip(x - step), clip(x + step)]
                points = [p for i, p in enumerate(raw) if p != x and p not in raw[:i]]
            else:
                target = clip(x + direction * step)
                points = [] if target == x else [target]
            unknown = [p for p in points if p not in memory]
            if unknown:
                return unknown
            decide(points)
        return []

    mismatches: list[str] = []
    used, n_round, reason = 0, 0, None
    while True:
        if stop is not None:
            reason = stop
            break
        remaining = max_evaluations - used
        if remaining <= 0:
            reason = "budget_exhausted"
            break
        expected = next_points()
        if not expected:
            reason = stop or "completed"
            break
        if n_round >= len(rounds):
            mismatches.append(f"replay expects round {n_round + 1} suggesting {expected}, trace has none")
            break
        rec = rounds[n_round]
        n_round += 1
        got = [s[pid] for s in rec["suggestions"]]
        if got != expected:
            mismatches.append(f"round {rec['round']}: replay suggests {expected}, trace {got}")
            break
        accepted = expected[:remaining]
        for p, cid in zip(accepted, rec["evaluated_candidate_ids"]):
            memory[p] = score(objective_of.get(cid))
            used += 1
        if all(p in memory for p in expected):
            decide(expected)
        if stop is None and n_round >= int(hp["max_iterations"]):
            stop = "max_iterations"
        if len(expected) > remaining:
            reason = "budget_exhausted"
            break
    if not mismatches and n_round != len(rounds):
        mismatches.append(f"replay ends after {n_round} rounds, trace has {len(rounds)}")
    return {"stop_reason": reason, "recommendation": {pid: x}, "rounds": n_round, "mismatches": mismatches}


def verify(opt_dir: Path, experiments_dir: Path) -> dict:
    base = verify_optimization(opt_dir, experiments_dir)
    record = json.loads((opt_dir / "optimization.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": f"algorithm.{name}", "status": "PASS" if ok else "FAIL", "detail": detail})

    info = record.get("algorithm")
    trace = record.get("algorithm_trace")
    space = record.get("parameter_space")
    budget = record.get("evaluation_budget")
    check("algorithm_record_present", info is not None and trace is not None and space is not None
          and budget is not None, "algorithm / trace / parameter_space / evaluation_budget")
    if info is None or trace is None or space is None or budget is None:
        return _report(record, base, checks, {})

    art = opt_dir / "artifacts"
    meta = json.loads((art / "algorithm-metadata.json").read_text(encoding="utf-8"))
    config = json.loads((art / "algorithm-config.json").read_text(encoding="utf-8"))
    exported_space = json.loads((art / "parameter-space.json").read_text(encoding="utf-8"))
    exported_trace = json.loads((art / "algorithm-trace.json").read_text(encoding="utf-8"))
    prov = record["provenance"]
    aid, version = info["algorithm_id"], info["algorithm_version"]
    baseline = record["baseline"]
    candidates = record["candidates"]
    cids = [c["candidate_id"] for c in candidates]
    by_id = {c["candidate_id"]: c for c in [baseline, *candidates] if c}
    maximize = record["objective"]["direction"] == "maximize"

    # 身份 / 分类 / 非学习、非科研成果、非验收
    check("algorithm_id", aid == record["optimizer_id"] == prov.get("algorithm") == trace["algorithm_id"]
          == meta["algorithm_id"] == config["algorithm_id"], aid)
    check("algorithm_version", version == record["optimizer_version"] == prov.get("algorithm_version")
          == trace["algorithm_version"] == meta["version"] == config["algorithm_version"], version)
    check("sdk_version", info["sdk_version"] == trace["sdk_version"] == prov.get("sdk_version")
          == config["sdk_version"] == EXPECTED_SDK_VERSION, info["sdk_version"])
    check("category", info["algorithm_category"] == meta["category"] == prov.get("algorithm_category"),
          info["algorithm_category"])
    check("not_learning_not_deliverable_not_acceptance",
          info["learning_algorithm"] is False and meta["learning_algorithm"] is False
          and info["project_research_deliverable"] is False and meta["project_research_deliverable"] is False
          and meta.get("acceptance_algorithm") is False and prov.get("acceptance_evidence") is False,
          f"learning={info['learning_algorithm']} deliverable={info['project_research_deliverable']}")
    check("source_revision", info["source_revision"].get("type") == "git_commit"
          and info["source_revision"].get("value") == prov.get("git_commit") and bool(info["source"]),
          f"{info['source']} @ {str(info['source_revision'].get('value'))[:12]}")

    # 参数空间
    space_hash = canonical_sha256(space)
    check("parameter_space_hash", space_hash == info["parameter_space_hash"] == prov.get("parameter_space_hash")
          == config["parameter_space_hash"] and exported_space == space,
          f"recomputed {space_hash[:16]}… vs record {info['parameter_space_hash'][:16]}…")
    params = space["parameters"]
    check("parameter_space_supported", all(p["role"] == "optimization_variable" for p in params)
          and all(p["type"] in meta["supported_parameter_types"] for p in params)
          and len(params) <= meta["capabilities"]["max_parameters"],
          f"{[(p['id'], p['type']) for p in params]} vs supported {meta['supported_parameter_types']}")
    ids = [p["id"] for p in params]
    check("candidates_in_parameter_space",
          all(sorted(c["parameters"]) == sorted(ids) and all(in_space(p, c["parameters"][p["id"]]) for p in params)
              for c in candidates),
          f"{len(candidates)} candidates within {[(p['id'], p.get('bounds'), p.get('choices')) for p in params]}")

    # 超参数
    hp = info["hyperparameters"]
    schema = {h["id"]: h for h in meta["hyperparameter_schema"]}
    check("hyperparameters_match_schema", sorted(hp) == sorted(schema)
          and all(hyperparameter_ok(schema[k], v) for k, v in hp.items()),
          ", ".join(f"{k}={v}" for k, v in hp.items()) or "(none)")
    check("hyperparameters_consistent", hp == record["algorithm_hyperparameters"] == trace["hyperparameters"]
          == config["hyperparameters"], "record / trace / config")
    defaults = {k: h["default"] for k, h in schema.items()}
    check("auto_configured_flag", info["auto_configured"] == (hp == defaults),
          f"auto_configured={info['auto_configured']} (defaults {'' if hp == defaults else 'not '}used)")
    config_hash = canonical_sha256({"algorithm_id": aid, "algorithm_version": version,
                                    "sdk_version": info["sdk_version"], "hyperparameters": hp,
                                    "max_evaluations": budget["max_evaluations"]})
    check("algorithm_config_hash", config_hash == info["algorithm_config_hash"] == prov.get("algorithm_config_hash")
          == config["algorithm_config_hash"], f"recomputed {config_hash[:16]}…")

    # 预算
    hits = [c for c in candidates if c.get("cache_hit")]
    n = len(candidates)
    check("budget_used", budget["evaluations_used"] == n == trace["evaluations_used"] <= budget["max_evaluations"]
          == trace["max_evaluations"] == config["evaluation_budget"]["max_evaluations"],
          f"used {n}/{budget['max_evaluations']}")
    check("budget_simulations_and_cache", budget["cache_hits"] == len(hits)
          and budget["simulations_run"] == n - len(hits) and budget["simulations_run"] + budget["cache_hits"] == n,
          f"simulations {budget['simulations_run']} + cache hits {budget['cache_hits']} = {n}")
    rejected_total = sum(len(r["rejected_suggestions"]) for r in trace["rounds"])
    check("budget_rejected_suggestions", rejected_total == trace["rejected_suggestions"]
          == budget["rejected_suggestions"], f"{rejected_total} rejected")

    # Trace
    evals = trace["evaluations"]
    head = evals[:1] if baseline else []
    tail = evals[len(head):]
    check("trace_incumbent", not baseline or (head and head[0]["candidate_id"] == baseline["candidate_id"]
                                              and head[0]["sequence"] == 0 and head[0]["round"] == 0),
          baseline["candidate_id"] if baseline else "no baseline")
    check("trace_evaluations_match_candidates",
          [e["candidate_id"] for e in tail] == cids and [e["sequence"] for e in tail] == list(range(1, n + 1))
          and all(e["parameters"] == c["parameters"] and e["cache_hit"] == bool(c.get("cache_hit"))
                  and e["round"] == c.get("algorithm_round")
                  and (e["objective"] == (c["objective"] or {}).get("value")) for e, c in zip(tail, candidates)),
          f"{len(tail)} trace evaluations vs {n} candidates")
    round_ids = [cid for r in trace["rounds"] for cid in r["evaluated_candidate_ids"]]
    check("trace_rounds", round_ids == cids and [r["round"] for r in trace["rounds"]]
          == list(range(1, len(trace["rounds"]) + 1))
          and all([s for s in r["suggestions"][:len(r["evaluated_candidate_ids"])]]
                  == [by_id[cid]["parameters"] for cid in r["evaluated_candidate_ids"]]
                  and r["rejected_suggestions"] == r["suggestions"][len(r["evaluated_candidate_ids"]):]
                  for r in trace["rounds"]),
          f"{len(trace['rounds'])} rounds")
    check("trace_artifact_matches_record", exported_trace == trace, "algorithm-trace.json")

    base_params = record["baseline_parameters"]

    def objective(cid: str) -> float | None:
        o = by_id[cid].get("objective")
        return None if o is None else o["value"]

    def key(cid: str) -> tuple[float, float, float]:
        o = objective(cid)
        s = -math.inf if o is None else (o if maximize else -o)
        return (s, 1.0 if by_id[cid]["parameters"] == base_params else 0.0, -float(by_id[cid]["iteration"]))

    best: str | None = None
    best_ok = True
    for e in evals:
        if objective(e["candidate_id"]) is not None and (best is None or key(e["candidate_id"]) > key(best)):
            best = e["candidate_id"]
        best_ok = best_ok and e["best_so_far_candidate_id"] == best
    check("trace_best_so_far", best_ok and best == record["best_candidate_id"],
          f"independent best-so-far ends at {best}; record best {record['best_candidate_id']}")

    # 缓存 / 去重
    backend_version = record["evaluation_context"]["backend_version"]
    ctx = record["evaluation_context"]
    keys_ok, hit_ok = True, True
    order = [baseline["candidate_id"]] + cids if baseline else cids
    for c in ([baseline] if baseline else []) + candidates:
        if c.get("evaluation_cache_key") is not None:
            keys_ok = keys_ok and c["evaluation_cache_key"] == cache_key(ctx, c["parameters"], ctx["backend_id"],
                                                                         backend_version)
        if c.get("cache_hit"):
            src = by_id.get(c.get("reused_candidate_id") or "")
            hit_ok = hit_ok and src is not None and not src.get("cache_hit") \
                and order.index(src["candidate_id"]) < order.index(c["candidate_id"]) \
                and src["parameters"] == c["parameters"] and src["experiment_ids"] == c["experiment_ids"] \
                and c.get("evaluation_cache_key") == src.get("evaluation_cache_key")
    simulated = [json.dumps(c["parameters"], sort_keys=True)
                 for c in ([baseline] if baseline else []) + candidates if not c.get("cache_hit")]
    check("cache_keys_recomputed", keys_ok, "sha256(context + parameters + backend)")
    check("cache_hits_reuse_earlier_evaluation", hit_ok,
          ", ".join(f"{c['candidate_id']}→{c.get('reused_candidate_id')}" for c in hits) or "no cache hits")
    check("no_duplicate_simulation", len(simulated) == len(set(simulated)), f"{len(simulated)} simulated points")

    # Stop reason
    stop = record.get("stop_reason")
    stop_ok = stop == trace["stop_reason"] == config["stop_reason"] and stop in TERMINAL_STOPS
    if stop == "budget_exhausted":
        stop_ok = stop_ok and (n == budget["max_evaluations"] or rejected_total > 0)
    else:
        stop_ok = stop_ok and rejected_total == 0
    check("stop_reason", stop_ok, f"{stop} ({trace.get('stop_detail')})")
    rec = trace.get("recommendation") or {}
    best_params = by_id[record["best_candidate_id"]]["parameters"] if record.get("best_candidate_id") else None
    matches = rec.get("parameters") == best_params if rec.get("parameters") is not None else None
    check("recommendation_matches_best_flag", matches == record.get("recommendation_matches_best"),
          f"recommendation {rec.get('parameters')} vs best {best_params}")

    # 决策重放
    replay: dict[str, Any] = {}
    if aid == "grid_search":
        choices = params[0].get("choices") or []
        first = [s[params[0]["id"]] for s in trace["rounds"][0]["suggestions"]] if trace["rounds"] else []
        check("replay_grid_search", len(trace["rounds"]) == 1 and first == choices
              and stop in {"completed", "budget_exhausted"}, f"suggestions {first} vs choices {choices}")
    elif aid == "research_demo_optimizer":
        objectives = {cid: objective(cid) for cid in by_id}
        replay = replay_research_demo(params[0], hp, baseline, trace["rounds"], objectives, maximize,
                                      budget["max_evaluations"])
        check("replay_suggestions", not replay["mismatches"],
              "; ".join(replay["mismatches"]) or f"{replay['rounds']} rounds reproduced")
        check("replay_stop_reason", replay["stop_reason"] == stop, f"replay {replay['stop_reason']} vs record {stop}")
        check("replay_recommendation", replay["recommendation"] == rec.get("parameters"),
              f"replay {replay['recommendation']} vs trace {rec.get('parameters')}")
    else:
        check("replay_not_available", True, f"no independent replay for '{aid}'; generic checks only")

    return _report(record, base, checks, replay)


def _report(record: dict, base: dict, checks: list[dict], replay: dict) -> dict:
    all_checks = base["checks"] + checks
    passed = all(c["status"] == "PASS" for c in all_checks)
    return {
        **base,
        "verifier": "scripts/verify_algorithm_run.py + scripts/verify_system_optimization.py (independent; "
                    "imports nothing from src/)",
        "overall": "PASS" if passed else "FAIL",
        "algorithm": {
            "algorithm_id": (record.get("algorithm") or {}).get("algorithm_id"),
            "algorithm_version": (record.get("algorithm") or {}).get("algorithm_version"),
            "stop_reason": record.get("stop_reason"),
            "replay": replay,
        },
        "verification_is_not_acceptance": True,
        "checks": all_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("optimization_id")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "system_optimizations")
    parser.add_argument("--experiments-dir", type=Path, default=ROOT / "data" / "system_experiments")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = verify(args.data_dir / args.optimization_id, args.experiments_dir)
    for c in report["checks"]:
        if c["status"] != "PASS":
            print(f"FAIL {c['check']}: {c['detail']}")
    n_pass = sum(c["status"] == "PASS" for c in report["checks"])
    print(f"{report['optimization_id']}: {report['overall']} ({n_pass}/{len(report['checks'])} checks)")
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
