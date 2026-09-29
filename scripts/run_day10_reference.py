from pathlib import Path

from algorithm_packages import AlgorithmPackageService


service = AlgorithmPackageService(Path.cwd())
record = service.run_and_wait(
    "example_external_optimizer--0.1.0",
    "MULTICELL-DEMO-001",
    {"seed": 20260929, "candidate_offset": 1},
    8,
)
print(record.get("run_id"), record.get("status"), record.get("benchmark_id"))
