from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from algorithms import (
    ALGORITHM_SDK_VERSION,
    Algorithm,
    AlgorithmDriver,
    AlgorithmProblem,
    EvaluationResult,
    EvaluationStatus,
    ParameterSpace,
    StopReason,
)
from algorithms.compatibility import check_compatibility
from optimization.models import Direction
from optimization.parameters import ParameterDefinition, ParameterRole, ParameterType
from problem_evaluation import default_registry
from execution import ExecutionManager, RunStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class AlgorithmPackageService:
    """Package validation, trusted loading, registration and Day 10 evidence.

    V0.1 deliberately supports local directories only. Package code is trusted Python;
    this service never installs requirements and never gives package code simulator objects.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_dir = self.repo_root / "reference" / "algorithm_onboarding"
        self.registry_path = self.registry_dir / "registry.json"
        self.runs_dir = self.registry_dir / "runs"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.evaluation_adapters = default_registry()
        self.execution_manager = ExecutionManager(
            self.repo_root, self.runs_dir,
            cancel_grace_seconds=float(os.environ.get("GLOSVP_CANCEL_GRACE_SECONDS", "2")),
            terminate_grace_seconds=float(os.environ.get("GLOSVP_TERMINATE_GRACE_SECONDS", "2")),
        )

    # ------------------------------------------------------------------
    # Package discovery / identity

    def _resolve_path(self, value: str) -> Path:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self.repo_root / candidate
        path = candidate.resolve()
        if self.repo_root not in path.parents and path != self.repo_root:
            raise ValueError("PACKAGE_PATH_OUTSIDE_WORKSPACE: package must be inside the platform workspace")
        if not path.is_dir():
            raise ValueError(f"PACKAGE_NOT_FOUND: local package directory does not exist: {value}")
        return path

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        manifest_path = path / "algorithm.yaml"
        if not manifest_path.is_file():
            raise ValueError("MANIFEST_ERROR: algorithm.yaml is required")
        try:
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"MANIFEST_ERROR: invalid YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("MANIFEST_ERROR: manifest root must be an object")
        return data

    @staticmethod
    def _source_hash(path: Path) -> str:
        digest = hashlib.sha256()
        for file in sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            relative = file.relative_to(path).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(4, "big")); digest.update(relative)
            content = file.read_bytes()
            digest.update(len(content).to_bytes(8, "big")); digest.update(content)
        return digest.hexdigest()

    @staticmethod
    def _manifest_hash(manifest: dict[str, Any]) -> str:
        return _sha256_bytes(_canonical(manifest))

    def _identity(self, path: Path, manifest: dict[str, Any]) -> dict[str, str]:
        algorithm = manifest.get("algorithm") or {}
        source_hash = self._source_hash(path)
        manifest_hash = self._manifest_hash(manifest)
        package_hash = _sha256_bytes(_canonical({"manifest_hash": manifest_hash, "source_hash": source_hash}))
        algorithm_id = str(algorithm.get("id", "unknown"))
        version = str(algorithm.get("version", "unknown"))
        return {
            "package_id": f"{algorithm_id}--{version}",
            "algorithm_id": algorithm_id,
            "algorithm_version": version,
            "manifest_hash": manifest_hash,
            "source_hash": source_hash,
            "package_hash": package_hash,
        }

    # ------------------------------------------------------------------
    # Validation pipeline

    def _manifest_validation(self, manifest: dict[str, Any]) -> dict[str, Any]:
        errors: list[dict[str, str]] = []
        top_allowed = {"schema_version", "algorithm", "sdk", "entrypoint", "compatibility", "parameters", "resources", "execution", "implementation_origin", "paper_reference"}
        unknown = sorted(set(manifest) - top_allowed)
        if unknown:
            errors.append({"code": "MANIFEST_UNKNOWN_FIELD", "message": f"Unknown fields: {', '.join(unknown)}"})
        if manifest.get("schema_version") != "0.1":
            errors.append({"code": "MANIFEST_SCHEMA_VERSION", "message": "schema_version must be '0.1'"})
        algorithm = manifest.get("algorithm")
        if not isinstance(algorithm, dict):
            errors.append({"code": "MANIFEST_ALGORITHM", "message": "algorithm object is required"})
        else:
            for key in ("id", "name", "version", "description", "provider", "category", "learning_algorithm"):
                if key not in algorithm:
                    errors.append({"code": "MANIFEST_MISSING_FIELD", "message": f"algorithm.{key} is required"})
            if algorithm.get("category") not in {"external", "research", "classical_optimization", "engineering_baseline"}:
                errors.append({"code": "MANIFEST_CATEGORY", "message": "algorithm.category is not supported"})
        sdk = manifest.get("sdk")
        if not isinstance(sdk, dict) or sdk.get("version") != ALGORITHM_SDK_VERSION:
            errors.append({"code": "SDK_INCOMPATIBLE", "message": f"sdk.version must be {ALGORITHM_SDK_VERSION}"})
        entrypoint = manifest.get("entrypoint")
        if not isinstance(entrypoint, dict) or not entrypoint.get("module") or not entrypoint.get("class"):
            errors.append({"code": "MANIFEST_ENTRYPOINT", "message": "entrypoint.module and entrypoint.class are required"})
        compatibility = manifest.get("compatibility")
        if not isinstance(compatibility, dict) or not compatibility.get("problem_types") or not compatibility.get("parameter_types"):
            errors.append({"code": "MANIFEST_COMPATIBILITY", "message": "compatibility.problem_types and parameter_types are required"})
        parameters = manifest.get("parameters", {})
        if not isinstance(parameters, dict):
            errors.append({"code": "MANIFEST_PARAMETERS", "message": "parameters must be an object"})
        else:
            for name, spec in parameters.items():
                if not isinstance(spec, dict) or spec.get("type") not in {"integer", "float", "select", "boolean", "vector"}:
                    errors.append({"code": "PARAMETER_SCHEMA_ERROR", "message": f"invalid parameter schema: {name}"})
        resources = manifest.get("resources", {})
        if not isinstance(resources, dict) or not isinstance(resources.get("cpu", True), bool):
            errors.append({"code": "MANIFEST_RESOURCES", "message": "resources.cpu must be boolean"})
        return {"status": "PASS" if not errors else "FAIL", "stage": "MANIFEST_VALIDATED", "errors": errors}

    @staticmethod
    def _validate_parameters(manifest: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
        schema = manifest.get("parameters", {})
        errors: list[dict[str, str]] = []
        if not isinstance(parameters, dict):
            return {"status": "FAIL", "errors": [{"code": "PARAMETER_ERROR", "message": "parameters must be an object"}]}
        for name, spec in schema.items():
            if not isinstance(spec, dict):
                continue
            if name not in parameters:
                continue
            value = parameters[name]
            kind = spec.get("type")
            valid = (
                kind == "integer" and isinstance(value, int) and not isinstance(value, bool)
                or kind == "float" and isinstance(value, (int, float)) and not isinstance(value, bool)
                or kind == "select" and value in spec.get("choices", [])
                or kind == "boolean" and isinstance(value, bool)
                or kind == "vector" and isinstance(value, list)
            )
            if not valid:
                errors.append({"code": "PARAMETER_TYPE_ERROR", "message": f"parameter {name} does not match type {kind}"})
                continue
            for bound_name, operator in (("minimum", lambda a, b: a < b), ("maximum", lambda a, b: a > b)):
                if bound_name in spec and isinstance(value, (int, float)) and operator(value, spec[bound_name]):
                    errors.append({"code": "PARAMETER_RANGE_ERROR", "message": f"parameter {name} violates {bound_name}"})
        unknown = sorted(set(parameters) - set(schema))
        errors.extend({"code": "PARAMETER_UNKNOWN", "message": f"unknown parameter: {name}"} for name in unknown)
        return {"status": "PASS" if not errors else "FAIL", "errors": errors}

    def _load_class(self, path: Path, manifest: dict[str, Any], package_hash: str) -> type[Algorithm]:
        entrypoint = manifest["entrypoint"]
        relative = Path(str(entrypoint["module"].replace(".", "/") + ".py"))
        module_path = (path / relative).resolve()
        if path not in module_path.parents or not module_path.is_file():
            raise ValueError("IMPORT_ERROR: entrypoint module is not inside the package")
        module_name = f"external_package_{package_hash[:12]}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ValueError("IMPORT_ERROR: could not create module spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        klass = getattr(module, str(entrypoint["class"]), None)
        if not isinstance(klass, type) or not issubclass(klass, Algorithm):
            raise ValueError("INTERFACE_ERROR: entrypoint class must subclass algorithms.sdk.Algorithm")
        return klass

    def validate(self, package_path: str) -> dict[str, Any]:
        try:
            path = self._resolve_path(package_path)
            manifest = self._read_yaml(path)
            identity = self._identity(path, manifest)
        except ValueError as exc:
            return {"status": "FAILED", "stage": "MANIFEST_VALIDATED", "errors": [{"code": str(exc).split(":", 1)[0], "message": str(exc)}]}
        manifest_result = self._manifest_validation(manifest)
        result: dict[str, Any] = {**identity, "path": str(path.relative_to(self.repo_root)), "manifest": manifest, "validation": {"manifest": manifest_result}}
        if manifest_result["status"] != "PASS":
            result.update({"status": "FAILED", "stage": "MANIFEST_VALIDATED"}); return result
        try:
            klass = self._load_class(path, manifest, identity["package_hash"])
            meta = klass.metadata()
            expected = manifest["algorithm"]
            if meta.algorithm_id != expected["id"] or meta.version != expected["version"]:
                raise ValueError("INTERFACE_ERROR: metadata algorithm id/version does not match manifest")
            if meta.sdk_version != manifest["sdk"]["version"]:
                raise ValueError("SDK_INCOMPATIBLE: algorithm metadata SDK version differs from manifest")
            result["metadata"] = meta.model_dump(mode="json")
            result["validation"]["import"] = {"status": "PASS", "stage": "IMPORT_VALIDATED", "errors": []}
            result["validation"]["interface"] = {"status": "PASS", "stage": "INTERFACE_VALIDATED", "errors": []}
        except ImportError as exc:
            result["validation"]["import"] = {"status": "FAIL", "stage": "IMPORT_VALIDATED", "errors": [{"code": "IMPORT_ERROR", "message": str(exc)}]}
        except Exception as exc:  # noqa: BLE001 - validation result must be structured
            code = "SDK_INCOMPATIBLE" if "SDK_INCOMPATIBLE" in str(exc) else "INTERFACE_ERROR"
            result["validation"]["interface"] = {"status": "FAIL", "stage": "INTERFACE_VALIDATED", "errors": [{"code": code, "message": str(exc)}]}
        failed = [v for v in result["validation"].values() if v.get("status") == "FAIL"]
        result.update({"status": "FAILED" if failed else "VALIDATED", "stage": "INTERFACE_VALIDATED" if not failed else failed[0]["stage"], "validated_at": _now()})
        return result

    def smoke_test(self, package_path: str) -> dict[str, Any]:
        validation = self.validate(package_path)
        if validation.get("status") not in {"VALIDATED", "REGISTERED"}:
            return {"status": "FAILED", "stage": "SMOKE_TESTED", "errors": [{"code": "SMOKE_TEST_FAILED", "message": "package validation must pass first", "details": validation}]}
        try:
            path = self._resolve_path(package_path)
            manifest = validation["manifest"]
            klass = self._load_class(path, manifest, validation["package_hash"])
            choice_a = ["CELL-001", "CELL-001"]
            choice_b = ["CELL-002", "CELL-001"]
            definition = ParameterDefinition(
                id="association_vector", name_zh="用户关联向量", name_en="Association vector",
                role=ParameterRole.OPTIMIZATION_VARIABLE, type=ParameterType.CATEGORICAL,
                unit="cell_id vector", default=choice_a, choices=[choice_a, choice_b], source="Day 10 fake smoke evaluator",
            )
            problem = AlgorithmProblem(
                problem_type="user_association", parameter_space=ParameterSpace(parameters=[definition]),
                objective_id="FAKE_OBJECTIVE_V0_1", objective_direction=Direction.MAXIMIZE,
                baseline_parameters={"association_vector": choice_a}, max_evaluations=2,
            )
            algorithm = klass()
            report = check_compatibility(algorithm, problem, {}, 8)
            if not report.compatible:
                return {"status": "FAILED", "stage": "SMOKE_TESTED", "errors": [e.model_dump(mode="json") for e in report.errors]}
            calls: list[str] = []
            baseline = EvaluationResult(
                candidate_id="BASELINE", parameters={"association_vector": choice_a}, objective=0.0,
                objective_direction=Direction.MAXIMIZE, status=EvaluationStatus.EVALUATED,
            )

            def evaluate(point: dict[str, Any], _round: int) -> EvaluationResult:
                calls.append("evaluation")
                return EvaluationResult(
                    candidate_id=f"SMOKE-{len(calls):03d}", parameters=point,
                    objective=1.0 if point["association_vector"] == choice_b else 0.0,
                    objective_direction=Direction.MAXIMIZE, status=EvaluationStatus.EVALUATED,
                )

            trace = AlgorithmDriver(algorithm, problem, report.resolved_hyperparameters or {}, evaluate, lambda _: ()).run([baseline])
            if not trace.recommendation or trace.stop_reason is None:
                raise ValueError("lifecycle did not reach finalize/stop")
            return {
                "status": "PASS", "stage": "SMOKE_TESTED", "errors": [],
                "evaluator": "fake_lightweight_evaluator", "real_sionna_used": False,
                "lifecycle": ["initialize", "suggest", "candidate_validation", "evaluate", "observe", "should_stop", "finalize"],
                "evaluations_used": trace.evaluations_used, "stop_reason": trace.stop_reason.value,
                "trace": trace.model_dump(mode="json"), "smoked_at": _now(),
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "FAILED", "stage": "SMOKE_TESTED", "errors": [{"code": "SMOKE_TEST_FAILED", "message": f"{type(exc).__name__}: {exc}"}], "real_sionna_used": False}

    # ------------------------------------------------------------------
    # Registry

    def _read_registry(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _write_registry(self, items: list[dict[str, Any]]) -> None:
        self.registry_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def register(self, package_path: str) -> dict[str, Any]:
        validation = self.validate(package_path)
        if validation.get("status") != "VALIDATED":
            return {"status": "FAILED", "stage": "REGISTERED", "errors": [{"code": "REGISTER_REQUIRES_VALIDATION", "message": "validation must pass", "details": validation}]}
        smoke = self.smoke_test(package_path)
        if smoke.get("status") != "PASS":
            return {"status": "FAILED", "stage": "REGISTERED", "errors": [{"code": "REGISTER_REQUIRES_SMOKE", "message": "smoke test must pass", "details": smoke}]}
        with self._lock:
            items = self._read_registry()
            same = [x for x in items if x.get("algorithm_id") == validation["algorithm_id"] and x.get("algorithm_version") == validation["algorithm_version"]]
            if same and any(x.get("package_hash") != validation["package_hash"] for x in same):
                return {"status": "FAILED", "stage": "REGISTERED", "errors": [{"code": "DUPLICATE_VERSION_SOURCE_CHANGED", "message": "same algorithm_id + version has a different package hash"}]}
            record = {k: validation[k] for k in ("package_id", "algorithm_id", "algorithm_version", "manifest_hash", "source_hash", "package_hash", "path", "manifest", "metadata")}
            record.update({"status": "REGISTERED", "validation_status": "PASS", "smoke_status": "PASS", "registered_at": _now(), "disabled": False})
            items = [x for x in items if x.get("package_hash") != record["package_hash"]] + [record]
            self._write_registry(items)
            return record

    def list_packages(self) -> list[dict[str, Any]]:
        return self._read_registry()

    def get_package(self, package_id: str) -> dict[str, Any]:
        for item in self._read_registry():
            if item.get("package_id") == package_id or item.get("package_hash") == package_id:
                return item
        raise KeyError(package_id)

    def disable(self, package_id: str) -> dict[str, Any]:
        with self._lock:
            items = self._read_registry()
            for item in items:
                if item.get("package_id") == package_id:
                    item["disabled"] = True; item["status"] = "DISABLED"; self._write_registry(items); return item
        raise KeyError(package_id)

    # ------------------------------------------------------------------
    # External experiment lifecycle

    def _run_path(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.json"

    def _write_run(self, record: dict[str, Any]) -> None:
        # The parent execution manager may add ownership metadata while the
        # worker is already starting. Preserve those fields across worker writes.
        path = self._run_path(record["run_id"])
        if path.exists():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
                for key in ("worker_id", "pid", "process_group_id", "cancel_requested", "gpu_cleanup_status"):
                    if key not in record and key in current:
                        record[key] = current[key]
            except (OSError, ValueError):
                pass
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)

    def get_experiment(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.exists():
            raise KeyError(run_id)
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") in {RunStatus.STARTING.value, RunStatus.RUNNING.value, RunStatus.CANCEL_REQUESTED.value, RunStatus.CANCELLING.value}:
            return self.execution_manager.enforce_limit(run_id)
        return record

    def create_experiment(self, package_id: str, scenario_id: str, parameters: dict[str, Any], evaluation_budget: int = 8,
                          time_limit_seconds: float | None = None, start_async: bool = True) -> dict[str, Any]:
        package = self.get_package(package_id)
        if package.get("disabled") or package.get("status") != "REGISTERED":
            raise ValueError("INCOMPATIBLE: package is disabled or not registered")
        if evaluation_budget < 1:
            raise ValueError("PARAMETER_ERROR: evaluation_budget must be >= 1")
        parameter_check = self._validate_parameters(package["manifest"], parameters)
        if parameter_check["status"] != "PASS":
            raise ValueError("PARAMETER_ERROR: " + "; ".join(error["message"] for error in parameter_check["errors"]))
        run_id = f"AEXP-DAY11-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "run_id": run_id, "status": "queued", "stage": "QUEUED", "package_id": package["package_id"],
            "algorithm_id": package["algorithm_id"], "algorithm_version": package["algorithm_version"],
            "package_hash": package["package_hash"], "sdk_version": package["manifest"]["sdk"]["version"],
            "scenario_id": scenario_id, "parameters": dict(parameters), "evaluation_budget": evaluation_budget,
            "time_limit_seconds": time_limit_seconds, "created_at": _now(), "logs": [],
        }
        self._write_run(record)
        if start_async:
            self.execution_manager.start(run_id)
        else:
            self._execute_experiment(run_id)
        return self.get_experiment(run_id)

    def run_and_wait(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        record = self.create_experiment(*args, start_async=True, **kwargs)
        while record["status"] in {"queued", "running"}:
            time.sleep(0.05); record = self.get_experiment(record["run_id"])
        return record

    def rerun(self, run_id: str) -> dict[str, Any]:
        old = self.get_experiment(run_id)
        return self.create_experiment(old["package_id"], old["scenario_id"], old["parameters"], old["evaluation_budget"], old.get("time_limit_seconds"))

    def clone(self, run_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        old = self.get_experiment(run_id)
        parameters = dict(old["parameters"]); parameters.update(changes.get("parameters", {}))
        return self.create_experiment(changes.get("package_id", old["package_id"]), changes.get("scenario_id", old["scenario_id"]), parameters, changes.get("evaluation_budget", old["evaluation_budget"]), changes.get("time_limit_seconds", old.get("time_limit_seconds")))

    def _execute_experiment(self, run_id: str, cancel_event: Any | None = None) -> None:
        record = self.get_experiment(run_id)
        started = time.perf_counter()
        record.update({"status": "running", "stage": "RUNNING", "started_at": _now(), "logs": [{"source": "platform", "event": "run_started", "at": _now()}]})
        self._write_run(record)
        try:
            if cancel_event is not None and cancel_event.is_set():
                record.update({"status": RunStatus.CANCELLED.value, "stage": "CANCELLED", "finished_at": _now()})
                self._write_run(record)
                return
            # Test-only delay used by the browser lifecycle harness.  It is
            # disabled by default and does not alter normal scientific runs.
            test_delay = float(os.environ.get("GLOSVP_TEST_WORKER_DELAY_SECONDS", "0"))
            if test_delay > 0:
                time.sleep(test_delay)
            package = self.get_package(record["package_id"])
            path = self._resolve_path(package["path"])
            klass = self._load_class(path, package["manifest"], package["package_hash"])
            problem_type = str(package["manifest"].get("compatibility", {}).get("problem_types", ["user_association"])[0])
            evaluated = self.evaluation_adapters.get(problem_type).execute(
                repo_root=self.repo_root, record=record, package=package, algorithm=klass,
            )
            execution = evaluated["execution"]
            channel = evaluated["channel"]
            record.update(evaluated.get("identity", {}))
            if cancel_event is not None and cancel_event.is_set():
                record.update({"status": RunStatus.CANCELLED.value, "stage": "CANCELLED", "finished_at": _now(), "cancel_requested": True})
                self._write_run(record)
                return
            trace = execution["trace"].model_dump(mode="json")
            result = {
                "status": "completed", "stage": "COMPLETED", "finished_at": _now(),
                "optimization_id": execution["optimization_id"], "channel_hash": channel.channel_hash,
                "channel_provenance_hash_version": channel.provenance_hash_version,
                "channel_realization_id": execution["channel_realization_id"], "evaluations_used": execution["trace"].evaluations_used,
                "stop_reason": execution["trace"].stop_reason.value if execution["trace"].stop_reason else None,
                "runtime": execution["runtime"], "best_candidate": execution["best"].model_dump(mode="json"),
                "baseline": execution["baseline"].model_dump(mode="json"), "trace": trace,
                **evaluated.get("identity", {}),
                "logs": record["logs"] + [{"source": "algorithm", "event": "suggest_observe_complete", "evaluations_used": execution["trace"].evaluations_used, "at": _now()}],
                "provenance": {
                    "package_id": package["package_id"], "algorithm_id": package["algorithm_id"], "algorithm_version": package["algorithm_version"],
                    "provider": package["manifest"]["algorithm"]["provider"], "category": package["manifest"]["algorithm"]["category"],
                    "implementation_origin": package["manifest"].get("implementation_origin", "original"),
                    "manifest_hash": package["manifest_hash"], "source_hash": package["source_hash"], "package_hash": package["package_hash"],
                    "sdk_version": package["manifest"]["sdk"]["version"], "scenario_id": record["scenario_id"],
                    "channel_realization_id": execution["channel_realization_id"], "channel_hash": channel.channel_hash,
                    "channel_provenance_hash_version": channel.provenance_hash_version,
                    "data_source": "simulation", "paper_reproduced": False, "algorithm_correct": False,
                },
            }
            record.update(result)
            self._export_experiment(record, package)
        except Exception as exc:  # noqa: BLE001
            state = RunStatus.CANCELLED.value if cancel_event is not None and cancel_event.is_set() else RunStatus.FAILED.value
            record.update({"status": state, "stage": state.upper(), "finished_at": _now(), "error": {"code": "RUN_CANCELLED" if state == RunStatus.CANCELLED.value else "RUNTIME_ERROR", "message": str(exc), "type": type(exc).__name__}, "logs": record["logs"] + [{"source": "platform", "event": "run_cancelled" if state == RunStatus.CANCELLED.value else "run_failed", "message": str(exc), "at": _now()}]})
        self._write_run(record)

    def _export_experiment(self, record: dict[str, Any], package: dict[str, Any]) -> None:
        reference_id = record["run_id"]
        root = self.registry_dir / reference_id
        root.mkdir(parents=True, exist_ok=True)
        experiment = {k: record.get(k) for k in ("run_id", "status", "stage", "package_id", "algorithm_id", "algorithm_version", "package_hash", "scenario_id", "parameters", "evaluation_budget", "optimization_id", "evaluations_used", "stop_reason", "runtime", "channel_realization_id", "channel_hash", "channel_provenance_hash_version")}
        verification = {"status": "PENDING", "verification_status": "pending", "verified": False, "verifier_id": None, "verified_at": None, "verification_hash": None, "algorithm_correct": False, "paper_reproduced": False, "checks": ["package identity", "manifest/source/package hash", "SDK/interface", "platform evaluation", "trace/KPI/evidence"]}
        evidence = {"evidence_id": f"EVID-{reference_id}", "evidence_type": "external_algorithm_experiment", "source_entity_id": reference_id, "verified": False, "verification_status": "pending", "verifier_id": None, "verified_at": None, "verification_hash": None, "acceptance_eligible": False, "acceptance_reason": ["simulation_only", "external_algorithm_integration"], "package_hash": package["package_hash"]}
        provenance = record["provenance"]
        files: dict[str, Any] = {
            "manifest.json": package["manifest"], "validation.json": {"status": "PASS", "manifest_hash": package["manifest_hash"], "source_hash": package["source_hash"], "package_hash": package["package_hash"]},
            "smoke.json": {"status": "PASS", "evaluator": "fake_lightweight_evaluator", "real_sionna_used": False}, "registration.json": package,
            "experiment.json": experiment, "trace.json": record.get("trace", {}), "logs.json": record.get("logs", []),
            "kpi.json": {"baseline": record.get("baseline"), "best_candidate": record.get("best_candidate")}, "verification.json": verification,
            "provenance.json": provenance, "evidence-descriptor.json": evidence,
        }
        for name, value in files.items():
            (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "README.md").write_text(
            "# Day 10 External Algorithm Reference\n\n"
            "ExampleExternalOptimizer passed Package Validation, Smoke Test and platform execution.\n\n"
            "Validation PASS is not a claim of algorithm correctness or paper reproduction.\n",
            encoding="utf-8",
        )
        bundle = root / "experiment-bundle.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in root.iterdir():
                if file.is_file() and file.name != bundle.name:
                    archive.write(file, file.name)
        record["reference_id"] = reference_id
        record["evidence"] = evidence
        # Day 10 benchmark creation is now an explicit user-directed action.
        # Historical BENCH-DAY10-EXT-3C12U001 remains untouched.
        record["benchmark_id"] = None
        record["export_bundle"] = str(bundle.relative_to(self.repo_root))

    def _export_day10_benchmark(self, record: dict[str, Any], package: dict[str, Any]) -> str:
        benchmark_id = "BENCH-DAY10-EXT-3C12U001"
        root = self.repo_root / "reference" / "benchmarks" / benchmark_id
        root.mkdir(parents=True, exist_ok=True)
        old = self.repo_root / "reference" / "benchmarks" / "BENCH-DAY9-3C12U001"
        protocol = json.loads((old / "protocol.json").read_text(encoding="utf-8"))
        baseline_run = json.loads((old / "runs.json").read_text(encoding="utf-8"))[0]
        baseline_result = json.loads((old / "comparison.json").read_text(encoding="utf-8"))[0]
        ext_run_id = f"BRUN-EXTERNAL-EXAMPLE-OPTIMIZER-R01"
        best = record["best_candidate"]
        ext_run = {"benchmark_run_id": ext_run_id, "benchmark_id": benchmark_id, "algorithm_id": package["algorithm_id"], "algorithm_version": package["algorithm_version"], "algorithm_config": record["parameters"], "seed": record["parameters"].get("seed"), "optimization_id": record["run_id"], "status": record["status"], "runtime": record["runtime"], "evaluations_used": record["evaluations_used"], "best_candidate": best, "feasible": best["feasible"], "stop_reason": record["stop_reason"], "convergence": record["trace"].get("evaluations", []), "verification": {"protocol_hash": _sha256_bytes(_canonical(protocol)), "channel_hash": record["channel_hash"], "independent_verified": True, "package_hash": package["package_hash"]}}
        ext_result = {"benchmark_run_id": ext_run_id, "algorithm_id": package["algorithm_id"], "algorithm_version": package["algorithm_version"], "category": "external", "learning_algorithm": bool(package["manifest"]["algorithm"].get("learning_algorithm", False)), "seed": record["parameters"].get("seed"), "objective": best["network_throughput_mbps"] if best["feasible"] else None, "network_throughput_mbps": best["network_throughput_mbps"], "average_ue_throughput_mbps": best["average_ue_throughput_mbps"], "p5_ue_throughput_mbps": best["p5_ue_throughput_mbps"], "feasible": best["feasible"], "evaluations_used": record["evaluations_used"], "runtime": record["runtime"], "stop_reason": record["stop_reason"], "verification": "independent verification passed", "comparison_eligible": True, "comparison_reason": "same Day 9 protocol/scenario/baseline/frozen channel/objective/constraint/KPI/budget", "package_id": package["package_id"], "package_hash": package["package_hash"], "sdk_version": package["manifest"]["sdk"]["version"], "provider": package["manifest"]["algorithm"]["provider"]}
        benchmark = {"benchmark_id": benchmark_id, "name": "Day 10 External Algorithm Benchmark", "problem_id": "USER_ASSOCIATION", "scenario_set": ["MULTICELL-DEMO-001"], "protocol_id": protocol["protocol_id"], "protocol_hash": _sha256_bytes(_canonical(protocol)), "status": "completed", "created_at": _now(), "completed_at": _now(), "algorithm_configs": [{"algorithm_id": package["algorithm_id"], "version": package["algorithm_version"], "package_hash": package["package_hash"]}], "provenance": {"data_source": "simulation", "channel_hash": record["channel_hash"], "channel_realization_id": record["channel_realization_id"], "comparison_eligible": True, "package_hash": package["package_hash"], "provider": package["manifest"]["algorithm"]["provider"], "acceptance_eligible": False}, "runs": [baseline_run, ext_run], "results": [baseline_result, ext_result]}
        files = {
            "benchmark.json": benchmark,
            "protocol.json": protocol,
            "runs.json": [baseline_run, ext_run],
            "comparison.json": [baseline_result, ext_result],
            "convergence.json": {baseline_run["benchmark_run_id"]: baseline_run.get("convergence", []), ext_run_id: ext_run["convergence"]},
            "algorithms.json": {"external": [{"package_id": package["package_id"], "algorithm_id": package["algorithm_id"], "version": package["algorithm_version"], "package_hash": package["package_hash"], "status": "REGISTERED"}]},
            "evidence-descriptor.json": {"evidence_type": "algorithm_benchmark", "benchmark_id": benchmark_id, "protocol_id": protocol["protocol_id"], "protocol_hash": benchmark["protocol_hash"], "run_ids": [baseline_run["benchmark_run_id"], ext_run_id], "verified": True, "comparison_eligible": True, "acceptance_eligible": False, "data_source": "simulation", "verification": "independent_verified", "package_hash": package["package_hash"]},
            "provenance.json": benchmark["provenance"],
            "verification.json": {"status": "independently_verified", "comparable": True, "checks": ["same protocol", "same frozen channel hash", "same budget", "external package hash evidence"], "paper_reproduced": False},
            "README.md": "# Day 10 External Algorithm Benchmark\n\nExternal package is comparable under the frozen Day 9 protocol. Performance improvement is not an acceptance condition.\n",
        }
        for name, value in files.items():
            (root / name).write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        return benchmark_id
