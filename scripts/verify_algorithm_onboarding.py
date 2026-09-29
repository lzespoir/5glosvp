from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_algorithm_onboarding.py <reference-id>")
        return 2
    root = Path(sys.argv[1]).resolve()
    required = [
        "README.md", "manifest.json", "validation.json", "smoke.json", "registration.json",
        "experiment.json", "trace.json", "logs.json", "kpi.json", "verification.json",
        "provenance.json", "evidence-descriptor.json", "experiment-bundle.zip",
    ]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        print(f"FAIL missing files: {missing}")
        return 1
    registration = json.loads((root / "registration.json").read_text(encoding="utf-8"))
    validation = json.loads((root / "validation.json").read_text(encoding="utf-8"))
    smoke = json.loads((root / "smoke.json").read_text(encoding="utf-8"))
    experiment = json.loads((root / "experiment.json").read_text(encoding="utf-8"))
    provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "evidence-descriptor.json").read_text(encoding="utf-8"))
    checks = [
        validation.get("status") == "PASS",
        smoke.get("status") == "PASS" and smoke.get("real_sionna_used") is False,
        registration.get("status") == "REGISTERED",
        registration.get("package_hash") == validation.get("package_hash"),
        experiment.get("package_hash") == registration.get("package_hash"),
        provenance.get("package_hash") == registration.get("package_hash"),
        evidence.get("package_hash") == registration.get("package_hash"),
        provenance.get("paper_reproduced") is False,
        provenance.get("algorithm_correct") is False,
        experiment.get("status") == "completed",
    ]
    benchmark_id = json.loads((root.parent.parent / "benchmarks" / "BENCH-DAY10-EXT-3C12U001" / "benchmark.json").read_text(encoding="utf-8"))
    checks.append(benchmark_id.get("provenance", {}).get("package_hash") == registration.get("package_hash"))
    if not all(checks):
        print("FAIL onboarding evidence checks")
        return 1
    print(f"ALGORITHM ONBOARDING VERIFIER: PASS ({root.name})")
    print(f"package_hash={registration['package_hash']}")
    print(f"benchmark_id=BENCH-DAY10-EXT-3C12U001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
