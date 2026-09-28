"""
参数定义 / Parameter definitions.

同一模型同时描述：
- 网络优化变量（Optimization Variable，例如 scheduler_beta）；
- 算法超参数（Algorithm Hyperparameter，例如 max_iterations）。
两者通过 role 区分，UI 与 API 分开展示。

值域不写死为枚举列表：continuous / integer 参数允许未来算法直接生成任意合法值（例如 0.734），
Grid Search 只是使用 choices 的一种算法。
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

ParameterValue = Union[float, int, str, list[float]]


class ParameterType(str, Enum):
    CONTINUOUS = "continuous"
    INTEGER = "integer"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"
    VECTOR = "vector"


class ParameterRole(str, Enum):
    OPTIMIZATION_VARIABLE = "optimization_variable"
    ALGORITHM_HYPERPARAMETER = "algorithm_hyperparameter"


class ValueGeneration(str, Enum):
    """候选值来源：用户枚举（Grid Search）或算法生成（未来学习优化器）。"""

    ENUMERATED = "enumerated"
    ALGORITHM_GENERATED = "algorithm_generated"


class ParameterBounds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lower: float
    upper: float
    lower_inclusive: bool = True
    upper_inclusive: bool = True

    @model_validator(mode="after")
    def _check(self) -> ParameterBounds:
        if not (math.isfinite(self.lower) and math.isfinite(self.upper)):
            raise ValueError("bounds must be finite")
        if self.lower >= self.upper:
            raise ValueError(f"lower bound {self.lower} must be < upper bound {self.upper}")
        return self

    def contains(self, value: float) -> bool:
        above = value >= self.lower if self.lower_inclusive else value > self.lower
        below = value <= self.upper if self.upper_inclusive else value < self.upper
        return above and below

    def describe(self) -> str:
        left = "[" if self.lower_inclusive else "("
        right = "]" if self.upper_inclusive else ")"
        return f"{left}{self.lower:g}, {self.upper:g}{right}"


class ParameterDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name_zh: str
    name_en: str
    role: ParameterRole
    type: ParameterType
    unit: str = Field(description="物理单位；无量纲参数使用 '1'")
    default: ParameterValue | None = None
    bounds: ParameterBounds | None = None
    choices: list[ParameterValue] | None = None
    vector_length: int | None = Field(default=None, ge=1)
    constraints: list[str] = Field(default_factory=list)
    value_generation: list[ValueGeneration] = Field(default_factory=lambda: [ValueGeneration.ENUMERATED])
    source: str
    description_zh: str = ""
    description_en: str = ""

    @model_validator(mode="after")
    def _check(self) -> ParameterDefinition:
        if self.type in (ParameterType.CONTINUOUS, ParameterType.INTEGER) and self.bounds is None:
            raise ValueError(f"{self.type.value} parameter '{self.id}' requires bounds")
        if self.type is ParameterType.CATEGORICAL and not self.choices:
            raise ValueError(f"categorical parameter '{self.id}' requires choices")
        if self.type is ParameterType.VECTOR and self.vector_length is None:
            raise ValueError(f"vector parameter '{self.id}' requires vector_length")
        for choice in self.choices or []:
            self.validate_value(choice)
        if self.default is not None:
            self.validate_value(self.default)
        return self

    def validate_value(self, value: ParameterValue) -> ParameterValue:
        """合法则返回规范化值，否则抛出 ValueError。"""
        t = self.type
        if t is ParameterType.CATEGORICAL:
            if value not in (self.choices or []):
                raise ValueError(f"{self.id}: {value!r} is not one of {self.choices}")
            return value
        if t is ParameterType.VECTOR:
            if not isinstance(value, list) or len(value) != self.vector_length:
                raise ValueError(f"{self.id}: expected a vector of length {self.vector_length}")
            return [self._check_scalar(float(v)) for v in value]
        if isinstance(value, (str, list)) or isinstance(value, bool):
            raise ValueError(f"{self.id}: expected a number, got {value!r}")
        number = float(value)
        if t is ParameterType.INTEGER:
            if not number.is_integer():
                raise ValueError(f"{self.id}: {value!r} is not an integer")
            return int(self._check_scalar(number))
        if t is ParameterType.DISCRETE and self.choices is not None and number not in self.choices:
            raise ValueError(f"{self.id}: {value!r} is not one of {self.choices}")
        return self._check_scalar(number)

    def _check_scalar(self, number: float) -> float:
        if not math.isfinite(number):
            raise ValueError(f"{self.id}: value must be finite")
        if self.bounds is not None and not self.bounds.contains(number):
            raise ValueError(f"{self.id}: {number:g} outside bounds {self.bounds.describe()}")
        return number
