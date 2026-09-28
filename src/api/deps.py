from fastapi import Request

from experiments import ExperimentService


def get_service(request: Request) -> ExperimentService:
    return request.app.state.service
