"""
算法注册表 / Algorithm registry.

业务层只通过 registry 获取算法，不写 if algorithm_id == ...。
Day 7 只允许静态注册仓库内的算法；不做动态插件加载 / 上传代码 / 远程执行。
"""

from __future__ import annotations

from .builtin import GridSearchAlgorithm
from .errors import AlgorithmNotFoundError
from .examples.research_demo_optimizer import ResearchDemoOptimizer
from .sdk import Algorithm, AlgorithmMetadata


class AlgorithmRegistry:
    def __init__(self) -> None:
        self._classes: dict[str, type[Algorithm]] = {}

    def register(self, algorithm_class: type[Algorithm]) -> None:
        algorithm_id = algorithm_class.metadata().algorithm_id
        if algorithm_id in self._classes:
            raise ValueError(f"Algorithm '{algorithm_id}' already registered")
        self._classes[algorithm_id] = algorithm_class

    def _class(self, algorithm_id: str) -> type[Algorithm]:
        try:
            return self._classes[algorithm_id]
        except KeyError:
            raise AlgorithmNotFoundError(
                f"Unknown algorithm '{algorithm_id}'. Available: {', '.join(sorted(self._classes)) or '-'}"
            ) from None

    def metadata(self, algorithm_id: str) -> AlgorithmMetadata:
        return self._class(algorithm_id).metadata()

    def create(self, algorithm_id: str) -> Algorithm:
        """每次优化运行一个新实例（算法有状态）。"""
        return self._class(algorithm_id)()

    def list(self) -> list[AlgorithmMetadata]:
        return [self._classes[i].metadata() for i in sorted(self._classes)]


def default_algorithm_registry() -> AlgorithmRegistry:
    registry = AlgorithmRegistry()
    registry.register(GridSearchAlgorithm)
    registry.register(ResearchDemoOptimizer)
    return registry
