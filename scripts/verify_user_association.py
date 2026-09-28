"""Independent Day 8 verifier; reads persisted JSON only and imports no src modules."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def verify(path: Path) -> tuple[int,int,list[str]]:
    d=json.loads((path/"optimization.json").read_text()); checks=[]
    def c(name, ok): checks.append((name,bool(ok)))
    s=d["scenario"]; base=d["baseline"]; best=d["best"]
    c("scenario",s["scenario_id"]=="MULTICELL-DEMO-001")
    c("three_cells",len(s["cells"])>=3)
    c("multi_ue",len(s["ues"])>=12)
    c("candidate_sets",len(d["candidate_cells"])==len(s["ues"]) and all(v for v in d["candidate_cells"].values()))
    c("baseline_valid",base["feasible"] and all(x["serving_cell_id"] in {z["cell_id"] for z in d["candidate_cells"][x["ue_id"]]} for x in base["ue_metrics"]))
    c("hashes",bool(d["channel"]["sha256"]) and all(len(x["association_hash"])==64 for x in d["history"]))
    c("same_channel",d["channel"]["reused"] is True)
    c("p5_floor",best["p5_ue_throughput_mbps"]+1e-9>=base["p5_ue_throughput_mbps"])
    c("feasible_best",best["feasible"])
    c("best_selection",best["network_throughput_mbps"]>=base["network_throughput_mbps"])
    c("moves",all("ue_id" in x and "from_cell" in x and "to_cell" in x and "feasible" in x for x in d["association_trace"]))
    c("per_ue",len(best["ue_metrics"])==len(s["ues"]))
    c("per_cell",len(best["cell_metrics"])==len(s["cells"]))
    c("budget",d["evaluation_budget"]["evaluations_used"]<=d["evaluation_budget"]["max_evaluations"])
    c("objective",d["objective"]["id"]=="NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1")
    c("mapping",d["task_book_mapping"]["category"]=="user_access_parameter_optimization")
    p=d["provenance"]; c("simulation_boundary",p["measured"] is False and p["huawei_data"] is False and p["acceptance_eligible"] is False)
    return sum(ok for _,ok in checks),len(checks),[n for n,ok in checks if not ok]

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("path",type=Path); a=ap.parse_args(); p,n,bad=verify(a.path)
    for x in bad: print("FAIL",x)
    print(f"{a.path.name}: {'PASS' if p==n else 'FAIL'} ({p}/{n} checks)")
    raise SystemExit(0 if p==n else 1)
