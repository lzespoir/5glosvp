from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class AMatrixArtifact(BaseModel):
    artifact_id: str
    artifact_type: str = "A_MATRIX"
    file_name: str
    file_hash: str
    file_size: int
    numpy_dtype: str
    numpy_shape: list[int]
    numpy_ndim: int
    element_count: int
    leaf_arrays: int
    leaf_shape_groups: dict[str, int]
    leaf_dtype_groups: dict[str, int]
    contains_nan: bool
    contains_inf: bool
    is_complex: bool
    observed_value_summary: dict[str, Any] = Field(default_factory=dict)
    semantic_status: str = "OBSERVED_DATA_ONLY"
    device_id: str = "UNKNOWN"
    axis_semantics: str = "UNKNOWN"
    unit: str = "UNKNOWN"
    measurement_coordinate_system: str = "UNKNOWN"
    beam_axis: str = "UNKNOWN"


def _leaves(value: Any) -> list[np.ndarray]:
    if isinstance(value, np.ndarray): return [value]
    if isinstance(value, dict):
        out: list[np.ndarray] = []
        for child in value.values(): out.extend(_leaves(child))
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for child in value: out.extend(_leaves(child))
        return out
    return []


def profile_file(path: Path) -> AMatrixArtifact:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    root = np.load(path, allow_pickle=True)
    leaves = _leaves(root.item() if root.shape == () and root.dtype == object else root)
    numeric = [item for item in leaves if np.issubdtype(item.dtype, np.number)]
    shapes: dict[str, int] = {}
    dtypes: dict[str, int] = {}
    for item in leaves:
        key = str(list(item.shape)); shapes[key] = shapes.get(key, 0) + 1
        dtypes[str(item.dtype)] = dtypes.get(str(item.dtype), 0) + 1
    complex_items = [item for item in numeric if np.iscomplexobj(item)]
    summary: dict[str, Any] = {}
    if complex_items:
        real = np.concatenate([item.real.ravel() for item in complex_items]); imag = np.concatenate([item.imag.ravel() for item in complex_items]); mag = np.concatenate([np.abs(item).ravel() for item in complex_items])
        summary = {"real": [float(real.min()), float(real.max()), float(real.mean()), float(real.std())], "imag": [float(imag.min()), float(imag.max()), float(imag.mean()), float(imag.std())], "magnitude": [float(mag.min()), float(mag.max()), float(mag.mean()), float(mag.std())]}
    elif numeric:
        merged = np.concatenate([item.astype(np.float64, copy=False).ravel() for item in numeric])
        summary = {"min": float(merged.min()), "max": float(merged.max()), "mean": float(merged.mean()), "std": float(merged.std())}
    return AMatrixArtifact(
        artifact_id=f"A-MATRIX-{digest[:12].upper()}", file_name=path.name, file_hash=digest, file_size=path.stat().st_size,
        numpy_dtype=str(root.dtype), numpy_shape=list(root.shape), numpy_ndim=root.ndim, element_count=int(root.size), leaf_arrays=len(leaves),
        leaf_shape_groups=shapes, leaf_dtype_groups=dtypes, contains_nan=any(np.isnan(item).any() for item in numeric), contains_inf=any(np.isinf(item).any() for item in numeric),
        is_complex=bool(complex_items), observed_value_summary=summary,
    )


def profile_directory(root: Path) -> list[AMatrixArtifact]:
    return [profile_file(path) for path in sorted(Path(root).glob("*.npy"))]
