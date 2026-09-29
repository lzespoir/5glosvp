from __future__ import annotations

import json
from pathlib import Path

from scenarios.service import ScenarioSystemService


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence = root / "reference" / "scenario_system" / "SCN-DAY12-FOUNDATION"
    evidence.mkdir(parents=True, exist_ok=True)
    service = ScenarioSystemService()
    write_json(evidence / "taxonomy.json", service.taxonomy().model_dump(mode="json"))
    write_json(evidence / "coverage-summary.json", service.coverage().model_dump(mode="json"))
    write_json(evidence / "scenario-catalog.json", [item.model_dump(mode="json") for item in service.catalog.definitions()])
    write_json(evidence / "compatibility-rules.json", [item.model_dump(mode="json") for item in service.rules()])
    write_json(evidence / "acceptance-mapping.json", [item.model_dump(mode="json") for item in service.acceptance()])
    write_json(evidence / "verification.json", service.verify())
    (evidence / "README.md").write_text(
        "# DAY12 Scenario System Foundation Evidence\n\n"
        "本 evidence 由 taxonomy + compatibility rules + catalog 独立重算生成。\n"
        "理论组合、有效组合、可执行组合、已实例化、已执行、已验证和验收证据分开记录；"
        "本 evidence 不宣称百余场景已完成系统级仿真验证。\n\n"
        "A 矩阵原始 .npy 保留在外部只读目录，不进入 Git；其画像见 design/DAY12_A_MATRIX_DATA_PROFILE.md。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
