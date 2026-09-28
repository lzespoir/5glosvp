"""
系统级实验仓库 / System experiment store.

    <root>/
    └── EXP-XXXXXXXX/
        ├── experiment.json
        └── artifacts/
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from experiments.store import atomic_write_text

from .errors import SystemArtifactNotFoundError, SystemExperimentNotFoundError
from .models import EXPERIMENT_ID_PATTERN, SystemExperimentRecord

logger = logging.getLogger(__name__)

RECORD_FILE = "experiment.json"
ARTIFACTS_DIR = "artifacts"


class FileSystemExperimentStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _dir(self, experiment_id: str) -> Path:
        if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
            raise SystemExperimentNotFoundError(f"Invalid experiment id: {experiment_id!r}")
        return self._root / experiment_id

    def exists(self, experiment_id: str) -> bool:
        return self._dir(experiment_id).exists()

    def artifact_dir(self, experiment_id: str) -> Path:
        return self._dir(experiment_id) / ARTIFACTS_DIR

    def create(self, record: SystemExperimentRecord) -> SystemExperimentRecord:
        with self._lock:
            exp_dir = self._dir(record.experiment_id)
            if exp_dir.exists():
                raise FileExistsError(f"Experiment already exists: {record.experiment_id}")
            (exp_dir / ARTIFACTS_DIR).mkdir(parents=True)
            self.update(record)
        return record

    def update(self, record: SystemExperimentRecord) -> SystemExperimentRecord:
        with self._lock:
            atomic_write_text(self._dir(record.experiment_id) / RECORD_FILE, record.model_dump_json(indent=2))
        return record

    def get(self, experiment_id: str) -> SystemExperimentRecord | None:
        try:
            path = self._dir(experiment_id) / RECORD_FILE
        except SystemExperimentNotFoundError:
            return None
        if not path.is_file():
            return None
        return SystemExperimentRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def _all(self) -> list[SystemExperimentRecord]:
        records = []
        for path in self._root.glob(f"EXP-*/{RECORD_FILE}"):
            try:
                records.append(SystemExperimentRecord.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable system experiment %s: %s", path, exc)
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def list(self, limit: int = 50, offset: int = 0) -> list[SystemExperimentRecord]:
        return self._all()[offset: offset + limit]

    def count(self) -> int:
        return len(list(self._root.glob(f"EXP-*/{RECORD_FILE}")))

    def resolve_artifact(self, experiment_id: str, name: str) -> Path:
        root = self.artifact_dir(experiment_id).resolve()
        candidate = (root / name).resolve()
        if not candidate.is_relative_to(root) or candidate == root or not candidate.is_file():
            raise SystemArtifactNotFoundError(f"Artifact not found: {name!r}")
        return candidate
