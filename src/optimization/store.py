"""
优化运行仓库 / Optimization store.

    <root>/
    └── OPT-XXXXXXXX/
        └── optimization.json

Radio Map 等产物仍归实验仓库管理，这里只保存实验 ID 引用。
"""

from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path

from experiments.store import atomic_write_text

from .errors import OptimizationNotFoundError
from .models import OPTIMIZATION_ID_PATTERN, OptimizationRecord

logger = logging.getLogger(__name__)

OPTIMIZATION_FILE = "optimization.json"


class OptimizationStore(ABC):
    @abstractmethod
    def create(self, record: OptimizationRecord) -> OptimizationRecord: ...

    @abstractmethod
    def get(self, optimization_id: str) -> OptimizationRecord | None: ...

    @abstractmethod
    def update(self, record: OptimizationRecord) -> OptimizationRecord: ...

    @abstractmethod
    def list(self, limit: int = 50, offset: int = 0) -> list[OptimizationRecord]: ...

    @abstractmethod
    def count(self) -> int: ...


class FileOptimizationStore(OptimizationStore):
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @property
    def root(self) -> Path:
        return self._root

    def _dir(self, optimization_id: str) -> Path:
        if not OPTIMIZATION_ID_PATTERN.fullmatch(optimization_id):
            raise OptimizationNotFoundError(f"Invalid optimization id: {optimization_id!r}")
        return self._root / optimization_id

    def _write(self, record: OptimizationRecord) -> None:
        atomic_write_text(self._dir(record.optimization_id) / OPTIMIZATION_FILE, record.model_dump_json(indent=2))

    def create(self, record: OptimizationRecord) -> OptimizationRecord:
        with self._lock:
            opt_dir = self._dir(record.optimization_id)
            if opt_dir.exists():
                raise FileExistsError(f"Optimization already exists: {record.optimization_id}")
            opt_dir.mkdir(parents=True)
            self._write(record)
        return record

    def get(self, optimization_id: str) -> OptimizationRecord | None:
        try:
            path = self._dir(optimization_id) / OPTIMIZATION_FILE
        except OptimizationNotFoundError:
            return None
        if not path.is_file():
            return None
        return OptimizationRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def update(self, record: OptimizationRecord) -> OptimizationRecord:
        with self._lock:
            if not (self._dir(record.optimization_id) / OPTIMIZATION_FILE).is_file():
                raise OptimizationNotFoundError(record.optimization_id)
            self._write(record)
        return record

    def _load_all(self) -> list[OptimizationRecord]:
        records = []
        for path in self._root.glob(f"OPT-*/{OPTIMIZATION_FILE}"):
            try:
                records.append(OptimizationRecord.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError) as e:
                logger.warning("Skipping unreadable optimization record %s: %s", path, e)
        return records

    def list(self, limit: int = 50, offset: int = 0) -> list[OptimizationRecord]:
        records = sorted(self._load_all(), key=lambda r: r.created_at, reverse=True)
        return records[offset: offset + limit]

    def count(self) -> int:
        return len(self._load_all())
