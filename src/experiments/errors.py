"""实验服务异常 / Experiment service exceptions."""


class ExperimentServiceError(Exception):
    """实验服务错误基类 / Base class for experiment service errors."""


class ScenarioNotFoundError(ExperimentServiceError):
    pass


class ExperimentNotFoundError(ExperimentServiceError):
    pass


class ArtifactNotFoundError(ExperimentServiceError):
    pass
