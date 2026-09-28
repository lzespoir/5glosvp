"""
实验仓库 / Experiment store.

FileExperimentStore 是唯一知道实验文件布局的模块：

    <root>/
    └── EXP-XXXXXXXX/
        ├── experiment.json
        ├── config.yaml
        └── artifacts/
            ├── result.json
            ├── metadata.json
            ├── radio_map.png
            ├── radio_map.npz
            └── run.log
"""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import yaml

from .errors import ArtifactNotFoundError, ExperimentNotFoundError
from .models import EXPERIMENT_ID_PATTERN, ExperimentRecord

logger = logging.getLogger(__name__)

EXPERIMENT_FILE = "experiment.json"
CONFIG_FILE = "config.yaml"
ARTIFACTS_DIR = "artifacts"


class ExperimentStore(ABC):
    """实验仓库接口 / Experiment store interface."""

    @abstractmethod
    def create(self, experiment: ExperimentRecord) -> ExperimentRecord: ...

    @abstractmethod
    def get(self, experiment_id: str) -> ExperimentRecord | None: ...

    @abstractmethod
    def update(self, experiment: ExperimentRecord) -> ExperimentRecord: ...

    @abstractmethod
    def list(self, limit: int = 50, offset: int = 0) -> list[ExperimentRecord]: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def artifact_dir(self, experiment_id: str) -> Path:
        """实验产物目录（运行时内部使用，不写入持久化元数据）。"""

    @abstractmethod
    def resolve_artifact(self, experiment_id: str, relative_path: str) -> Path:
        """安全解析产物路径，保证结果位于该实验的产物目录内。"""


def atomic_write_text(path: Path, text: str) -> None:
    """写入 <name>.tmp 后 os.replace，避免进程异常导致半写入文件。"""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class FileExperimentStore(ExperimentStore):
    """文件型实验仓库 / File-based experiment store."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @property
    def root(self) -> Path:
        return self._root

    def _experiment_dir(self, experiment_id: str) -> Path:
        if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
            raise ExperimentNotFoundError(f"Invalid experiment id: {experiment_id!r}")
        return self._root / experiment_id

    def _write(self, experiment: ExperimentRecord) -> None:
        path = self._experiment_dir(experiment.experiment_id) / EXPERIMENT_FILE
        atomic_write_text(path, experiment.model_dump_json(indent=2))

    def create(self, experiment: ExperimentRecord) -> ExperimentRecord:
        with self._lock:
            exp_dir = self._experiment_dir(experiment.experiment_id)
            if exp_dir.exists():
                raise FileExistsError(f"Experiment already exists: {experiment.experiment_id}")
            (exp_dir / ARTIFACTS_DIR).mkdir(parents=True)
            atomic_write_text(
                exp_dir / CONFIG_FILE,
                yaml.safe_dump(experiment.config, allow_unicode=True, sort_keys=False),
            )
            self._write(experiment)
        return experiment

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        try:
            path = self._experiment_dir(experiment_id) / EXPERIMENT_FILE
        except ExperimentNotFoundError:
            return None
        if not path.is_file():
            return None
        return ExperimentRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def update(self, experiment: ExperimentRecord) -> ExperimentRecord:
        with self._lock:
            if not (self._experiment_dir(experiment.experiment_id) / EXPERIMENT_FILE).is_file():
                raise ExperimentNotFoundError(experiment.experiment_id)
            self._write(experiment)
        return experiment

    def _load_all(self) -> list[ExperimentRecord]:
        records = []
        for path in self._root.glob(f"EXP-*/{EXPERIMENT_FILE}"):
            try:
                records.append(ExperimentRecord.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError) as e:
                logger.warning("Skipping unreadable experiment record %s: %s", path, e)
        return records

    def list(self, limit: int = 50, offset: int = 0) -> list[ExperimentRecord]:
        records = sorted(self._load_all(), key=lambda r: r.created_at, reverse=True)
        return records[offset: offset + limit]

    def count(self) -> int:
        return len(self._load_all())

    def artifact_dir(self, experiment_id: str) -> Path:
        return self._experiment_dir(experiment_id) / ARTIFACTS_DIR

    def resolve_artifact(self, experiment_id: str, relative_path: str) -> Path:
        root = self.artifact_dir(experiment_id).resolve()
        candidate = (root / relative_path).resolve()
        if not candidate.is_relative_to(root) or candidate == root:
            raise ArtifactNotFoundError(
                f"Artifact path escapes artifact root: {relative_path!r}"
            )
        if not candidate.is_file():
            raise ArtifactNotFoundError(f"Artifact not found: {relative_path!r}")
        return candidate
