from fastapi import Request

from experiments import ExperimentService
from optimization import OptimizationService
from system_simulation import SystemExperimentService


def get_service(request: Request) -> ExperimentService:
    return request.app.state.service


def get_optimization_service(request: Request) -> OptimizationService:
    return request.app.state.optimization_service


def get_system_service(request: Request) -> SystemExperimentService:
    return request.app.state.system_service
