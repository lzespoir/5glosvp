from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np

from .models import (
    AMatrixEntry,
    AMatrixLibrary,
    AMatrixManifest,
    AMatrixSourceStatus,
    AngularGrid,
    BeamPattern,
    DataQuality,
    NormalizationPolicy,
)

ANGULAR_GRID = AngularGrid()
NORMALIZATION = NormalizationPolicy()
LIBRARY_FILES = {
    "spread": "a_matrix_spread.npy",
    "phase_power": "a_matrix_phase_power.npy",
}
FAMILY_LABELS = {"spread": "8_BEAM_FAMILY", "phase_power": "7_BEAM_FAMILY"}
SSB_KEY_RE = re.compile(
    r"^(?P<aau>[^#]+)#(?P<arr>.+?)ssbcase(?P<case>\d+)_"
    r"(?P<nbeam>\d+)beam__tilt(?P<tilt>-?\d+)_azimuth(?P<az>-?\d+)#(?P<bid>\d+)$"
)
CSI_KEY_RE = re.compile(
    r"^(?P<aau>[^#]+)#(?P<arr>.+?)csi-rscase(?P<case>\d+)_"
    r"(?P<nbeam>\d+)beam(?:__tilt(?P<tilt>-?\d+)(?:_azimuth(?P<az>-?\d+))?)?_#"
    r"(?P<bid>\d+)$"
)


class AMatrixDataError(ValueError):
    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


def default_source_dir() -> Path:
    return Path(
        os.environ.get(
            "DAY13_AMATRIX_SOURCE_DIR",
            "/home/ubuntu/h2/sionnatest/webapp/data/a_matrix",
        )
    )


