"""
参数空间 / Parameter space.

一个优化问题可以有 1 个或上千个参数；数据结构不假设单参数。
所有参数都是网络优化变量（role = optimization_variable），算法超参数另有 schema。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from optimization.parameters import ParameterDefinition, ParameterRole, ParameterValue


class ParameterConstraint(BaseModel):
    """跨参数约束（声明式；Day 7 只保存与展示，不求解）。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    expression: str
    description: str = ""


class ParameterSpace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameters: list[ParameterDefinition] = Field(min_length=1)
    constraints: list[ParameterConstraint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> ParameterSpace:
        ids = [p.id for p in self.parameters]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate parameter ids: {ids}")
        wrong = [p.id for p in self.parameters if p.role is not ParameterRole.OPTIMIZATION_VARIABLE]
        if wrong:
            raise ValueError(f"parameter space may only contain optimization variables, got {wrong}")
        return self

    @property
    def ids(self) -> list[str]:
        return [p.id for p in self.parameters]

    def get(self, parameter_id: str) -> ParameterDefinition:
        for p in self.parameters:
            if p.id == parameter_id:
                return p
        raise KeyError(parameter_id)

    def validate_point(self, point: dict[str, Any]) -> dict[str, ParameterValue]:
        """候选配置必须恰好覆盖全部参数且每个值合法；返回规范化值，否则抛出 ValueError。"""
        missing = [i for i in self.ids if i not in point]
        extra = [k for k in point if k not in self.ids]
        if missing or extra:
            raise ValueError(f"candidate must set exactly {self.ids} (missing {missing}, unexpected {extra})")
        return {p.id: p.validate_value(point[p.id]) for p in self.parameters}

    def sha256(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_sha256(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
