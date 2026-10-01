from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from xml.etree import ElementTree

from antenna import AMatrixAdapter, AMatrixDataError

from scenarios.combination import canonical_hash, scenario_from_dimensions
from scenarios.taxonomy import TAXONOMY

from .models import (
    AntennaDefinition, Capability, CellDefinition, ConfiguredScenario, CoordinateReference,
    EnvironmentAsset, EnvironmentDefinition, MapLayer, Parameter, Position, ScenarioInstance,
    SiteDefinition, UEDefinition, ValidationIssue, ValidationResult,
    ProvenanceLink, WorkspaceProvenanceChain,
)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def file_digest(path: Path) -> str:
    digestor = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digestor.update(chunk)
    return digestor.hexdigest()


def definition_digest(scenario: ConfiguredScenario) -> str:
    payload = scenario.model_dump(mode="json", exclude={"state", "version", "definition_hash", "created_at", "updated_at", "lineage", "pre_archive_state", "archived_at", "archived_source", "restored_at", "restored_source"})
    return digest(payload)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NetworkImporter(Protocol):
    """Contract for future network imports; no file format is parsed in Day15."""

    supported_formats: tuple[str, ...]

    def import_network(
        self, path: Path, coordinate: CoordinateReference
    ) -> tuple[list[SiteDefinition], list[CellDefinition]]: ...


