from __future__ import annotations
import json, logging, time, uuid
from pathlib import Path
import yaml
from .backend import MultiCellBackend
from .models import *

class UserAssociationService:
    def __init__(self, configs_dir: Path, reference_dir: Path | None = None):
        self.configs_dir=Path(configs_dir); self.reference_dir=Path(reference_dir or "reference/user_association")
        self.reference_dir.mkdir(parents=True, exist_ok=True)

    def list_scenarios(self):
        out=[]
        for p in sorted(self.configs_dir.glob("multicell*.yaml")):
            out.append(self.load(p.stem))
        return out

    def load(self, scenario_id: str) -> MultiCellScenario:
        p=self.configs_dir / f"{scenario_id.lower()}.yaml"
        if not p.exists(): p=self.configs_dir / "multicell_demo.yaml"
        return MultiCellScenario.model_validate(yaml.safe_load(p.read_text()))

    def scenario_view(self, scenario_id: str):
        s=self.load(scenario_id); b=MultiCellBackend(s); c=b.candidate_cells()
        return {"scenario":s.model_dump(mode="json"), "candidate_cells":{k:[x.model_dump() for x in v] for k,v in c.items()},
                "backend":"sionna_multicell", "interference_model":INTERFERENCE_MODEL,
                "candidate_policy":CANDIDATE_POLICY}

    def run(self, scenario_id: str, budget: int = 12):
        s=self.load(scenario_id); b=MultiCellBackend(s); base=b.baseline(); base_eval=b.evaluate(base, p5_floor=None, channel_reused=False)
        floor=base_eval.p5_ue_throughput_mbps; current=base; current_eval=b.evaluate(current,p5_floor=floor,channel_reused=True)
        history=[]; seen={current_eval.association_hash}; candidates=[current_eval]
        iteration=0
        for ue in [u.ue_id for u in s.ues]:
            if len(candidates)>=budget+1: break
            from_cell=current.assignments[ue]
            for cand in b.candidate_cells()[ue]:
                if cand.cell_id==from_cell: continue
                trial=dict(current.assignments); trial[ue]=cand.cell_id; a=Association(assignments=trial)
                ev=b.evaluate(a,p5_floor=floor,channel_reused=True); iteration+=1
                dup=ev.association_hash in seen; accepted=(not dup and ev.feasible and ev.network_throughput_mbps>current_eval.network_throughput_mbps)
                history.append(AssociationMove(iteration=iteration,ue_id=ue,from_cell=from_cell,to_cell=cand.cell_id,
                    reason="candidate move generated from overloaded cell",objective_before=current_eval.network_throughput_mbps,
                    objective_after=ev.network_throughput_mbps,p5_before=current_eval.p5_ue_throughput_mbps,
                    p5_after=ev.p5_ue_throughput_mbps,feasible=ev.feasible,accepted=accepted))
                candidates.append(ev); seen.add(ev.association_hash)
                if accepted: current,current_eval=a,ev
                if iteration>=budget: break
            if iteration>=budget: break
        best=current_eval if current_eval.feasible else base_eval
        result={"optimization_id":"OPT-"+uuid.uuid4().hex[:8].upper(),"scenario":s.model_dump(mode="json"),"candidate_cells":{k:[x.model_dump() for x in v] for k,v in b.candidate_cells().items()},
          "channel":{"channel_realization_id":"CH-MULTICELL-"+b.channel.channel_hash[:8].upper(),"sha256":b.channel.channel_hash,"provider":"sionna_rt","provider_versions":b.channel.provider_versions,"reused":True},
          "baseline_policy":BASELINE_POLICY,"baseline":base_eval.model_dump(mode="json"),"best":best.model_dump(mode="json"),
          "history":[x.model_dump(mode="json") for x in candidates],"association_trace":[x.model_dump(mode="json") for x in history],
          "evaluation_budget":{"max_evaluations":budget,"evaluations_used":len(candidates)-1,"cache_hits":0},"stop_reason":"budget_exhausted" if iteration>=budget else "completed",
          "problem_type":"user_association","task_book_mapping":{"category":"user_access_parameter_optimization","evidence_level":"simulation"},
          "objective":{"id":OBJECTIVE_ID,"direction":"maximize","constraint":"P5 UE Throughput >= baseline P5"},
          "provenance":{"algorithm":"greedy_load_aware_association","algorithm_category":"engineering_baseline","learning_algorithm":False,"measured":False,"huawei_data":False,"acceptance_evidence":False,"acceptance_eligible":False,"interference_model":INTERFERENCE_MODEL}}
        self._export(result)
        return result

    def _export(self, result):
        p=self.reference_dir/result["optimization_id"]; p.mkdir(parents=True,exist_ok=True)
        for name,key in [("README.md",None),("scenario.json","scenario"),("candidate-cells.json","candidate_cells"),("evaluation-context.json","channel"),("baseline-association.json","baseline"),("optimization.json",None),("candidate-history.json","history"),("association-trace.json","association_trace")]:
            if name=="README.md": text="# Day 8 Multi-Cell User Association\n\nSimulation evidence only. Measured: NO. Huawei Data: NO. Acceptance Eligible: NO.\nInter-cell interference model: APPROXIMATE_COCHANNEL_INTERFERENCE_V0_1.\n"
            elif name=="optimization.json": text=json.dumps(result,ensure_ascii=False,indent=2)
            else: text=json.dumps(result[key],ensure_ascii=False,indent=2)
            (p/name).write_text(text,encoding="utf-8")
