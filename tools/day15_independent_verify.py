"""Independent persisted-object audit. Uses only the Python standard library.

Does not call WorkspaceService, Pydantic models, or production validators.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def rows(root: Path, collection: str):
    return [json.loads(path.read_text(encoding="utf-8")) for path in (root / collection).glob("*.json")]


def verify(root: Path):
    problems = []
    scenarios = rows(root, "scenarios")
    instances = rows(root, "instances")
    assets = rows(root, "assets")
    asset_by_id = {item["asset_id"]: item for item in assets}
    scenario_by_id = {item["scenario_id"]: item for item in scenarios}
    if len(scenario_by_id) != len(scenarios):
        problems.append("duplicate scenario ID")
    for row in scenarios:
        source = dict(row)
        for key in ("state", "version", "definition_hash", "created_at", "updated_at", "lineage"):
            source.pop(key, None)
        if canonical(source) != row["definition_hash"]:
            problems.append(f"definition hash mismatch: {row['scenario_id']}")
        if row["state"] == "READY":
            problems.append(f"false runnable state: {row['scenario_id']}")
        environment = row.get("environment")
        if environment and environment.get("asset_id"):
            asset = asset_by_id.get(environment["asset_id"])
            if not asset or asset.get("sha256") != environment.get("asset_sha256"):
                problems.append(f"asset provenance mismatch: {row['scenario_id']}")
    for item in instances:
        frozen = item["frozen_definition"]
        identity = {"scenario_id": item["scenario_id"], "version": item["scenario_version"], "definition_hash": item["definition_hash"], "asset_hashes": item.get("asset_hashes", {}), "seed": item["seed"]}
        if canonical(identity) != item["identity_hash"]:
            problems.append(f"instance identity mismatch: {item['instance_id']}")
        if frozen["scenario_id"] != item["scenario_id"] or frozen["definition_hash"] != item["definition_hash"] or frozen["version"] != item["scenario_version"]:
            problems.append(f"frozen snapshot mismatch: {item['instance_id']}")
        if item["run_status"] != "NOT_EXECUTED":
            problems.append(f"unexpected execution status: {item['instance_id']}")
        if item["scenario_id"] not in scenario_by_id:
            problems.append(f"orphan instance: {item['instance_id']}")
    report = {"verifier": "day15_independent_verify_stdlib_v1", "scenario_definition_count": len(scenarios), "asset_count": len(assets), "instance_count": len(instances), "configured_active_count": sum(item["state"] != "ARCHIVED" for item in scenarios), "run_count": 0, "problems": problems, "result": "PASS" if not problems else "FAIL"}
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: day15_independent_verify.py <workspace_store_root>")
    result = verify(Path(sys.argv[1]))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["result"] == "PASS" else 1)
