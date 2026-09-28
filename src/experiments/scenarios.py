"""
场景目录 / Scenario catalog.

Day 2 不使用数据库，直接读取 configs/*.yaml。
"""

from __future__ import annotations

import logging
from pathlib import Path

from simulation import ScenarioConfig, ScenarioConfigError

from .errors import ScenarioNotFoundError

logger = logging.getLogger(__name__)


class ScenarioCatalog:
    def __init__(self, configs_dir: Path) -> None:
        self._configs_dir = Path(configs_dir)

    def list(self) -> list[ScenarioConfig]:
        """每次调用重新读取目录，新增配置文件无需重启服务。无效文件记录警告后跳过。"""
        scenarios: dict[str, ScenarioConfig] = {}
        for path in sorted(self._configs_dir.glob("*.yaml")):
            try:
                config = ScenarioConfig.from_yaml(path)
            except ScenarioConfigError as e:
                logger.warning("Skipping invalid scenario config %s: %s", path.name, e)
                continue
            if config.scenario_id in scenarios:
                logger.warning(
                    "Duplicate scenario_id %s in %s; keeping first", config.scenario_id, path.name
                )
                continue
            scenarios[config.scenario_id] = config
        return list(scenarios.values())

    def get(self, scenario_id: str) -> ScenarioConfig:
        for config in self.list():
            if config.scenario_id == scenario_id:
                return config
        raise ScenarioNotFoundError(f"Scenario not found: {scenario_id}")
