from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .catalog import ScenarioCatalog
from .combination import count_combinations, iter_dimension_combinations, scenario_from_dimensions
from .models import AcceptanceMapping, ScenarioCoverage, ScenarioCoverageCell, ScenarioCounts, ScenarioInstance, ScenarioPreview, ScenarioTaxonomy, ScenarioWorkspace
from .rules import RULES
from .taxonomy import TAXONOMY
from .verifier import verify_catalog


class ScenarioSystemService:
    def __init__(self, catalog: ScenarioCatalog | None = None) -> None:
        self.catalog = catalog or ScenarioCatalog()

    def taxonomy(self) -> ScenarioTaxonomy: return TAXONOMY
    def rules(self): return RULES

    def preview(self, selection: dict[str, Any] | None = None, limit: int = 100) -> ScenarioPreview:
        combos = []
        for dimensions in iter_dimension_combinations(selection):
            scenario = scenario_from_dimensions(dimensions)
            if scenario.compatibility_status != "INVALID_COMBINATION": combos.append(scenario)
            if len(combos) >= limit: break
        raw = count_combinations(selection)
        return ScenarioPreview(counts=ScenarioCounts(**raw), combinations=combos, truncated=raw["valid_count"] > len(combos))

    def catalog_page(self, offset: int = 0, limit: int = 50, family: str | None = None) -> tuple[list, int]:
        items = list(self.catalog.definitions())
        if family: items = [item for item in items if item.scenario_family == family]
        return items[offset:offset + limit], len(items)

    def detail(self, scenario_id: str): return self.catalog.get(scenario_id)

    def materialize(self, scenario_id: str, seed: int = 0) -> ScenarioWorkspace:
        scenario = self.detail(scenario_id)
        instance_key = f"{scenario.scenario_id}:{scenario.version}:{scenario.scenario_definition_hash}:{seed}"
        instance_id = f"SCI-D12-{hashlib.sha256(instance_key.encode()).hexdigest()[:10].upper()}"
        instance = ScenarioInstance(scenario_instance_id=instance_id, scenario_id=scenario.scenario_id, scenario_version=scenario.version, scenario_definition_hash=scenario.scenario_definition_hash, seed=seed, status=scenario.compatibility_status, identity={"seed_is_instance_only": True, "dimensions": scenario.dimensions})
        return ScenarioWorkspace(workspace_status="READY" if scenario.compatibility_status == "VALID_EXECUTABLE" else "READY_WITH_DECLARED_LIMITATION", scenario=scenario, scenario_instance=instance, experiment_identity={"scenario_id": scenario.scenario_id, "scenario_version": scenario.version, "scenario_definition_hash": scenario.scenario_definition_hash, "scenario_instance_id": instance_id}, message_zh="已生成 Experiment Workspace 身份上下文；未自动运行昂贵 Sionna 仿真。")

    def coverage(self) -> ScenarioCoverage:
        definitions = list(self.catalog.definitions())
        counts = self.catalog.counts()
        matrix: list[ScenarioCoverageCell] = []
        for family in TAXONOMY.families:
            family_items = [item for item in definitions if item.scenario_family == family["value"]]
            for problem in ("NETWORK_STRUCTURE", "USER_ACCESS", "SYSTEM_RESOURCE"):
                items = [item for item in family_items if problem in item.supported_problem_types]
                matrix.append(ScenarioCoverageCell(row=family["value"], column=problem, dimensions={"scenario_family": family["value"], "optimization_problem": problem}, counts=ScenarioCounts(theoretical_count=len(items), valid_count=len(items), invalid_count=0, executable_count=sum(item.compatibility_status == "VALID_EXECUTABLE" for item in items), requires_external_asset_count=sum(item.compatibility_status == "REQUIRES_EXTERNAL_ASSET" for item in items), materialized_count=len(items), verified_count=len(items)), evidence=[]))
        family_counts = {}
        for family in TAXONOMY.families:
            items = [item for item in definitions if item.scenario_family == family["value"]]
            family_counts[family["value"]] = ScenarioCounts(theoretical_count=len(items), valid_count=len(items), invalid_count=0, executable_count=sum(item.compatibility_status == "VALID_EXECUTABLE" for item in items), requires_external_asset_count=sum(item.compatibility_status == "REQUIRES_EXTERNAL_ASSET" for item in items), materialized_count=len(items), verified_count=len(items))
        return ScenarioCoverage(counts=counts, matrix=matrix, family_counts=family_counts)

    def acceptance(self) -> list[AcceptanceMapping]:
        return [
            AcceptanceMapping(key="task-1-2", title_zh="任务书 1.2：5G 网络学习优化仿真验证平台", title_en="Task 1.2", status="部分实现", evidence=["scenario taxonomy", "catalog", "coverage API"], note_zh="已建立场景组合与覆盖管理骨架，非百余场景全部系统级验证。"),
            AcceptanceMapping(key="research-1", title_zh="研究内容 1：网络结构参数优化", title_en="Research content 1", status="部分实现", evidence=["NETWORK_STRUCTURE dimension", "coverage_structure family"], note_zh="可表达验证条件，不新增算法。"),
            AcceptanceMapping(key="research-4", title_zh="研究内容 4：网络优化应用验证平台", title_en="Research content 4", status="部分实现", evidence=["three optimization problem types", "TrafficModelAdapter contract"], note_zh="真实模型和数据仍按状态标记。"),
            AcceptanceMapping(key="innovation-4", title_zh="创新点 4：百余业务场景与模型接入", title_en="Innovation point 4", status="待接入真实模型/待实测验证", evidence=["120 semantic definitions", "A-matrix profile"], note_zh="不能宣称创新点 4 已完成验收。"),
        ]

    def verify(self) -> dict:
        return verify_catalog(list(self.catalog.definitions())) | {"counts": self.coverage().counts.model_dump(mode="json")}
