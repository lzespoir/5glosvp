"""
算法—问题兼容性 / Algorithm–problem compatibility.

运行前检查参数类型、参数数量、约束、目标数量、问题类型、超参数与评价预算；
不支持时明确拒绝（例如 Grid Search + 无候选值的连续参数），绝不偷偷离散化，也不运行到一半才失败。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from optimization.parameters import ParameterType

from .sdk import (
    Algorithm,
    AlgorithmMetadata,
    AlgorithmProblem,
    CompatibilityCode,
    CompatibilityIssue,
    HyperparameterValue,
)


class CompatibilityReport(BaseModel):
    algorithm_id: str
    compatible: bool
    errors: list[CompatibilityIssue]
    warnings: list[str]
    resolved_hyperparameters: dict[str, HyperparameterValue] | None = None


def resolve_hyperparameters(
    metadata: AlgorithmMetadata, values: dict[str, Any]
) -> tuple[dict[str, HyperparameterValue], list[CompatibilityIssue]]:
    """未提供的超参数取推荐默认值；未知键与非法值都报告为 INVALID_HYPERPARAMETER。"""
    schema = {h.id: h for h in metadata.hyperparameter_schema}
    issues = [
        CompatibilityIssue(code=CompatibilityCode.INVALID_HYPERPARAMETER,
                           message=f"Unknown hyperparameter '{k}' for {metadata.algorithm_id}. "
                                   f"Known: {', '.join(schema) or '-'}")
        for k in values if k not in schema
    ]
    resolved: dict[str, HyperparameterValue] = {}
    for hid, definition in schema.items():
        try:
            resolved[hid] = definition.validate_value(values[hid]) if hid in values else definition.default
        except ValueError as e:
            issues.append(CompatibilityIssue(code=CompatibilityCode.INVALID_HYPERPARAMETER, message=str(e)))
    return resolved, issues


def _type_message(metadata: AlgorithmMetadata, parameter_id: str, ptype: ParameterType) -> str:
    supported = ", ".join(t.value for t in metadata.supported_parameter_types) or "-"
    if ptype is ParameterType.CONTINUOUS and metadata.capabilities.supports_discrete:
        return (f"{metadata.name_en} requires discrete candidate values; continuous parameter '{parameter_id}' "
                f"has none (supported: {supported}).")
    return f"{metadata.name_en} does not support {ptype.value} parameter '{parameter_id}' (supported: {supported})."


def check_compatibility(
    algorithm: Algorithm,
    problem: AlgorithmProblem,
    hyperparameters: dict[str, Any],
    max_evaluations_limit: int,
) -> CompatibilityReport:
    metadata = algorithm.metadata()
    caps = metadata.capabilities
    errors: list[CompatibilityIssue] = []
    warnings: list[str] = []

    if problem.problem_type not in metadata.supported_problem_types:
        errors.append(CompatibilityIssue(
            code=CompatibilityCode.ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED,
            message=f"{metadata.name_en} does not support '{problem.problem_type}' problems "
                    f"(supported: {', '.join(metadata.supported_problem_types)}).",
        ))
    supported_types = set(metadata.supported_parameter_types)
    for p in problem.parameter_space.parameters:
        if p.type not in supported_types:
            errors.append(CompatibilityIssue(code=CompatibilityCode.ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED,
                                             message=_type_message(metadata, p.id, p.type), parameter_id=p.id))
    n_params = len(problem.parameter_space.parameters)
    if caps.max_parameters is not None and n_params > caps.max_parameters:
        errors.append(CompatibilityIssue(
            code=CompatibilityCode.ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED,
            message=f"{metadata.name_en} supports at most {caps.max_parameters} parameter(s), got {n_params}.",
        ))
    if problem.parameter_space.constraints and not caps.supports_constraints:
        errors.append(CompatibilityIssue(
            code=CompatibilityCode.ALGORITHM_CONSTRAINTS_NOT_SUPPORTED,
            message=f"{metadata.name_en} does not support parameter-space constraints.",
        ))
    if problem.objective_count > 1 and not caps.supports_multi_objective:
        errors.append(CompatibilityIssue(
            code=CompatibilityCode.ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED,
            message=f"{metadata.name_en} supports a single objective only.",
        ))
    if not 1 <= problem.max_evaluations <= max_evaluations_limit:
        errors.append(CompatibilityIssue(
            code=CompatibilityCode.INVALID_EVALUATION_BUDGET,
            message=f"max_evaluations must be within [1, {max_evaluations_limit}], got {problem.max_evaluations}.",
        ))

    resolved, hp_issues = resolve_hyperparameters(metadata, hyperparameters)
    errors.extend(hp_issues)
    if not errors:
        errors.extend(algorithm.validate_problem(problem, resolved))

    discrete = [p for p in problem.parameter_space.parameters if p.type is ParameterType.DISCRETE and p.choices]
    if not errors and not caps.supports_iterative_feedback and len(discrete) == n_params:
        grid = 1
        for p in discrete:
            grid *= len(p.choices or [])
        if problem.max_evaluations < grid:
            warnings.append(f"Evaluation budget {problem.max_evaluations} < {grid} candidates: "
                            "the search will stop with budget_exhausted.")
    return CompatibilityReport(
        algorithm_id=metadata.algorithm_id,
        compatible=not errors,
        errors=errors,
        warnings=warnings,
        resolved_hyperparameters=resolved if not errors else None,
    )
