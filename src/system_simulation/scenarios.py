"""
系统级场景目录 / System scenario catalog: configs/system/*.yaml
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from .errors import SystemScenarioNotFoundError
from .models import SystemScenario

logger = logging.getLogger(__name__)


class SystemScenarioCatalog:
    def __init__(self, configs_dir: Path) -> None:
        self._dir = Path(configs_dir)

    def list(self) -> list[SystemScenario]:
        scenarios: list[SystemScenario] = []
        if not self._dir.is_dir():
            return scenarios
        for path in sorted(self._dir.glob("*.yaml")):
            try:
                scenarios.append(SystemScenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))))
            except (OSError, yaml.YAMLError, ValidationError) as exc:
                logger.warning("Skipping invalid system scenario %s: %s", path.name, exc)
        return scenarios

    def get(self, scenario_id: str) -> SystemScenario:
        for s in self.list():
            if s.scenario_id == scenario_id:
                return s
        raise SystemScenarioNotFoundError(f"System scenario not found: {scenario_id}")