def parse_entry_key(entry_key: str, beam_type: str) -> dict[str, Any]:
    matcher = SSB_KEY_RE if beam_type.upper() == "SSB" else CSI_KEY_RE
    match = matcher.match(entry_key)
    if not match:
        return {}
    data = match.groupdict()
    return {
        "aau_type": data["aau"],
        "beam_id": int(data["bid"]),
        "coverage": int(data["case"]),
        "nbeam_label": int(data["nbeam"]),
        "tilt_deg": int(data["tilt"]) if data.get("tilt") else None,
        "azimuth_deg": int(data["az"]) if data.get("az") else None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quality(array: np.ndarray) -> DataQuality:
    numeric = np.asarray(array)
    shape = list(numeric.shape)
    dtype = str(numeric.dtype)
    if numeric.ndim != 2 or tuple(numeric.shape) != (91, 72):
        raise AMatrixDataError(
            "INVALID_A_MATRIX_SHAPE",
            f"A-Matrix entry shape must be (91, 72), got {tuple(numeric.shape)}",
            {"shape": shape},
        )
    if not np.issubdtype(numeric.dtype, np.number):
        raise AMatrixDataError("INVALID_A_MATRIX_DTYPE", "A-Matrix entry must be numeric")
    values = np.asarray(numeric, dtype=np.float64)
    nan_count = int(np.isnan(values).sum())
    inf_count = int(np.isinf(values).sum())
    finite = nan_count == 0 and inf_count == 0
    if not finite:
        raise AMatrixDataError(
            "INVALID_A_MATRIX_FINITE",
            "A-Matrix entry contains NaN or Inf",
            {"nan_count": nan_count, "inf_count": inf_count},
        )
    negative_count = int((values < 0).sum())
    max_value = float(values.max())
    all_zero = bool(np.all(values == 0))
    return DataQuality(
        shape=shape,
        dtype=dtype,
        finite=True,
        nan_count=nan_count,
        inf_count=inf_count,
        negative_count=negative_count,
        min_value=float(values.min()),
        max_value=max_value,
        all_zero=all_zero,
        status="DATA_SEMANTICS_WARNING" if negative_count else "VALID",
    )


def normalize_response(raw_response: np.ndarray) -> tuple[np.ndarray, np.ndarray, DataQuality]:
    raw = np.asarray(raw_response, dtype=np.float64)
    quality = _quality(raw)
    if quality.max_value <= 0:
        raise AMatrixDataError(
            "INVALID_A_MATRIX_RESPONSE",
            "A-Matrix response max must be greater than zero; all-zero/negative input is not usable",
        )
    normalized = raw / quality.max_value
    field_amplitude = np.sqrt(np.maximum(normalized, 0.0))
    return normalized, field_amplitude, quality


class AMatrixAdapter:
    """Read-only compatible adapter for the sionnatest A-Matrix libraries."""

    def __init__(self, source_dir: Path | str | None = None) -> None:
        self.source_dir = Path(source_dir or default_source_dir())
        self._libraries: dict[str, dict[str, Any]] = {}
        self._hash_cache: dict[Path, str] = {}

    def _path(self, library_id: str) -> Path:
        try:
            filename = LIBRARY_FILES[library_id]
        except KeyError as exc:
            raise AMatrixDataError("UNKNOWN_A_MATRIX_LIBRARY", f"Unknown A-Matrix library: {library_id}") from exc
        path = self.source_dir / filename
        if not path.is_file():
            raise AMatrixDataError("A_MATRIX_SOURCE_NOT_FOUND", f"A-Matrix source not found: {filename}")
        return path

    def _source_hash(self, path: Path) -> str:
        if path not in self._hash_cache:
            self._hash_cache[path] = _sha256(path)
        return self._hash_cache[path]

    def _load(self, library_id: str) -> dict[str, Any]:
        if library_id in self._libraries:
            return self._libraries[library_id]
        path = self._path(library_id)
        root = np.load(path, allow_pickle=True).item()
        if not isinstance(root, dict) or not root:
            raise AMatrixDataError("INVALID_A_MATRIX_CONTAINER", f"Invalid A-Matrix container: {path.name}")
        top_key = next(iter(root))
        middle = root[top_key]
        if not isinstance(middle, dict):
            raise AMatrixDataError("INVALID_A_MATRIX_CONTAINER", f"Invalid A-Matrix hierarchy: {path.name}")
        patterns: dict[str, dict[str, np.ndarray]] = {}
        for beam_type, entries in middle.items():
            if isinstance(entries, dict):
                patterns[str(beam_type)] = {str(k): np.asarray(v) for k, v in entries.items()}
        data = {"top_key": str(top_key), "patterns": patterns, "path": path}
        self._libraries[library_id] = data
        return data

    def _find(self, library_id: str, beam_type: str, entry_key: str) -> tuple[str, np.ndarray]:
        preferred = [beam_type, beam_type.upper(), "SSB", "CSI-RS"]
        libraries = [library_id, *[item for item in LIBRARY_FILES if item != library_id]]
        for lib in libraries:
            data = self._load(lib)
            for candidate in preferred + list(data["patterns"]):
                if entry_key in data["patterns"].get(candidate, {}):
                    return lib, data["patterns"][candidate][entry_key]
        raise AMatrixDataError("A_MATRIX_ENTRY_NOT_FOUND", f"A-Matrix entry not found: {entry_key}")

    def _entry_model(self, library_id: str, beam_type: str, entry_key: str, array: np.ndarray) -> AMatrixEntry:
        path = self._path(library_id)
        metadata = parse_entry_key(entry_key, beam_type)
        quality = _quality(array)
        mapping_status = "CONFIRMED_BY_PROFILE" if entry_key in self._profile_entry_keys() else "PARTIAL"
        return AMatrixEntry(
            entry_key=entry_key,
            raw_shape=list(array.shape),
            dtype=str(array.dtype),
            beam_id=metadata.get("beam_id"),
            beam_family=FAMILY_LABELS[library_id],
            beam_type=beam_type,
            aau_type=metadata.get("aau_type"),
            coverage=metadata.get("coverage"),
            tilt_deg=metadata.get("tilt_deg"),
            azimuth_deg=metadata.get("azimuth_deg"),
            source_file_name=path.name,
            source_hash=self._source_hash(path),
            mapping_status=mapping_status,
            data_quality=quality,
        )

    def libraries(self) -> list[AMatrixLibrary]:
        result = []
        for library_id, filename in LIBRARY_FILES.items():
            data = self._load(library_id)
            path = self._path(library_id)
            result.append(
                AMatrixLibrary(
                    library_id=library_id,
                    family=FAMILY_LABELS[library_id],
                    source_file_name=filename,
                    source_artifact="sionnatest/a_matrix",
                    source_hash=self._source_hash(path),
                    entry_count=sum(len(v) for v in data["patterns"].values()),
                    beam_types={k: len(v) for k, v in data["patterns"].items()},
                )
            )
        return result

    def profiles(self) -> list[dict[str, Any]]:
        path = self.source_dir / "profiles.json"
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("profiles") or []) if isinstance(data, dict) else []

    def _profile_entry_keys(self) -> set[str]:
        keys: set[str] = set()
        for profile in self.profiles():
            if profile.get("entry_key"):
                keys.add(str(profile["entry_key"]))
            raw = profile.get("keys_by_beam")
            if isinstance(raw, dict):
                keys.update(str(value) for value in raw.values())
        return keys

    def entry(self, library_id: str, beam_type: str, entry_key: str) -> tuple[AMatrixEntry, np.ndarray]:
        actual_library, array = self._find(library_id, beam_type, entry_key)
        actual_type = beam_type
        for candidate, entries in self._load(actual_library)["patterns"].items():
            if entry_key in entries:
                actual_type = candidate
                break
        return self._entry_model(actual_library, actual_type, entry_key, array), np.asarray(array, dtype=np.float64)

    def pattern(self, library_id: str, beam_type: str, entry_key: str) -> BeamPattern:
        entry, raw = self.entry(library_id, beam_type, entry_key)
        normalized, field_amplitude, _ = normalize_response(raw)
        return BeamPattern(
            entry=entry,
            angular_grid=ANGULAR_GRID,
            normalization=NORMALIZATION,
            normalized_response=normalized.tolist(),
            field_amplitude=field_amplitude.tolist(),
        )

    def manifest(self) -> list[AMatrixManifest]:
        manifests = []
        for library in self.libraries():
            path = self._path(library.library_id)
            manifests.append(
                AMatrixManifest(
                    artifact_id=f"AMX-D13-{library.source_hash[:12].upper()}",
                    source_family=library.family,
                    source_file_name=library.source_file_name,
                    source_hash=library.source_hash,
                    source_size_bytes=path.stat().st_size,
                    source_mtime_ns=path.stat().st_mtime_ns,
                    entry_count=library.entry_count,
                    shape=[91, 72],
                    dtype="object-container/float64-leaf",
                    angular_grid_version=ANGULAR_GRID.version,
                    normalization_policy=NORMALIZATION.policy_id,
                    profile_mapping_version="sionnatest-profiles-v1",
                    semantic_status="RELATIVE_RESPONSE_ONLY",
                )
            )
        return manifests

    def source_status(self) -> AMatrixSourceStatus:
        files = []
        for path in sorted(self.source_dir.glob("*.npy")):
            files.append({"name": path.name, "size_bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns, "sha256": self._source_hash(path)})
        return AMatrixSourceStatus(source_path=str(self.source_dir), files=files)
