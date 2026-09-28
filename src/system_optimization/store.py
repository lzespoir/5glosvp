"""
系统级优化仓库 / System optimization store.

    <root>/
    └── OPT-XXXXXXXX/
        ├── optimization.json
        ├── context/channel.npz        冻结信道实现（Artifact Store，不提交 Git）
        └── artifacts/                 evaluation-context.json、comparison.png …
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from experiments.store import atomic_write_text

from .errors import SystemOptimizationArtifactNotFoundError, SystemOptimizationNotFoundError
from .models import SYSTEM_OPTIMIZATION_ID_PATTERN, SystemOptimizationRecord

logger = logging.getLogger(__name__)

RECORD_FILE = "optimization.json"
CONTEXT_DIR = "context"
ARTIFACTS_DIR = "artifacts"


class FileSystemOptimizationStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _dir(self, optimization_id: str) -> Path:
        if not SYSTEM_OPTIMIZATION_ID_PATTERN.fullmatch(optimization_id):
            raise SystemOptimizationNotFoundError(f"Invalid optimization id: {optimization_id!r}")
        return self._root / optimization_id

    def exists(self, optimization_id: str) -> bool:
        return self._dir(optimization_id).exists()

    def context_dir(self, optimization_id: str) -> Path:
        return self._dir(optimization_id) / CONTEXT_DIR

    def artifact_dir(self, optimization_id: str) -> Path:
        return self._dir(optimization_id) / ARTIFACTS_DIR

    def create(self, record: SystemOptimizationRecord) -> None:
        with self._lock:
            opt_dir = self._dir(record.optimization_id)
            if opt_dir.exists():
                raise FileExistsError(f"Optimization already exists: {record.optimization_id}")
            (opt_dir / CONTEXT_DIR).mkdir(parents=True)
            (opt_dir / ARTIFACTS_DIR).mkdir()
            self.update(record)

    def update(self, record: SystemOptimizationRecord) -> None:
        with self._lock:
            atomic_write_text(self._dir(record.optimization_id) / RECORD_FILE, record.model_dump_json(indent=2))

    def get(self, optimization_id: str) -> SystemOptimizationRecord | None:
        try:
            path = self._dir(optimization_id) / RECORD_FILE
        except SystemOptimizationNotFoundError:
            return None
        if not path.is_file():
            return None
        return SystemOptimizationRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def _all(self) -> list[SystemOptimizationRecord]:
        records = []
        for path in self._root.glob(f"OPT-*/{RECORD_FILE}"):
            try:
                records.append(SystemOptimizationRecord.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable system optimization %s: %s", path, exc)
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def list(self, limit: int = 50, offset: int = 0) -> list[SystemOptimizationRecord]:
        return self._all()[offset: offset + limit]

    def list_all(self) -> list[SystemOptimizationRecord]:
        return self._all()

    def count(self) -> int:
        return len(list(self._root.glob(f"OPT-*/{RECORD_FILE}")))

    def resolve_artifact(self, optimization_id: str, name: str) -> Path:
        if name == RECORD_FILE:
            path = self._dir(optimization_id) / RECORD_FILE
            if path.is_file():
                return path
        root = self.artifact_dir(optimization_id).resolve()
        candidate = (root / name).resolve()
        if not candidate.is_relative_to(root) or candidate == root or not candidate.is_file():
            raise SystemOptimizationArtifactNotFoundError(f"Artifact not found: {name!r}")
        return candidate
