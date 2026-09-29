from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        relative = file.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big")); digest.update(relative)
        content = file.read_bytes()
        digest.update(len(content).to_bytes(8, "big")); digest.update(content)
    return digest.hexdigest()


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
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((root / "validation.json").read_text(encoding="utf-8"))
    smoke = json.loads((root / "smoke.json").read_text(encoding="utf-8"))
    experiment = json.loads((root / "experiment.json").read_text(encoding="utf-8"))
    provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "evidence-descriptor.json").read_text(encoding="utf-8"))
    verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
    checks = [
        validation.get("status") == "PASS",
        smoke.get("status") == "PASS" and smoke.get("real_sionna_used") is False,
        registration.get("status") == "REGISTERED",
        registration.get("package_hash") == validation.get("package_hash"),
        experiment.get("package_hash") == registration.get("package_hash"),
        provenance.get("package_hash") == registration.get("package_hash"),
        evidence.get("package_hash") == registration.get("package_hash"),
        registration.get("manifest_hash") == hashlib.sha256(canonical(manifest)).hexdigest(),
        registration.get("source_hash") == source_hash(root.parent.parent.parent / registration.get("path", "")),
        registration.get("package_hash") == hashlib.sha256(canonical({"manifest_hash": registration.get("manifest_hash"), "source_hash": registration.get("source_hash")})).hexdigest(),
        provenance.get("paper_reproduced") is False,
        provenance.get("algorithm_correct") is False,
        experiment.get("status") == "completed",
    ]
    historical_benchmark = root.parent.parent / "benchmarks" / "BENCH-DAY10-EXT-3C12U001" / "benchmark.json"
    if historical_benchmark.is_file():
        benchmark_id = json.loads(historical_benchmark.read_text(encoding="utf-8"))
        checks.append(benchmark_id.get("provenance", {}).get("package_hash") == registration.get("package_hash"))
    if not all(checks):
        print("FAIL onboarding evidence checks")
        return 1
    # Only a pending Day 11 record is transitioned. Historical Day 4-10
    # references keep their original semantics and numerical values.
    current_status = str(evidence.get("verification_status", "")).lower()
    if current_status not in {"independently_verified", "independent_verified"}:
        verified_at = datetime.now(timezone.utc).isoformat()
        verification_hash = hashlib.sha256(canonical({
            "package_hash": registration["package_hash"],
            "source_hash": registration.get("source_hash"),
            "manifest_hash": registration.get("manifest_hash"),
            "run_id": experiment.get("run_id"),
            "status": experiment.get("status"),
            "channel_hash": provenance.get("channel_hash"),
            "trace": json.loads((root / "trace.json").read_text(encoding="utf-8")),
        })).hexdigest()
        verification.update({"status": "VERIFIED", "verification_status": "verified", "verified": True,
                             "verifier_id": "algorithm-onboarding-independent-verifier-v0.2",
                             "verified_at": verified_at, "verification_hash": verification_hash})
        evidence.update({"verification_status": "verified", "verified": True,
                         "verifier_id": "algorithm-onboarding-independent-verifier-v0.2",
                         "verified_at": verified_at, "verification_hash": verification_hash})
        (root / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "evidence-descriptor.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ALGORITHM ONBOARDING VERIFIER: PASS ({root.name})")
    print(f"package_hash={registration['package_hash']}")
    print("verification_transition=VERIFIED" if current_status not in {"independently_verified", "independent_verified"} else "verification_transition=LEGACY_UNCHANGED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