class WorkspaceStore:
    """Atomic JSON store. IDs are never used directly as file names."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self._lock = threading.RLock()

    def _path(self, collection: str, key: str) -> Path:
        if collection not in {"scenarios", "assets", "instances"}:
            raise ValueError("invalid collection")
        return self.root / collection / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    def read(self, collection: str, key: str) -> dict[str, Any]:
        path = self._path(collection, key)
        if not path.is_file():
            raise KeyError(key)
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, collection: str, key: str, payload: dict[str, Any]) -> None:
        path = self._path(collection, key)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".workspace-", suffix=".json", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def delete(self, collection: str, key: str) -> None:
        path = self._path(collection, key)
        with self._lock:
            if not path.is_file():
                raise KeyError(key)
            path.unlink()

    def all(self, collection: str) -> list[dict[str, Any]]:
        directory = self.root / collection
        if not directory.is_dir():
            return []
        return [json.loads(path.read_text(encoding="utf-8")) for path in directory.glob("*.json")]


class ScenarioValidator:
    def __init__(self, antenna_adapter: AMatrixAdapter | None = None):
        self.antenna_adapter = antenna_adapter or AMatrixAdapter()

    def validate(self, scenario: ConfiguredScenario, assets: dict[str, EnvironmentAsset]) -> ValidationResult:
        issues: list[ValidationIssue] = []

        def add(severity: str, code: str, path: str, message: str):
            issues.append(ValidationIssue(severity=severity, code=code, path=path, message=message))

        environment = scenario.environment
        if environment is None:
            add("ERROR", "ENVIRONMENT_MISSING", "environment", "请配置环境")
        else:
            if environment.asset_id and environment.asset_id not in assets:
                add("ERROR", "ENVIRONMENT_ASSET_UNKNOWN", "environment.asset_id", "环境资产未注册")
            if environment.asset_id in assets:
                asset = assets[environment.asset_id]
                if environment.asset_sha256 != asset.sha256:
                    add("ERROR", "ASSET_HASH_MISMATCH", "environment.asset_sha256", "环境资产 hash 与登记记录不一致")
                if asset.coordinate.status == "UNKNOWN":
                    add("ERROR", "ASSET_COORDINATE_UNKNOWN", "environment.asset_id", "环境资产坐标语义未确认")
                if asset.coordinate.coordinate_system != environment.coordinate.coordinate_system or asset.coordinate.unit != environment.coordinate.unit:
                    add("ERROR", "ASSET_COORDINATE_MISMATCH", "environment.coordinate", "场景与环境资产坐标语义不一致")
            if environment.coordinate.status == "UNKNOWN" or environment.coordinate.unit == "UNKNOWN":
                add("ERROR", "COORDINATE_UNKNOWN", "environment.coordinate", "坐标空间或单位未确认")
        if not scenario.sites:
            add("ERROR", "SITE_MISSING", "sites", "请添加站点")
        if not scenario.cells:
            add("ERROR", "CELL_MISSING", "cells", "请添加小区")
        if environment:
            layer_ids = [layer.layer_id for layer in environment.layers]
            layer_keys = [(layer.kind, layer.source_asset_id) for layer in environment.layers]
            if len(layer_ids) != len(set(layer_ids)) or len(layer_keys) != len(set(layer_keys)):
                add("ERROR", "MAP_LAYER_DUPLICATE", "environment.layers", "图层 ID 或同类型/来源图层重复")
            for index, layer in enumerate(environment.layers):
                if layer.source_asset_id and layer.source_asset_id not in assets:
                    add("ERROR", "MAP_LAYER_ASSET_UNKNOWN", f"environment.layers.{index}.source_asset_id", "图层引用的环境资产未登记")
        site_ids = {site.site_id for site in scenario.sites}
        antenna_ids = {antenna.antenna_definition_id for antenna in scenario.antennas}
        if len(site_ids) != len(scenario.sites):
            add("ERROR", "DUPLICATE_SITE", "sites", "站点 ID 重复")
        if len({cell.cell_id for cell in scenario.cells}) != len(scenario.cells):
            add("ERROR", "DUPLICATE_CELL", "cells", "小区 ID 重复")
        if len(antenna_ids) != len(scenario.antennas):
            add("ERROR", "DUPLICATE_ANTENNA", "antennas", "天线 ID 重复")
        if scenario.antennas:
            try:
                profiles = {item["id"]: item for item in self.antenna_adapter.profiles()}
                manifest = {item.source_family: item for item in self.antenna_adapter.manifest()}
            except AMatrixDataError:
                profiles, manifest = {}, {}
            for index, antenna in enumerate(scenario.antennas):
                path = f"antennas.{index}"
                if antenna.provider_type != "A_MATRIX":
                    if antenna.provider_status == "IMPLEMENTED":
                        add("ERROR", "PROVIDER_STATUS_UNTRUSTED", path, "非 A-Matrix Provider 当前仅有接口契约")
                    continue
                profile = profiles.get(antenna.profile_id or "")
                family = {"spread": "8_BEAM_FAMILY", "phase_power": "7_BEAM_FAMILY"}.get(profile.get("library")) if profile else None
                source = manifest.get(family or "")
                if not profile or not source or antenna.artifact_id != source.artifact_id or antenna.artifact_hash != source.source_hash or antenna.normalization != "PEAK_LINEAR_POWER_TO_RELATIVE" or antenna.calibration_status != "RELATIVE_ONLY" or antenna.beam_count != len(profile.get("beam_ids", [])):
                    add("ERROR", "A_MATRIX_PROVENANCE_MISMATCH", path, "Profile、波束数、artifact/hash 或归一化语义与源数据不一致")
        if len({ue.ue_id for ue in scenario.ues}) != len(scenario.ues):
            add("ERROR", "DUPLICATE_UE", "ues", "UE ID 重复")
        if environment:
            for index, site in enumerate(scenario.sites):
                if site.position.coordinate.coordinate_system != environment.coordinate.coordinate_system or site.position.coordinate.unit != environment.coordinate.unit:
                    add("ERROR", "COORDINATE_MISMATCH", f"sites.{index}.position", "站点坐标与环境不一致")
        for index, cell in enumerate(scenario.cells):
            prefix = f"cells.{index}"
            if cell.site_id not in site_ids:
                add("ERROR", "CELL_SITE_UNKNOWN", prefix + ".site_id", "小区站点不存在")
            if not cell.antenna.antenna_definition_id or cell.antenna.antenna_definition_id not in antenna_ids:
                add("ERROR", "CELL_ANTENNA_UNKNOWN", prefix + ".antenna", "小区天线未绑定或不存在")
            for name in ("carrier_frequency", "bandwidth", "tx_power"):
                parameter = getattr(cell.core, name)
                if parameter.value is None or parameter.unit == "UNKNOWN" or parameter.source == "UNKNOWN":
                    add("ERROR", "CELL_PARAMETER_MISSING", prefix + ".core." + name, "关键无线参数需显式填写单位与来源")
            if cell.position and environment and cell.position.coordinate.coordinate_system != environment.coordinate.coordinate_system:
                add("ERROR", "COORDINATE_MISMATCH", prefix + ".position", "小区坐标与环境不一致")
            if cell.position and environment and cell.position.coordinate.unit != environment.coordinate.unit:
                add("ERROR", "COORDINATE_MISMATCH", prefix + ".position", "小区坐标单位与环境不一致")
            for name in ("azimuth", "mechanical_tilt", "electrical_tilt", "antenna_height"):
                parameter = getattr(cell.core, name)
                if parameter.value is None or parameter.unit == "UNKNOWN" or parameter.source == "UNKNOWN":
                    add("WARNING", "CELL_PARAMETER_UNSPECIFIED", prefix + ".core." + name, "该小区参数未声明；不会从默认值推断")
        if not scenario.ues:
            add("ERROR", "UE_MISSING", "ues", "请添加 UE")
        for index, ue in enumerate(scenario.ues):
            if ue.mobility == "UNKNOWN":
                add("ERROR", "UE_MOBILITY_UNSPECIFIED", f"ues.{index}.mobility", "请明确声明 UE 移动性")
            elif ue.mobility != "STATIC":
                add("WARNING", "UE_MOBILITY_NOT_IMPLEMENTED", f"ues.{index}.mobility", "当前仅支持静态 UE 几何配置")
            if ue.traffic_profile == "UNKNOWN":
                add("ERROR", "UE_TRAFFIC_PROFILE_UNSPECIFIED", f"ues.{index}.traffic_profile", "请明确声明 UE 业务 profile")
            elif ue.traffic_profile != "full_buffer":
                add("WARNING", "UE_TRAFFIC_PROFILE_NOT_IMPLEMENTED", f"ues.{index}.traffic_profile", "当前 UE 业务 profile 未接入执行")
            if not ue.position:
                add("ERROR", "UE_POSITION_MISSING", f"ues.{index}.position", "UE 缺少位置")
            if ue.serving_cell_id and ue.serving_cell_id not in {cell.cell_id for cell in scenario.cells}:
                add("ERROR", "UE_CELL_UNKNOWN", f"ues.{index}.serving_cell_id", "UE 关联小区不存在")
            if ue.position and environment and ue.position.coordinate.coordinate_system != environment.coordinate.coordinate_system:
                add("ERROR", "COORDINATE_MISMATCH", f"ues.{index}.position", "UE 坐标与环境不一致")
        if scenario.traffic.kind == "UNKNOWN" or scenario.traffic.source == "UNKNOWN":
            add("ERROR", "TRAFFIC_UNSPECIFIED", "traffic", "请显式选择业务模型")
        elif scenario.traffic.availability != "AVAILABLE":
            add("ERROR", "TRAFFIC_UNAVAILABLE", "traffic", "该业务模型当前不可执行")
        if scenario.radio.backend == "UNKNOWN" or scenario.radio.source == "UNKNOWN":
            add("ERROR", "RADIO_BACKEND_UNSPECIFIED", "radio", "请显式声明无线后端及来源")
        elif scenario.radio.status != "REGISTERED":
            add("WARNING", "RADIO_BACKEND_NOT_REGISTERED", "radio", "所选无线模型尚未在当前平台注册")
        if scenario.radio.status == "REGISTERED" and (scenario.radio.version == "UNKNOWN" or scenario.radio.calibration_status == "UNKNOWN"):
            add("ERROR", "RADIO_MODEL_PROVENANCE_INCOMPLETE", "radio", "已注册无线模型必须显式携带版本与校准状态")
        if not scenario.optimization_problems:
            add("ERROR", "PROBLEM_MISSING", "optimization_problems", "请选择优化问题")
        if any(a.provider_status != "IMPLEMENTED" for a in scenario.antennas):
            add("WARNING", "ANTENNA_CONTRACT_ONLY", "antennas", "存在未实现的天线 Provider")
        valid = not any(issue.severity == "ERROR" for issue in issues)
        asset_backend_ready = True
        if environment and environment.asset_id in assets:
            asset_backend_ready = scenario.radio.backend in assets[environment.asset_id].supported_backends
        provider_ready = all(a.provider_status == "IMPLEMENTED" and scenario.radio.backend in a.supported_backends for a in scenario.antennas)
        if valid and not (asset_backend_ready and provider_ready):
            add("WARNING", "BACKEND_INCOMPATIBLE", "radio.backend", "环境资产或天线与无线后端不兼容")
        if valid:
            add("WARNING", "EXECUTION_ADAPTER_NOT_IMPLEMENTED", "radio.backend", "Day15 配置尚未接入真实实验执行器；可以冻结定义，不能声称已可运行")
        return ValidationResult(issues=issues, config_valid=valid, simulation_ready=False, state="VALID" if valid else "INVALID")


class ScenarioReferenced(ValueError):
    def __init__(self, scenario_id: str, reference_summary: dict[str, int]):
        super().__init__("SCENARIO_REFERENCED")
        self.scenario_id = scenario_id
        self.reference_summary = reference_summary


class ScenarioReferenceGuard:
    """Extensible registry of authoritative references; never cascades deletion."""

    def __init__(self, store: WorkspaceStore):
        self.store = store
        self._providers = {"scenario_instances": self._scenario_instances}

    def _scenario_instances(self, scenario_id: str) -> int:
        return sum(row.get("scenario_id") == scenario_id for row in self.store.all("instances"))

    def register_provider(self, name: str, provider) -> None:
        if not name or name in self._providers:
            raise ValueError("REFERENCE_PROVIDER_INVALID")
        self._providers[name] = provider

    def reference_summary(self, scenario_id: str) -> dict[str, int]:
        return {name: int(provider(scenario_id)) for name, provider in self._providers.items()}


class WorkspaceService:
    def __init__(self, root: Path | str):
        self.store = WorkspaceStore(root)
        self.validator = ScenarioValidator()
        self.reference_guard = ScenarioReferenceGuard(self.store)

    def assets(self) -> list[EnvironmentAsset]:
        return [EnvironmentAsset.model_validate(row) for row in self.store.all("assets")]

    def register_asset(self, *, name: str, asset_type: str, source_path: str | None = None, coordinate: CoordinateReference | None = None) -> EnvironmentAsset:
        if not source_path:
            raise ValueError("ASSET_PATH_REQUIRED")
        metadata: dict[str, Any] = {}
        size = None
        checksum = None
        if source_path:
            path = Path(source_path).resolve(strict=True)
            if not path.is_file():
                raise ValueError("ASSET_NOT_FILE")
            configured_roots = os.environ.get("GLOSVP_ASSET_ROOTS", "")
            allowed_roots = [Path(item).resolve() for item in configured_roots.split(os.pathsep) if item] if configured_roots else [(self.store.root.parent / "assets").resolve()]
            if not any(path.is_relative_to(root) for root in allowed_roots):
                raise ValueError("ASSET_OUTSIDE_ALLOWED_ROOTS")
            if path.stat().st_size > 2 * 1024 ** 3:
                raise ValueError("ASSET_TOO_LARGE")
            extensions = {"GLTF": {".gltf", ".glb"}, "OSM": {".osm", ".xml"}, "GEOJSON": {".geojson", ".json"}}
            if asset_type in extensions and path.suffix.lower() not in extensions[asset_type]:
                raise ValueError("ASSET_FORMAT_MISMATCH")
            size = path.stat().st_size
            checksum = file_digest(path)
            if asset_type == "GLTF" and path.suffix.lower() == ".gltf" and size <= 64 * 1024 ** 2:
                obj = json.loads(path.read_text(encoding="utf-8"))
                metadata = {"asset_version": obj.get("asset", {}).get("version"), "scene_count": len(obj.get("scenes", [])), "node_count": len(obj.get("nodes", [])), "mesh_count": len(obj.get("meshes", []))}
            elif asset_type == "GLTF":
                with path.open("rb") as handle:
                    metadata = {"glb_magic": handle.read(4).decode("ascii", errors="replace")}
            elif asset_type == "OSM":
                for _, element in ElementTree.iterparse(path, events=("start",)):
                    metadata = {"root_tag": element.tag, "version": element.attrib.get("version")}
                    break
        asset = EnvironmentAsset(asset_id="ENV-ASSET-" + uuid.uuid4().hex[:10].upper(), name=name, asset_type=asset_type, source_path=str(Path(source_path).resolve()) if source_path else None, size_bytes=size, sha256=checksum, metadata=metadata, coordinate=coordinate or CoordinateReference(), supported_backends=[], conversion_status="NOT_CONVERTED")
        self.store.write("assets", asset.asset_id, asset.model_dump(mode="json"))
        return asset

    def get(self, scenario_id: str) -> ConfiguredScenario:
        return ConfiguredScenario.model_validate(self.store.read("scenarios", scenario_id))

    def list(self, *, offset: int = 0, limit: int = 20, search: str = "", family: str = "", state: str = "", problem: str = "", environment: str = "", traffic: str = "", source: str = "") -> dict[str, Any]:
        items = [ConfiguredScenario.model_validate(row) for row in self.store.all("scenarios")]
        items = [row for row in items if (row.state == "ARCHIVED" if state == "ARCHIVED" else row.state != "ARCHIVED" and (not state or state == "ACTIVE" or row.state == state)) and (not search or search.lower() in (row.name + row.scenario_id).lower()) and (not family or row.family == family) and (not problem or problem in row.optimization_problems) and (not environment or row.environment and row.environment.environment_id == environment) and (not traffic or row.traffic.kind == traffic) and (not source or row.source == source)]
        items.sort(key=lambda row: (row.updated_at, row.scenario_id), reverse=True)
        return {"items": items[offset:offset + limit], "total": len(items), "offset": offset, "limit": limit}

    def counts(self) -> dict[str, int]:
        rows = [ConfiguredScenario.model_validate(row) for row in self.store.all("scenarios")]
        active = [row for row in rows if row.state != "ARCHIVED"]
        return {"configured_scenario_count": len(active), "runnable_scenario_count": sum(row.state == "READY" for row in active), "executed_scenario_count": 0, "experiment_verified_count": 0, "acceptance_evidence_count": 0}

    def coverage(self) -> dict[str, Any]:
        """Coverage is derived only from saved, non-archived workspace definitions."""
        active = [ConfiguredScenario.model_validate(row) for row in self.store.all("scenarios") if row.get("state") != "ARCHIVED"]
        families = sorted({row.family for row in active})
        problems = ["NETWORK_STRUCTURE", "USER_ACCESS", "SYSTEM_RESOURCE"]
        matrix = [
            {"family": family, "problem_type": problem, "configured_count": sum(family == row.family and problem in row.optimization_problems for row in active)}
            for family in families for problem in problems
        ]
        return {
            "source": "PERSISTED_CONFIGURED_SCENARIOS",
            "configured_scenario_count": len(active),
            "family_counts": {family: sum(row.family == family for row in active) for family in families},
            "problem_counts": {problem: sum(problem in row.optimization_problems for row in active) for problem in problems},
            "matrix": matrix,
        }

    def create(self, name: str, family: str = "custom", candidate_hash: str | None = None) -> ConfiguredScenario:
        if not name.strip():
            raise ValueError("SCENARIO_NAME_REQUIRED")
        if candidate_hash and any(row.candidate_hash == candidate_hash for row in [ConfiguredScenario.model_validate(item) for item in self.store.all("scenarios")]):
            raise ValueError("CANDIDATE_ALREADY_CONFIGURED")
        now = utc_now()
        scenario = ConfiguredScenario(scenario_id="SCN-D15-" + uuid.uuid4().hex[:10].upper(), name=name.strip(), family=family, candidate_hash=candidate_hash, created_at=now, updated_at=now)
        scenario.definition_hash = definition_digest(scenario)
        self.store.write("scenarios", scenario.scenario_id, scenario.model_dump(mode="json"))
        return scenario

    def from_candidate(self, dimensions: dict[str, str]) -> ConfiguredScenario:
        if set(dimensions) != {dimension.key for dimension in TAXONOMY.dimensions}:
            raise ValueError("CANDIDATE_DIMENSIONS_INCOMPLETE")
        for dimension in TAXONOMY.dimensions:
            if dimensions[dimension.key] not in {option.value for option in dimension.options}:
                raise ValueError("CANDIDATE_DIMENSION_UNKNOWN")
        candidate = scenario_from_dimensions(dimensions)
        if candidate.compatibility_status == "INVALID_COMBINATION":
            raise ValueError("CANDIDATE_COMBINATION_INVALID")
        candidate_id = "CAND-" + candidate.scenario_definition_hash[:16].upper()
        return self.promote_candidate(candidate_id, dimensions)

    def promote_candidate(self, candidate_id: str, dimensions: dict[str, str]) -> ConfiguredScenario:
        if set(dimensions) != {dimension.key for dimension in TAXONOMY.dimensions}:
            raise ValueError("CANDIDATE_DIMENSIONS_INCOMPLETE")
        for dimension in TAXONOMY.dimensions:
            if dimensions[dimension.key] not in {option.value for option in dimension.options}:
                raise ValueError("CANDIDATE_DIMENSION_UNKNOWN")
        candidate = scenario_from_dimensions(dimensions)
        if candidate.compatibility_status == "INVALID_COMBINATION":
            raise ValueError("CANDIDATE_COMBINATION_INVALID")
        expected_id = "CAND-" + candidate.scenario_definition_hash[:16].upper()
        if candidate_id != expected_id:
            raise ValueError("CANDIDATE_IDENTITY_MISMATCH")
        if any(ConfiguredScenario.model_validate(item).candidate_hash == candidate.scenario_definition_hash for item in self.store.all("scenarios")):
            raise ValueError("CANDIDATE_ALREADY_CONFIGURED")
        now = utc_now()
        scenario = ConfiguredScenario(
            scenario_id="SCN-D15-" + uuid.uuid4().hex[:10].upper(),
            name=candidate.name_zh,
            family=candidate.scenario_family,
            classification=dict(dimensions),
            optimization_problems=list(candidate.supported_problem_types),
            candidate_hash=candidate.scenario_definition_hash,
            source="CANDIDATE_PROMOTED",
            state="DRAFT",
            created_at=now,
            updated_at=now,
            lineage={"candidate_id": candidate_id, "candidate_hash": candidate.scenario_definition_hash, "taxonomy_version": candidate.taxonomy_version, "dimensions": dict(dimensions), "status": "PROMOTED_DRAFT_NOT_NETWORK_CONFIGURATION"},
        )
        scenario.definition_hash = definition_digest(scenario)
        self.store.write("scenarios", scenario.scenario_id, scenario.model_dump(mode="json"))
        return scenario

    def save(self, scenario: ConfiguredScenario) -> ConfiguredScenario:
        current = self.get(scenario.scenario_id)
        if current.state == "ARCHIVED":
            raise ValueError("SCENARIO_ARCHIVED")
        if scenario.version != current.version:
            raise ValueError("SCENARIO_VERSION_CONFLICT")
        scenario = scenario.model_copy(deep=True)
        if scenario.environment and scenario.environment.asset_id:
            asset = EnvironmentAsset.model_validate(self.store.read("assets", scenario.environment.asset_id))
            scenario.environment.asset_sha256 = asset.sha256
        if definition_digest(scenario) == current.definition_hash:
            return current
        scenario.created_at = current.created_at
        scenario.version = current.version + 1
        scenario.updated_at = utc_now()
        scenario.definition_hash = definition_digest(scenario)
        scenario.state = self.validate(scenario).state
        self.store.write("scenarios", scenario.scenario_id, scenario.model_dump(mode="json"))
        return scenario

    def clone(self, scenario_id: str) -> ConfiguredScenario:
        source = self.get(scenario_id)
        clone = source.model_copy(deep=True)
        clone.scenario_id = "SCN-D15-" + uuid.uuid4().hex[:10].upper()
        clone.name = source.name + "（副本）"
        clone.version = 1
        clone.state = "DRAFT"
        clone.source = "CLONED_VARIANT"
        clone.candidate_hash = None
        clone.lineage = {"cloned_from": scenario_id, "source_version": source.version, "source_hash": source.definition_hash}
        clone.created_at = clone.updated_at = utc_now()
        clone.definition_hash = definition_digest(clone)
        self.store.write("scenarios", clone.scenario_id, clone.model_dump(mode="json"))
        return clone

    def archive(self, scenario_id: str) -> ConfiguredScenario:
        scenario = self.get(scenario_id)
        if scenario.state == "ARCHIVED":
            return scenario
        scenario.pre_archive_state = scenario.state
        scenario.state = "ARCHIVED"
        scenario.archived_at = utc_now()
        scenario.archived_source = "API"
        scenario.restored_at = None
        scenario.restored_source = None
        scenario.updated_at = utc_now()
        self.store.write("scenarios", scenario.scenario_id, scenario.model_dump(mode="json"))
        return scenario

    def restore(self, scenario_id: str) -> ConfiguredScenario:
        scenario = self.get(scenario_id)
        if scenario.state != "ARCHIVED":
            raise ValueError("SCENARIO_NOT_ARCHIVED")
        # Older archived records predate lifecycle provenance; DRAFT is the safe fallback.
        scenario.pre_archive_state = scenario.pre_archive_state or "DRAFT"
        scenario.state = scenario.pre_archive_state
        scenario.restored_at = utc_now()
        scenario.restored_source = "API"
        scenario.updated_at = scenario.restored_at
        self.store.write("scenarios", scenario.scenario_id, scenario.model_dump(mode="json"))
        return scenario

    def delete_scenario(self, scenario_id: str) -> dict[str, Any]:
        scenario = self.get(scenario_id)
        if scenario.state not in {"DRAFT", "INVALID", "ARCHIVED"}:
            raise ValueError("SCENARIO_MUST_BE_ARCHIVED")
        reference_summary = self.reference_guard.reference_summary(scenario_id)
        if any(reference_summary.values()):
            raise ScenarioReferenced(scenario_id, reference_summary)
        self.store.delete("scenarios", scenario_id)
        return {"scenario_id": scenario_id, "deleted": True, "cascade_deleted": False}

    def validate(self, scenario: ConfiguredScenario) -> ValidationResult:
        return self.validator.validate(scenario, {asset.asset_id: asset for asset in self.assets()})

    def materialize(self, scenario_id: str, seed: int) -> ScenarioInstance:
        scenario = self.get(scenario_id)
        check = self.validate(scenario)
        if not check.config_valid:
            raise ValueError("SCENARIO_CONFIG_INVALID")
        asset_hashes: dict[str, str] = {}
        if scenario.environment and scenario.environment.asset_id:
            asset = EnvironmentAsset.model_validate(self.store.read("assets", scenario.environment.asset_id))
            source = Path(asset.source_path or "")
            if not source.is_file() or file_digest(source) != asset.sha256:
                raise ValueError("ASSET_SOURCE_CHANGED")
            asset_hashes[asset.asset_id] = asset.sha256 or ""
        identity = {"scenario_id": scenario.scenario_id, "version": scenario.version, "definition_hash": scenario.definition_hash, "asset_hashes": asset_hashes, "seed": seed}
        instance = ScenarioInstance(instance_id="SCI-D15-" + digest(identity)[:12].upper(), scenario_id=scenario.scenario_id, scenario_version=scenario.version, definition_hash=scenario.definition_hash, asset_hashes=asset_hashes, seed=seed, frozen_definition=scenario.model_copy(deep=True), identity_hash=digest(identity), created_at=utc_now())
        self.store.write("instances", instance.instance_id, instance.model_dump(mode="json"))
        return instance

    def get_instance(self, instance_id: str) -> ScenarioInstance:
        return ScenarioInstance.model_validate(self.store.read("instances", instance_id))

    def provenance(self, scenario_id: str) -> WorkspaceProvenanceChain:
        scenario = self.get(scenario_id)
        links: list[ProvenanceLink] = []
        if scenario.environment and scenario.environment.asset_id:
            asset = next((item for item in self.assets() if item.asset_id == scenario.environment.asset_id), None)
            if asset:
                links.append(ProvenanceLink(object_type="ASSET", object_id=asset.asset_id, status=asset.conversion_status, identity_hash=asset.sha256, details={"type": asset.asset_type, "coordinate": asset.coordinate.model_dump(mode="json")}))
        links.append(ProvenanceLink(object_type="DEFINITION", object_id=scenario.scenario_id, status=scenario.state, identity_hash=scenario.definition_hash, details={"version": scenario.version, "source": scenario.source}))
        instances = [ScenarioInstance.model_validate(row) for row in self.store.all("instances") if row.get("scenario_id") == scenario_id]
        for instance in sorted(instances, key=lambda row: row.created_at):
            links.append(ProvenanceLink(object_type="INSTANCE", object_id=instance.instance_id, status=instance.run_status, identity_hash=instance.identity_hash, details={"definition_hash": instance.definition_hash, "asset_hashes": instance.asset_hashes, "seed": instance.seed}))
            links.append(ProvenanceLink(object_type="RUN", object_id=f"RUN-{instance.instance_id}", status="NOT_CONNECTED", details={"reason": "workspace scenario execution adapter is not implemented"}))
        links.append(ProvenanceLink(object_type="OBSERVATION", object_id="OBSERVATIONS-NONE", status="NOT_AVAILABLE", details={"count": 0}))
        links.append(ProvenanceLink(object_type="EVIDENCE", object_id="EVIDENCE-NONE", status="NOT_AVAILABLE", details={"count": 0}))
        return WorkspaceProvenanceChain(scenario_id=scenario_id, links=links)

    def batch_edit_cells(self, scenario_id: str, cell_ids: list[str], updates: dict[str, Parameter], version: int) -> ConfiguredScenario:
        if not cell_ids or not updates or not set(updates).issubset({"carrier_frequency", "bandwidth", "tx_power", "azimuth", "mechanical_tilt", "electrical_tilt", "antenna_height"}):
            raise ValueError("BATCH_EDIT_INVALID")
        scenario = self.get(scenario_id)
        if scenario.version != version or not set(cell_ids).issubset({cell.cell_id for cell in scenario.cells}):
            raise ValueError("BATCH_EDIT_TARGET_OR_VERSION_INVALID")
        for cell in scenario.cells:
            if cell.cell_id in cell_ids:
                for key, value in updates.items():
                    setattr(cell.core, key, value)
                cell.version += 1
        return self.save(scenario)


CAPABILITIES = [
    Capability(capability_id="SCENARIO_SYSTEM", name="场景体系", status="FOUNDATION", implementation_version="D15-0.1", limitations=["Day12 candidate space is separate from configured library"]),
    Capability(capability_id="MULTI_SITE_RADIO", name="多站多小区无线观测", status="IMPLEMENTED", implementation_version="D14-FAST-PROPAGATION-0.1", evidence_refs=["reference/day14/SCN-DAY14-MULTISITE-RADIO"], limitations=["Uncalibrated simulation"]),
    Capability(capability_id="A_MATRIX", name="A-Matrix 天线响应", status="IMPLEMENTED", implementation_version="D13-ANGULAR-GRID-0.1", evidence_refs=["design/DAY13_FINAL_REPORT.md"], limitations=["Relative response only"]),
    Capability(capability_id="UE_TWIN", name="UE Twin 几何", status="IMPLEMENTED", implementation_version="D13-ANGULAR-GRID-0.1", limitations=["Static geometry"]),
    Capability(capability_id="NETWORK_IMPORT", name="网络配置导入", status="NOT_IMPLEMENTED", limitations=["NetworkImporter contract only; no CSV/GeoJSON/vendor parser is enabled"]),
    Capability(capability_id="TRAFFIC", name="业务模型", status="FOUNDATION", limitations=["Full buffer available; prediction and measured traffic unavailable"]),
    Capability(capability_id="HANDOVER", name="切换", status="NOT_IMPLEMENTED"),
    Capability(capability_id="MEASURED_DATA", name="实测数据验证", status="NOT_IMPLEMENTED"),
    Capability(capability_id="LARGE_SCALE", name="千小区物理仿真", status="NOT_IMPLEMENTED"),
    Capability(capability_id="ACCEPTANCE_EVIDENCE", name="验收证据", status="NOT_IMPLEMENTED"),
]

RADIO_MODELS = [
    {"backend": "FAST_PROPAGATION", "version": "D14-FAST-PROPAGATION-0.1", "status": "REGISTERED", "calibration_status": "UNCALIBRATED_SIMULATION", "source": "USER_DEFINED", "limitations": ["Day14 uses an explicit fixed fixture", "Day15 scenario execution adapter is not connected"]},
]
