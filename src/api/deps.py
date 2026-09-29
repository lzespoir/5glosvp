from fastapi import Request

from experiments import ExperimentService
from optimization import OptimizationService
from system_optimization import SystemOptimizationService
from system_simulation import SystemExperimentService
from scenarios import ScenarioSystemService


def get_service(request: Request) -> ExperimentService:
    return request.app.state.service


def get_optimization_service(request: Request) -> OptimizationService:
    return request.app.state.optimization_service


def get_system_service(request: Request) -> SystemExperimentService:
    return request.app.state.system_service


def get_system_optimization_service(request: Request) -> SystemOptimizationService:
    return request.app.state.system_optimization_service


def get_scenario_service(request: Request) -> ScenarioSystemService:
    return request.app.state.scenario_service
