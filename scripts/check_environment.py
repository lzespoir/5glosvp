"""
环境检查 / Environment check.

Usage:
    python scripts/check_environment.py [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from simulation.backends import get_backend  # noqa: E402

LINE = "=" * 50


def _row(label: str, status: str, detail: str = "") -> str:
    text = f"{label:<24}{status}"
    return f"{text}    ({detail})" if detail else text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print raw JSON report")
    args = parser.parse_args()

    report = get_backend("sionna_rt").health_check()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["available"] else 1

    def pf(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    print(LINE)
    print("5G Validation Platform")
    print("Environment Check / 环境检查")
    print(LINE)
    print()
    print(_row("Python", pf(report["python_ok"]), report["python_version"]))
    print(_row("Sionna RT", pf(report["sionna_rt_importable"]), report["sionna_rt_version"] or "not installed"))
    print(_row("Mitsuba", pf(report["mitsuba_available"]), report["mitsuba_version"] or "-"))
    print(_row("Dr.Jit", pf(report["drjit_available"]), report["drjit_version"] or "-"))
    print(_row("Mitsuba Variant", report["mitsuba_variant"] or "NONE"))
    print()
    print(_row("GPU", "AVAILABLE (CUDA)" if report["gpu_available"] else "OPTIONAL / NOT FOUND"))
    print(_row("CPU (LLVM)", "AVAILABLE" if report["llvm_available"] else "NOT FOUND"))
    print(_row("Scene smoke test", pf(report["scene_smoke_test"])))
    print()
    print(_row("Sionna RT Backend", "READY" if report["available"] else "NOT READY"))

    if report["warnings"]:
        print()
        print("Warnings / 警告:")
        for w in report["warnings"]:
            print(f"  - {w}")
    if report["errors"]:
        print()
        print("Errors / 错误:")
        for e in report["errors"]:
            print(f"  - {e}")
    print()
    print(LINE)
    return 0 if report["available"] else 1


if __name__ == "__main__":
    sys.exit(main())
