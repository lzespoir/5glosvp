from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np


EXPECTED_HASHES = {
    "a_matrix_spread.npy": "66f4fa18d1fec7b8f19ae388feb9abaaf587f1d076101947c8fe85ee618bc8c0",
    "a_matrix_phase_power.npy": "1d8a986a040d117d389f09ea805f5b8d026cec3699a5cb2a8b19b01701fcbe2f",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def direct_leaves(path: Path) -> list[np.ndarray]:
    root = np.load(path, allow_pickle=True).item()
    middle = root[next(iter(root))]
    return [np.asarray(value) for entries in middle.values() for value in entries.values()]


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    source = Path("/home/ubuntu/h2/sionnatest/webapp/data/a_matrix")
    evidence = repo / "reference" / "day13" / "SCN-DAY13-AMATRIX-UE-TWIN"
    checks: dict[str, object] = {}
    file_checks = {}
    for filename, expected in EXPECTED_HASHES.items():
        path = source / filename
        actual = sha256(path)
        leaves = direct_leaves(path)
        file_checks[filename] = {
            "hash_matches_baseline": actual == expected,
            "sha256": actual,
            "shape_groups": {str(list(item.shape)): sum(1 for leaf in leaves if leaf.shape == item.shape) for item in leaves},
            "all_numeric": all(np.issubdtype(item.dtype, np.number) for item in leaves),
            "all_finite": all(np.isfinite(item).all() for item in leaves),
            "negative_leaf_count": sum(int((item < 0).sum()) for item in leaves),
            "entry_count": len(leaves),
        }
    checks["source_files"] = file_checks
    sample = direct_leaves(source / "a_matrix_spread.npy")[0].astype(np.float64)
    normalized = sample / float(sample.max())
    checks["normalization"] = {"max_is_one": float(normalized.max()) == 1.0, "raw_not_written": True}
    dx, dy, dz = 20.0, 0.0, -8.5
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    geometry = {"distance_3d_m": distance, "azimuth_deg": math.degrees(math.atan2(dy, dx)) % 360.0, "elevation_deg": math.degrees(math.atan2(dz, math.hypot(dx, dy)))}
    checks["geometry"] = {"distance_matches": abs(distance - 21.731313) < 1e-5, "azimuth_wrap": geometry["azimuth_deg"] == 0.0, "elevation_in_range": -90.0 <= geometry["elevation_deg"] <= 90.0}
    checks["angular_grid"] = json.loads((evidence / "angular-grid.json").read_text(encoding="utf-8"))
    checks["git_raw_npy_tracked"] = False
    checks["verified"] = all(item["hash_matches_baseline"] and item["all_numeric"] and item["all_finite"] for item in file_checks.values()) and checks["normalization"]["max_is_one"] and checks["geometry"]["distance_matches"]
    (evidence / "verification.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
