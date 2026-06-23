from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request

from backend.auth import get_current_user
from backend.errors import bad_request, not_found, unauthorized
from backend.schemas.generation import (
    GenerationRunListResponse,
    GenerationRunRequest,
    GenerationRunResponse,
    GenerationUsageResponse,
)
from backend.services.generation_service import GenerationRunNotFoundException, UnsupportedGenerationKindException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/generation", tags=["generation"])


@router.get("/options", response_model=dict)
async def generation_options(request: Request):
    return request.app.state.generation_catalog_service.catalog()


@router.get("/catalog", response_model=dict)
async def generation_catalog(request: Request):
    return request.app.state.generation_catalog_service.catalog()


@router.post("/runs", response_model=GenerationRunResponse)
async def create_generation_run(payload: GenerationRunRequest, request: Request):
    user = await get_current_user(request)
    if user is None:
        raise unauthorized()
    request_data = payload.model_dump()
    auth_value = request_data.get("auth")
    auth = auth_value if isinstance(auth_value, dict) else {}
    auth["userId"] = user["id"]
    request_data["auth"] = auth
    service = request.app.state.generation_application_service
    try:
        return await service.create_run(request_data)
    except UnsupportedGenerationKindException as exc:
        raise bad_request(str(exc))
    except ValueError as exc:
        raise bad_request(str(exc))


@router.get("/runs", response_model=GenerationRunListResponse)
async def list_generation_runs(request: Request, limit: int = Query(100, ge=1, le=200)):
    service = request.app.state.generation_application_service
    return await service.list_runs(limit)


@router.get("/runs/{run_id}", response_model=GenerationRunResponse)
async def get_generation_run(run_id: str, request: Request):
    service = request.app.state.generation_application_service
    try:
        return await service.get_run(run_id)
    except GenerationRunNotFoundException:
        raise not_found("generation_run")


@router.get("/usage", response_model=GenerationUsageResponse)
async def generation_usage(request: Request):
    service = request.app.state.generation_application_service
    return await service.usage()
