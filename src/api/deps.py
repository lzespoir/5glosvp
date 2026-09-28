from fastapi import Request

from experiments import ExperimentService
from optimization import OptimizationService


def get_service(request: Request) -> ExperimentService:
    return request.app.state.service


def get_optimization_service(request: Request) -> OptimizationService:
    return request.app.state.optimization_service
