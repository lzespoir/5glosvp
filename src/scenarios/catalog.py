from __future__ import annotations

from functools import lru_cache

from .combination import count_combinations, iter_dimension_combinations, scenario_from_dimensions
from .models import ScenarioDefinition, ScenarioCounts


class ScenarioCatalog:
    def __init__(self, materialized_limit: int = 120) -> None:
        self.materialized_limit = materialized_limit

    @lru_cache(maxsize=1)
    def definitions(self) -> tuple[ScenarioDefinition, ...]:
        result: list[ScenarioDefinition] = []
        for dimensions in iter_dimension_combinations():
            scenario = scenario_from_dimensions(dimensions)
            if scenario.compatibility_status == "INVALID_COMBINATION":
                continue
            result.append(scenario)
            if len(result) >= self.materialized_limit:
                break
        return tuple(result)

    def counts(self) -> ScenarioCounts:
        raw = count_combinations()
        return ScenarioCounts(
            **raw,
            materialized_count=len(self.definitions()),
            definition_verified_count=len(self.definitions()),
            experiment_verified_count=0,
            verified_count=0,
            acceptance_evidence_count=0,
        )

    def get(self, scenario_id: str) -> ScenarioDefinition:
        for scenario in self.definitions():
            if scenario.scenario_id == scenario_id:
                return scenario
        raise KeyError(scenario_id)
