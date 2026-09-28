"""算法接入错误 / Algorithm integration errors."""

from __future__ import annotations

from .sdk import CompatibilityCode, CompatibilityIssue


class AlgorithmError(Exception):
    pass


class AlgorithmNotFoundError(AlgorithmError):
    pass


class AlgorithmCompatibilityError(AlgorithmError):
    """运行前兼容性检查失败；code 为第一个错误的代码。"""

    def __init__(self, errors: list[CompatibilityIssue]) -> None:
        super().__init__("; ".join(e.message for e in errors))
        self.errors = errors
        self.code: CompatibilityCode = errors[0].code


class AlgorithmExecutionError(AlgorithmError):
    """算法在 suggest / observe / finalize 中抛出异常，或违反接口契约（例如越界建议）。"""
